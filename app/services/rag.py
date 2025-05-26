from typing import Any, Dict, Optional
import logging
import re
from sqlalchemy.future import select
from app.services.llm_client import generar_respuesta
from app.services.retrieval.retriever_factory import get_retriever
from app.models.producto import Producto
from app.models.mensaje import Mensaje
from app.services.prompts import prompt_ventas, prompt_empresa
from app.services.contextos import CONTEXTO_EMPRESA_SEXTINVALLE
from app.services.pedidos import PedidoManager

async def consultar_rag(
    mensaje: str,
    tipo: str,
    db,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Sextinvalle",
    tono: str = "formal",
    instrucciones: str = "",
    usuario_id: int = None,
    llm: str = "gemini",
    chat_id: str = None,
    **kwargs
) -> dict:
    """
    Pipeline RAG: retrieval, generación y respuesta.
    """
    try:
        # Memoria conversacional reciente (últimos 10 mensajes)
        historial_contexto = ""
        estado_pedido = {"tiene_pedido": False}
        
        if chat_id:
            result = await db.execute(
                select(Mensaje)
                .where(Mensaje.chat_id == chat_id)
                .order_by(Mensaje.timestamp.desc())
                .limit(10)
            )
            historial = result.scalars().all()[::-1]  # Orden cronológico
            historial_contexto = "\n".join([
                f"{m.remitente}: {m.mensaje}" + 
                (f" (Estado: {m.estado_venta})" if m.estado_venta else "")
                for m in historial
            ])
            logging.info(f"[consultar_rag] Historial de conversación: {historial_contexto[:300]}...")
            
            # Obtener estado del pedido actual
            estado_pedido = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            # Verificar si el usuario está pidiendo ver su pedido
            if any(palabra in mensaje.lower() for palabra in ["mi pedido", "pedido actual", "mostrar pedido", "ver pedido", "resumen pedido"]):
                pedido_actual = await PedidoManager.mostrar_pedido_actual(chat_id, db)
                if pedido_actual:
                    productos_texto = "\n".join([
                        f"- {p['producto']} x{p['cantidad']} = ${p['total']:,.0f}"
                        for p in pedido_actual['productos']
                    ])
                    datos_cliente = pedido_actual['datos_cliente']
                    datos_texto = "\n".join([f"- {k}: {v}" for k, v in datos_cliente.items() if v])
                    
                    respuesta_pedido = f"📋 **Tu pedido actual:**\n\n**Productos:**\n{productos_texto}\n\n**Total: ${pedido_actual['total']:,.0f}**"
                    
                    if datos_cliente:
                        respuesta_pedido += f"\n\n**Datos registrados:**\n{datos_texto}"
                    
                    if pedido_actual['campos_faltantes']:
                        respuesta_pedido += f"\n\n⚠️ **Faltan datos:** {', '.join(pedido_actual['campos_faltantes'])}"
                    
                    return {
                        "respuesta": respuesta_pedido,
                        "estado_venta": pedido_actual['estado'],
                        "tipo_mensaje": "venta",
                        "metadatos": pedido_actual
                    }
                else:
                    return {
                        "respuesta": "No tienes ningún pedido activo en este momento. ¿Te gustaría ver nuestros productos disponibles?",
                        "estado_venta": None,
                        "tipo_mensaje": "venta",
                        "metadatos": None
                    }

        # Retrieval según tipo de consulta
        logging.info(f"[consultar_rag] Tipo de consulta recibido: {tipo}")
        if tipo in ("inventario", "venta"):
            contexto = await retrieval_inventario(mensaje, db)
            # Información del pedido actual para el contexto
            info_pedido = ""
            if estado_pedido["tiene_pedido"]:
                productos_pedido = estado_pedido["productos"]
                total_pedido = sum(p["total"] for p in productos_pedido)
                info_pedido = f"\nPEDIDO ACTUAL DEL CLIENTE:\n"
                for p in productos_pedido:
                    info_pedido += f"- {p['producto']} x{p['cantidad']} = ${p['total']:,.0f}\n"
                info_pedido += f"Total del pedido: ${total_pedido:,.0f}\n"
                
                if estado_pedido["campos_faltantes"]:
                    info_pedido += f"Datos faltantes: {', '.join(estado_pedido['campos_faltantes'])}\n"
            
            instrucciones_extra = instrucciones + (
                "\nIMPORTANTE:\n1. Si no hay productos en el inventario, responde claramente que no tenemos productos disponibles para esa consulta.\n"
                "2. No inventes ni sugieras productos fuera del inventario.\n"
                f"3. Historial reciente de la conversación:\n{historial_contexto}\n"
                f"{info_pedido}"
            )
            system_prompt, user_prompt = prompt_ventas(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones_extra
            )
            logging.info(f"[consultar_rag] Contexto inventario obtenido: {contexto[:200]}...")
        elif tipo == "contexto":
            contexto = await retrieval_contexto_empresa(mensaje, db)
            if not contexto or contexto.strip() == "":
                contexto = "No se encontró información relevante sobre la empresa."
            instrucciones_extra = instrucciones + (
                f"\nHistorial reciente de la conversación:\n{historial_contexto}\n"
            )
            system_prompt, user_prompt = prompt_empresa(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones_extra
            )
            logging.info(f"[consultar_rag] Contexto empresa obtenido: {contexto[:200]}...")
        else:
            return {
                "respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes reformularla o ser más específico?",
                "estado_venta": None,
                "tipo_mensaje": tipo,
                "metadatos": None
            }

        # LLM (responde usando prompt)
        respuesta = await generar_respuesta(
            prompt=user_prompt,
            system_prompt=system_prompt,
            llm=llm
        )

        # Procesamiento de ventas y gestión de pedidos
        estado_venta = None
        metadatos = None
        
        # Procesamiento especial cuando hay pedido activo (INDEPENDIENTE del tipo clasificado)
        if chat_id and estado_pedido["tiene_pedido"] and estado_pedido["campos_faltantes"]:
            # PRIMERO: Verificar si el mensaje contiene intención de agregar más productos
            palabras_agregar_producto = ["también", "además", "agregar", "añadir", "quiero", "necesito", "comprar", "cotizar"]
            es_agregar_producto = any(palabra in mensaje.lower() for palabra in palabras_agregar_producto)
            
            # Verificar si hay productos mencionados en el mensaje
            producto_detectado, cantidad_detectada = await extraer_producto_cantidad(mensaje, db)
            tiene_producto = producto_detectado is not None and cantidad_detectada is not None
            
            # Si es claramente una intención de agregar producto, procesarlo como venta
            if es_agregar_producto and tiene_producto:
                logging.info(f"[consultar_rag] Detectado intento de agregar producto adicional: {mensaje}")
                # No procesar como datos del cliente, dejar que se procese como venta más abajo
                pass
            else:
                # Si hay pedido activo y faltan datos, procesar como recolección de datos
                campo_detectado = await detectar_campo_cliente(mensaje, estado_pedido["campos_faltantes"])
                
                if campo_detectado:
                    logging.info(f"[consultar_rag] Campo detectado: {campo_detectado} para mensaje: {mensaje}")
                    
                    resultado = await PedidoManager.actualizar_datos_cliente(
                        chat_id=chat_id,
                        campo=campo_detectado,
                        valor=mensaje.strip(),
                        db=db
                    )
                    
                    if resultado["exito"]:
                        estado_venta = "recolectando_datos"
                        metadatos = {
                            "campos_faltantes": resultado["campos_faltantes"],
                            "datos_completos": resultado["datos_completos"]
                        }
                        
                        # Actualizar respuesta para confirmar el dato recibido
                        campo_nombres = {
                            "nombre_completo": "nombre",
                            "cedula": "cédula",
                            "telefono": "teléfono",
                            "direccion": "dirección",
                            "barrio": "barrio",
                            "indicaciones_adicionales": "indicaciones adicionales"
                        }
                        
                        respuesta = f"✅ Perfecto, he registrado tu {campo_nombres.get(campo_detectado, campo_detectado)}: {mensaje.strip()}"
                        
                        if resultado["campos_faltantes"]:
                            siguiente_campo = resultado["campos_faltantes"][0]
                            respuesta += f"\n\nAhora necesito tu {campo_nombres.get(siguiente_campo, siguiente_campo)}."
                        
                        # Si todos los datos están completos, usar mensaje de finalización
                        if resultado["datos_completos"] and resultado.get("pedido_finalizado"):
                            estado_venta = "cerrada"
                            metadatos = resultado
                            respuesta = resultado.get("mensaje_finalizacion", "Tu pedido ha sido registrado exitosamente. Pronto te contactaremos para coordinar la entrega. ¡Gracias por confiar en Sextinvalle!")
                            
                            if resultado.get("ventas_creadas"):
                                logging.info(f"Pedido finalizado con {resultado['total_ventas']} ventas creadas")
                        
                        return {
                            "respuesta": respuesta,
                            "estado_venta": estado_venta,
                            "tipo_mensaje": "venta",
                            "metadatos": metadatos
                        }
                    else:
                        # Manejar errores de validación
                        if resultado.get("tipo_error") == "validacion":
                            return {
                                "respuesta": resultado["error"],
                                "estado_venta": "recolectando_datos",
                                "tipo_mensaje": "venta",
                                "metadatos": {"error_validacion": True, "campo": resultado.get("campo")}
                            }
                        else:
                            logging.error(f"[consultar_rag] Error actualizando datos del cliente: {resultado}")
                            return {
                                "respuesta": "Hubo un error procesando tu información. Por favor, intenta de nuevo.",
                                "estado_venta": "recolectando_datos", 
                                "tipo_mensaje": "venta",
                                "metadatos": {"error": True}
                            }
                else:
                    logging.warning(f"[consultar_rag] No se pudo detectar campo para mensaje: {mensaje}")

        if tipo == "venta" and chat_id:
            # Detectar intención de compra y extraer productos (incluyendo productos adicionales)
            palabras_intencion_compra = ["quiero", "necesito", "comprar", "cotizar", "precio de", "también", "además", "agregar", "añadir"]
            if any(palabra in mensaje.lower() for palabra in palabras_intencion_compra):
                logging.info(f"[consultar_rag] Detectada intención de compra en: {mensaje}")
                
                # Intentar extraer producto y cantidad del mensaje
                producto_detectado, cantidad_detectada = await extraer_producto_cantidad(mensaje, db)
                logging.info(f"[consultar_rag] Producto detectado: {producto_detectado}, Cantidad: {cantidad_detectada}")
                
                # Manejar errores de validación de cantidad
                if isinstance(producto_detectado, dict) and "error" in producto_detectado:
                    logging.error(f"[consultar_rag] Error en validación de cantidad: {producto_detectado}")
                    return {
                        "respuesta": producto_detectado["error"],
                        "estado_venta": None,
                        "tipo_mensaje": tipo,
                        "metadatos": {"error_validacion": True}
                    }
                
                if producto_detectado and cantidad_detectada:
                    logging.info(f"[consultar_rag] Llamando a agregar_producto_pedido...")
                    
                    # Agregar producto al pedido
                    resultado_pedido = await PedidoManager.agregar_producto_pedido(
                        chat_id=chat_id,
                        producto=producto_detectado["nombre"],
                        cantidad=cantidad_detectada,
                        precio=producto_detectado["precio"],
                        db=db,
                        producto_id=producto_detectado["id"]
                    )
                    
                    logging.info(f"[consultar_rag] Resultado de agregar_producto_pedido: {resultado_pedido}")
                    
                    if resultado_pedido["exito"]:
                        estado_venta = "pendiente"
                        metadatos = {
                            "productos": resultado_pedido["productos"],
                            "total": resultado_pedido["total"]
                        }
                        logging.info(f"Producto agregado al pedido: {producto_detectado['nombre']} x{cantidad_detectada}")
                        
                        # Personalizar respuesta para productos adicionales
                        if any(palabra in mensaje.lower() for palabra in ["también", "además", "agregar", "añadir"]):
                            respuesta = f"✅ Perfecto, he agregado {cantidad_detectada} {producto_detectado['nombre']} a tu pedido.\n\n"
                            respuesta += f"Tu pedido ahora incluye {len(resultado_pedido['productos'])} productos por un total de ${resultado_pedido['total']:,.0f}.\n\n"
                            respuesta += "¿Deseas agregar algo más o proceder con el pedido?"
                        
                        # IMPORTANTE: Retornar inmediatamente para evitar que se sobrescriba la respuesta
                        return {
                            "respuesta": respuesta,
                            "estado_venta": estado_venta,
                            "tipo_mensaje": tipo,
                            "metadatos": metadatos
                        }
                    else:
                        logging.error(f"[consultar_rag] Error agregando producto: {resultado_pedido}")
                else:
                    logging.warning(f"[consultar_rag] No se detectó producto o cantidad válida")
            
            # Detectar confirmación de compra (incluyendo mensajes con "dame las X unidades")
            elif (any(palabra in mensaje.lower() for palabra in ["sí", "confirmo", "acepto", "está bien", "perfecto", "solo eso", "nada más", "dame"]) or
                  ("dame" in mensaje.lower() and any(palabra in mensaje.lower() for palabra in ["unidades", "unidad"]))):
                estado_actual = await PedidoManager.obtener_estado_pedido(chat_id, db)
                if estado_actual["tiene_pedido"]:
                    estado_venta = "recolectando_datos"  # Cambiar a recolectando_datos para iniciar el flujo
                    metadatos = estado_actual
                    
                    # Agregar mensaje para solicitar el primer campo
                    campos_faltantes = estado_actual.get("campos_faltantes", PedidoManager.CAMPOS_REQUERIDOS)
                    if campos_faltantes:
                        primer_campo = campos_faltantes[0]
                        campo_nombres = {
                            "nombre_completo": "nombre completo",
                            "cedula": "cédula",
                            "telefono": "teléfono",
                            "direccion": "dirección",
                            "barrio": "barrio",
                            "indicaciones_adicionales": "indicaciones adicionales"
                        }
                        respuesta = f"✅ Perfecto, procederemos con tu pedido.\n\nPara procesar tu pedido, necesito algunos datos. Empecemos con tu {campo_nombres.get(primer_campo, primer_campo)}."
                        
                        return {
                            "respuesta": respuesta,
                            "estado_venta": estado_venta,
                            "tipo_mensaje": "venta",
                            "metadatos": metadatos
                        }
            
            # Estado por defecto basado en heurística
            if not estado_venta:
                if any(x in respuesta.lower() for x in ["¿deseas", "quieres confirmar", "te gustaría agregarlo", "confirmar pedido"]):
                    estado_venta = "pendiente"
                elif any(x in respuesta.lower() for x in ["pedido registrado", "compra confirmada", "venta realizada"]):
                    estado_venta = "cerrada"
                elif any(x in mensaje.lower() for x in ["cotización", "precio", "costo"]):
                    estado_venta = "iniciada"

        return {
            "respuesta": respuesta,
            "estado_venta": estado_venta,
            "tipo_mensaje": tipo,
            "metadatos": metadatos
            }

    except Exception as e:
        logging.error(f"[consultar_rag] Error: {str(e)}")
        return {
            "respuesta": "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
            "estado_venta": None,
            "tipo_mensaje": tipo,
            "metadatos": None
        }

async def retrieval_inventario(mensaje: str, db):
    """
    Recupera productos relevantes usando búsqueda semántica (FAISS o Pinecone) con fallback a búsqueda por texto.
    Solo productos activos y con stock > 0.
    NO muestra stock exacto ni lista completa de productos.
    """
    try:
        # Primero intentar búsqueda semántica
        retriever = get_retriever(db)
        await retriever.sync_with_db()
        ids = await retriever.search(mensaje, top_k=3)
        
        productos_encontrados = []
        
        if ids:
            result = await db.execute(
                select(Producto).where(
                    Producto.id.in_(ids),
                    Producto.activo == True,
                    Producto.stock > 0
                )
            )
            productos_encontrados = result.scalars().all()
        
        # FALLBACK: Si no encuentra productos relevantes o los productos no son relevantes, usar búsqueda por texto
        productos_relevantes = False
        if productos_encontrados:
            # Verificar si los productos encontrados son realmente relevantes
            palabras_mensaje = mensaje.lower().split()
            for producto in productos_encontrados:
                nombre_producto = producto.nombre.lower()
                # Si alguna palabra del mensaje está en el nombre del producto, es relevante
                if any(palabra in nombre_producto for palabra in palabras_mensaje if len(palabra) > 2):
                    productos_relevantes = True
                    break
        
        # MEJORA: Si encontramos productos relevantes pero pocos, buscar productos similares adicionales
        if productos_relevantes and len(productos_encontrados) < 3:
            # Buscar productos similares adicionales
            palabras_busqueda = mensaje.lower().split()
            palabras_relevantes = [p for p in palabras_busqueda if len(p) > 2]
            
            if palabras_relevantes:
                condiciones_adicionales = []
                for palabra in palabras_relevantes:
                    condiciones_adicionales.append(Producto.nombre.ilike(f"%{palabra}%"))
                    condiciones_adicionales.append(Producto.descripcion.ilike(f"%{palabra}%"))
                    
                    # Buscar versión singular/plural
                    if palabra.endswith('es') and len(palabra) > 4:
                        singular = palabra[:-2]
                        condiciones_adicionales.append(Producto.nombre.ilike(f"%{singular}%"))
                        condiciones_adicionales.append(Producto.descripcion.ilike(f"%{singular}%"))
                    elif palabra.endswith('s') and len(palabra) > 3 and not palabra.endswith('es'):
                        singular = palabra[:-1]
                        condiciones_adicionales.append(Producto.nombre.ilike(f"%{singular}%"))
                        condiciones_adicionales.append(Producto.descripcion.ilike(f"%{singular}%"))
                
                from sqlalchemy import or_
                result_adicional = await db.execute(
                    select(Producto).where(
                        or_(*condiciones_adicionales),
                        Producto.activo == True,
                        Producto.stock > 0
                    ).limit(5)
                )
                productos_adicionales = result_adicional.scalars().all()
                
                # Combinar productos sin duplicados
                ids_existentes = {p.id for p in productos_encontrados}
                for p in productos_adicionales:
                    if p.id not in ids_existentes:
                        productos_encontrados.append(p)
                        if len(productos_encontrados) >= 5:  # Límite máximo
                            break
        
        if not productos_encontrados or not productos_relevantes:
            logging.info("[retrieval_inventario] Fallback a búsqueda por texto")
            palabras_busqueda = mensaje.lower().split()
            
            # Filtrar palabras relevantes (más de 2 caracteres)
            palabras_relevantes = [p for p in palabras_busqueda if len(p) > 2]
            
            if palabras_relevantes:
                # Buscar productos que contengan alguna de las palabras (incluyendo singulares/plurales)
                condiciones = []
                for palabra in palabras_relevantes:
                    # Buscar la palabra tal como está
                    condiciones.append(Producto.nombre.ilike(f"%{palabra}%"))
                    condiciones.append(Producto.descripcion.ilike(f"%{palabra}%"))
                    
                    # Buscar versión singular/plural con reglas específicas para español
                    if palabra.endswith('es') and len(palabra) > 4:
                        # Plurales que terminan en 'es' -> quitar 'es'
                        singular = palabra[:-2]
                        condiciones.append(Producto.nombre.ilike(f"%{singular}%"))
                        condiciones.append(Producto.descripcion.ilike(f"%{singular}%"))
                    elif palabra.endswith('s') and len(palabra) > 3 and not palabra.endswith('es'):
                        # Plurales que terminan en 's' -> quitar 's'
                        singular = palabra[:-1]
                        condiciones.append(Producto.nombre.ilike(f"%{singular}%"))
                        condiciones.append(Producto.descripcion.ilike(f"%{singular}%"))
                    elif not palabra.endswith('s'):
                        # Si no termina en 's', probar con 's' y 'es'
                        plural_s = palabra + 's'
                        plural_es = palabra + 'es'
                        condiciones.append(Producto.nombre.ilike(f"%{plural_s}%"))
                        condiciones.append(Producto.descripcion.ilike(f"%{plural_s}%"))
                        condiciones.append(Producto.nombre.ilike(f"%{plural_es}%"))
                        condiciones.append(Producto.descripcion.ilike(f"%{plural_es}%"))
                
                from sqlalchemy import or_
                result = await db.execute(
                    select(Producto).where(
                        or_(*condiciones),
                        Producto.activo == True,
                        Producto.stock > 0
                    ).limit(3)
                )
                productos_encontrados = result.scalars().all()
        
        if not productos_encontrados:
            logging.info("[retrieval_inventario] No se encontraron productos relevantes")
            return "No encontramos productos específicos para tu consulta. ¿Podrías ser más específico sobre qué tipo de producto de seguridad necesitas?"
        
        # MEJORA: Agrupar productos similares y mostrar variaciones
        productos_agrupados = {}
        for p in productos_encontrados:
            # Extraer nombre base del producto (sin especificaciones)
            nombre_base = p.nombre
            for especificacion in ["10 libras", "20 libras", "amarillo", "azul", "rojo", "verde", "negro", "blanco", "pequeño", "mediano", "grande"]:
                nombre_base = nombre_base.replace(especificacion, "").strip()
            
            if nombre_base not in productos_agrupados:
                productos_agrupados[nombre_base] = []
            productos_agrupados[nombre_base].append(p)
        
        contexto = []
        for nombre_base, productos_grupo in productos_agrupados.items():
            if len(productos_grupo) == 1:
                # Producto único
                p = productos_grupo[0]
                disponibilidad = "Disponible" if p.stock > 10 else "Stock limitado" if p.stock > 0 else "Agotado"
                contexto.append(f"{p.nombre}: {p.descripcion} (Precio: ${p.precio:,.0f}, {disponibilidad})")
            else:
                # Múltiples variaciones del mismo producto
                contexto.append(f"**{nombre_base}** - Disponible en las siguientes variaciones:")
                for p in productos_grupo:
                    disponibilidad = "Disponible" if p.stock > 10 else "Stock limitado" if p.stock > 0 else "Agotado"
                    # Extraer solo la especificación diferenciadora
                    especificacion = p.nombre.replace(nombre_base, "").strip()
                    contexto.append(f"  - {especificacion}: {p.descripcion} (Precio: ${p.precio:,.0f}, {disponibilidad})")
        
        contexto_str = "\n".join(contexto)
        logging.info(f"[retrieval_inventario] Contexto encontrado: {len(productos_encontrados)} productos en {len(productos_agrupados)} grupos")
        return contexto_str
        
    except Exception as e:
        logging.error(f"[retrieval_inventario] Error: {str(e)}")
        return "Error al buscar productos. Por favor, intenta de nuevo."

async def retrieval_contexto_empresa(mensaje: str, db):
    """
    Recupera contexto de la empresa.
    (Actualmente estático, pero puede mejorarse para cargar dinámicamente en el futuro).
    """
    return CONTEXTO_EMPRESA_SEXTINVALLE

async def extraer_producto_cantidad(mensaje: str, db):
    """
    Extrae producto y cantidad del mensaje del usuario usando LLM y búsqueda en BD
    """
    try:
        import re
        
        # Buscar números en el mensaje para cantidad
        numeros = re.findall(r'-?\d+', mensaje)  # Incluir números negativos
        cantidad_raw = int(numeros[0]) if numeros else 1
        
        # Log para debugging
        logging.info(f"Números encontrados en '{mensaje}': {numeros}, cantidad_raw: {cantidad_raw}")
        
        # VALIDACIÓN CRÍTICA: Rechazar cantidades inválidas inmediatamente
        if cantidad_raw <= 0:
            return {"error": f"La cantidad debe ser mayor a 0. Recibido: {cantidad_raw}"}, None
        
        if cantidad_raw > 1000:
            return {"error": f"La cantidad máxima por producto es 1000 unidades. Para pedidos mayores, contacta directamente con ventas. Recibido: {cantidad_raw}"}, None
        
        cantidad = cantidad_raw
        
        # Buscar productos en la base de datos que coincidan con palabras del mensaje
        palabras_mensaje = mensaje.lower().split()
        
        result = await db.execute(
            select(Producto).where(
                Producto.activo == True,
                Producto.stock > 0
            )
        )
        productos = result.scalars().all()
        
        # Buscar coincidencias por nombre - mejorado para manejar SKUs similares
        productos_candidatos = []
        
        # Diccionario de sinónimos mejorado para productos
        sinonimos = {
            "extintor": ["extintor", "extintores", "pqs", "extinguidor", "extinguidores", "polvo", "químico", "seco"],
            "linterna": ["linterna", "linternas", "led", "recargable", "recargables", "lámpara", "lámparas", "luz", "iluminación"],
            "casco": ["casco", "cascos", "seguridad", "industrial", "protección", "cabeza"],
            "guantes": ["guantes", "guante", "nitrilo", "seguridad", "protección", "manos"],
            "botas": ["botas", "bota", "seguridad", "acero", "protección", "pies"],
            "chaleco": ["chaleco", "chalecos", "reflectivo", "reflectivos", "visibilidad", "alta"],
            "arnés": ["arnés", "arnes", "arneses", "seguridad", "alturas", "altura", "completo"],
            "respirador": ["respirador", "respiradores", "n95", "mascarilla", "mascarillas", "protección"],
            "gafas": ["gafas", "lentes", "seguridad", "transparentes", "protección", "ojos"],
            "detector": ["detector", "detectores", "humo", "fotoeléctrico", "alarma"],
            "señal": ["señal", "señales", "evacuación", "led", "salida", "emergencia"],
            "botiquín": ["botiquín", "botiquin", "botiquines", "primeros", "auxilios", "emergencia"],
            "candado": ["candado", "candados", "loto", "seguridad", "bloqueo"],
            "manta": ["manta", "mantas", "ignífuga", "ignifuga", "fuego", "protección"],
            "cinta": ["cinta", "cintas", "seguridad", "amarilla", "aislante", "demarcación"],
            "alicate": ["alicate", "alicates", "pinza", "pinzas", "universal"],
            "martillo": ["martillo", "martillos"],
            "taladro": ["taladro", "taladros", "industrial"],
            "televisor": ["televisor", "televisores", "industrial", "pulgadas"]
        }
        
        # Extraer especificaciones del mensaje (números, colores, tamaños)
        import re
        especificaciones_mensaje = {
            "numeros": re.findall(r'\d+', mensaje),
            "colores": [color for color in ["amarillo", "azul", "rojo", "verde", "negro", "blanco", "naranja"] if color in mensaje.lower()],
            "unidades": [unidad for unidad in ["libras", "kg", "pulgadas", "metros", "cm"] if unidad in mensaje.lower()]
        }
        
        for producto in productos:
            nombre_producto = producto.nombre.lower()
            palabras_producto = nombre_producto.split()
            
            # Contar coincidencias básicas
            coincidencias_basicas = 0
            for palabra_mensaje in palabras_mensaje:
                if len(palabra_mensaje) > 2:
                    # Buscar coincidencias directas
                    for palabra_producto in palabras_producto:
                        if palabra_mensaje in palabra_producto or palabra_producto in palabra_mensaje:
                            coincidencias_basicas += 1
                    
                    # Buscar coincidencias por sinónimos
                    for clave, lista_sinonimos in sinonimos.items():
                        if palabra_mensaje in lista_sinonimos:
                            for palabra_producto in palabras_producto:
                                if any(sin in palabra_producto for sin in lista_sinonimos):
                                    coincidencias_basicas += 2
            
            # Contar coincidencias de especificaciones (números, colores, etc.)
            coincidencias_especificas = 0
            
            # Verificar números (ej: 10 libras, 20 libras)
            for numero in especificaciones_mensaje["numeros"]:
                if numero in nombre_producto:
                    coincidencias_especificas += 3  # Peso alto para especificaciones exactas
            
            # Verificar colores
            for color in especificaciones_mensaje["colores"]:
                if color in nombre_producto:
                    coincidencias_especificas += 3
            
            # Verificar unidades
            for unidad in especificaciones_mensaje["unidades"]:
                if unidad in nombre_producto:
                    coincidencias_especificas += 2
            
            # Solo considerar productos con coincidencias básicas
            if coincidencias_basicas > 0:
                productos_candidatos.append({
                    "producto": {
                        "id": producto.id,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "stock": producto.stock
                    },
                    "coincidencias_basicas": coincidencias_basicas,
                    "coincidencias_especificas": coincidencias_especificas,
                    "score_total": coincidencias_basicas + coincidencias_especificas
                })
        
        if productos_candidatos:
            # Ordenar por score total (especificaciones primero, luego básicas)
            productos_candidatos.sort(key=lambda x: (x["coincidencias_especificas"], x["coincidencias_basicas"]), reverse=True)
            
            mejor_candidato = productos_candidatos[0]
            logging.info(f"Producto encontrado: {mejor_candidato['producto']['nombre']} (Score: {mejor_candidato['score_total']}, Específicas: {mejor_candidato['coincidencias_especificas']})")
            
            # Si hay múltiples candidatos con score similar, registrar para posible ambigüedad
            candidatos_similares = [c for c in productos_candidatos if c["score_total"] >= mejor_candidato["score_total"] * 0.8]
            if len(candidatos_similares) > 1:
                logging.warning(f"Múltiples productos similares encontrados: {[c['producto']['nombre'] for c in candidatos_similares[:3]]}")
            
            return mejor_candidato["producto"], cantidad
        
        return None, None
        
    except Exception as e:
        logging.error(f"Error extrayendo producto y cantidad: {e}")
        return None, None

async def detectar_campo_cliente(mensaje: str, campos_faltantes: list):
    """
    Detecta qué campo del cliente corresponde al mensaje basado en patrones mejorados
    """
    import re
    
    mensaje_lower = mensaje.lower().strip()
    
    # Excluir mensajes de confirmación/negación que no son datos del cliente
    confirmaciones = ["sí", "si", "confirmo", "acepto", "está bien", "perfecto", "ok", "vale", "no", "nada más", "solo eso", "dame", "por favor"]
    if any(conf in mensaje_lower for conf in confirmaciones):
        return None
    
    # Excluir mensajes que contienen números y palabras de productos (claramente no son datos del cliente)
    palabras_productos = ["unidades", "unidad", "producto", "productos", "cinta", "extintor", "casco", "guantes", "botas"]
    if (any(char.isdigit() for char in mensaje) and 
        any(palabra in mensaje_lower for palabra in palabras_productos)):
        return None
    
    # Si el mensaje parece ser un número de teléfono celular (10 dígitos que empiezan por 3)
    if re.match(r'^3\d{9}$', mensaje) and "telefono" in campos_faltantes:
        return "telefono"
    
    # Si el mensaje parece ser una cédula (6-12 dígitos consecutivos, pero no celular)
    if re.match(r'^\d{6,12}$', mensaje) and not re.match(r'^3\d{9}$', mensaje) and "cedula" in campos_faltantes:
        return "cedula"
    
    # Si el mensaje parece ser un número de teléfono con formato (espacios/guiones)
    if re.match(r'^[\d\s\-\+\(\)]{7,15}$', mensaje) and "telefono" in campos_faltantes:
        return "telefono"
    
    # Si contiene palabras típicas de nombres (2+ palabras, al menos una con mayúscula)
    if (len(mensaje.split()) >= 2 and 
        any(palabra[0].isupper() for palabra in mensaje.split() if palabra.isalpha()) and
        "nombre_completo" in campos_faltantes):
        return "nombre_completo"
    
    # Si contiene palabras típicas de direcciones
    direccion_palabras = ["calle", "carrera", "avenida", "cr", "cl", "av", "diagonal", "transversal", "#", "bis"]
    if (any(palabra in mensaje_lower for palabra in direccion_palabras) and 
        "direccion" in campos_faltantes):
        return "direccion"
    
    # Si es una palabra simple que podría ser un barrio
    if (len(mensaje.split()) <= 2 and 
        not any(char.isdigit() for char in mensaje) and
        "barrio" in campos_faltantes):
        return "barrio"
    
    # Si contiene palabras de referencia/indicaciones
    indicaciones_palabras = ["casa", "edificio", "torre", "conjunto", "cerca", "frente", "al lado", "esquina"]
    if (any(palabra in mensaje_lower for palabra in indicaciones_palabras) and 
        "indicaciones_adicionales" in campos_faltantes):
        return "indicaciones_adicionales"
    
    # Si no se detectó ningún patrón específico, usar el primer campo faltante
    # (respeta el orden lógico de la conversación)
    if campos_faltantes:
        return campos_faltantes[0]
    
    return None
