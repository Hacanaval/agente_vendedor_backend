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
from app.services.rag_clientes import RAGClientes

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

        # NUEVO: Detectar consultas de historial de clientes
        # TEMPORALMENTE DESACTIVADO COMPLETAMENTE para testing
        """
        deteccion_cliente = await RAGClientes.detectar_consulta_cliente(mensaje)
        
        if deteccion_cliente["es_consulta_cliente"]:
            logging.info(f"[consultar_rag] Detectada consulta de cliente: {deteccion_cliente}")
            
            if deteccion_cliente["cedula_detectada"]:
                # Consulta específica con cédula
                cedula = deteccion_cliente["cedula_detectada"]
                
                if deteccion_cliente["tipo_consulta"] == "estadisticas":
                    resultado = await RAGClientes.obtener_estadisticas_cliente(cedula, db, llm)
                else:
                    resultado = await RAGClientes.consultar_historial_cliente(cedula, mensaje, db, llm)
                
                return {
                    "respuesta": resultado["respuesta"],
                    "estado_venta": None,
                    "tipo_mensaje": "cliente",
                    "metadatos": {
                        "tipo_consulta_cliente": deteccion_cliente["tipo_consulta"],
                        "cedula": cedula,
                        "encontrado": resultado.get("encontrado", False)
                    }
                }
            
            elif deteccion_cliente["tipo_consulta"] == "busqueda":
                # Buscar cliente por nombre
                # Extraer nombre del mensaje
                palabras = mensaje.split()
                nombre_busqueda = " ".join([p for p in palabras if not p.isdigit() and p.lower() not in ["buscar", "cliente", "encontrar", "información", "de", "del"]])
                
                if nombre_busqueda:
                    resultado = await RAGClientes.buscar_cliente_por_nombre(nombre_busqueda, db)
                    
                    return {
                        "respuesta": resultado["respuesta"],
                        "estado_venta": None,
                        "tipo_mensaje": "cliente",
                        "metadatos": {
                            "tipo_consulta_cliente": "busqueda",
                            "termino_busqueda": nombre_busqueda,
                            "clientes_encontrados": resultado.get("total", 0)
                        }
                    }
                else:
                    return {
                        "respuesta": "Para buscar un cliente, proporciona su nombre o cédula. Ejemplo: 'Buscar cliente Juan Pérez' o 'Cliente 12345678'",
                        "estado_venta": None,
                        "tipo_mensaje": "cliente",
                        "metadatos": {"error": "falta_termino_busqueda"}
                    }
            else:
                return {
                    "respuesta": "Para consultar información de un cliente, proporciona su cédula. Ejemplo: 'Historial del cliente 12345678' o 'Estadísticas del cliente 12345678'",
                    "estado_venta": None,
                    "tipo_mensaje": "cliente",
                    "metadatos": {"error": "falta_cedula"}
                }
        """

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
                "\nIMPORTANTE:\n1. Si el contexto empieza con 'PRODUCTOS_DISPONIBLES:', presenta SIEMPRE toda esa lista de productos al cliente de manera organizada y atractiva.\n"
                "2. Si no hay productos específicos para una búsqueda, responde claramente que no tenemos productos disponibles para esa consulta particular.\n"
                "3. No inventes ni sugieras productos fuera del inventario proporcionado.\n"
                f"4. Historial reciente de la conversación:\n{historial_contexto}\n"
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
                            "correo": "correo electrónico",
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
                        
                        # Generar respuesta natural basada en el contexto
                        if any(palabra in mensaje.lower() for palabra in ["también", "además", "agregar", "añadir"]):
                            respuesta = f"Perfecto, he agregado {cantidad_detectada} {producto_detectado['nombre']} a tu pedido.\n\n"
                            respuesta += f"Tu pedido ahora incluye {len(resultado_pedido['productos'])} productos por un total de ${resultado_pedido['total']:,.0f}.\n\n"
                            respuesta += "¿Te gustaría agregar algo más o procedemos con este pedido?"
                        else:
                            # Primera vez agregando producto
                            respuesta = f"Excelente, he agregado {cantidad_detectada} {producto_detectado['nombre']} a tu pedido por un total de ${resultado_pedido['total']:,.0f}.\n\n"
                            respuesta += "¿Deseas agregar algún otro producto o procedemos con este pedido?"
                        
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
                            "correo": "correo electrónico",
                            "direccion": "dirección",
                            "barrio": "barrio",
                            "indicaciones_adicionales": "indicaciones adicionales"
                        }
                        respuesta = f"Perfecto, procederemos con tu pedido.\n\nPara coordinar la entrega, necesito algunos datos. ¿Podrías proporcionarme tu {campo_nombres.get(primer_campo, primer_campo)}?"
                        
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
    Recupera productos relevantes usando búsqueda híbrida mejorada.
    Maneja consultas generales, específicas y múltiples productos.
    """
    try:
        logging.info(f"[retrieval_inventario] Procesando consulta: '{mensaje}'")
        
        # 1. DETECTAR CONSULTAS GENERALES (mostrar todo)
        consultas_generales = [
            "qué tienen", "que tienen", "productos disponibles", "qué productos", 
            "que productos", "catálogo", "inventario", "lista", "tienen disponible",
            "qué venden", "que venden", "mostrar productos", "ver productos",
            "disponibles", "ofrecen", "manejan", "venden", "productos",
            "todo lo que tienen", "que hay", "que tiene", "mostrar todo",
            "ver todo", "todo disponible", "que ofrecen", "que manejan"
        ]
        
        mensaje_lower = mensaje.lower()
        es_consulta_general = any(patron in mensaje_lower for patron in consultas_generales)
        
        # DEBUGGING detección
        logging.info(f"[retrieval_inventario] Mensaje: '{mensaje}' | Lower: '{mensaje_lower}' | Es general: {es_consulta_general}")
        if not es_consulta_general:
            logging.info(f"[retrieval_inventario] Patrones evaluados: {[patron for patron in consultas_generales if patron in mensaje_lower]}")
        
        if es_consulta_general:
            logging.info(f"[retrieval_inventario] DETECTADA CONSULTA GENERAL: '{mensaje}'")
            
            # Obtener TODOS los productos activos de la base de datos
            try:
                result = await db.execute(
                    select(Producto).where(
                        Producto.activo == True,
                        Producto.stock > 0
                    ).order_by(Producto.nombre)
                )
                todos_productos = result.scalars().all()
                
                if not todos_productos:
                    return "Lo siento, actualmente no tenemos productos disponibles en nuestro inventario."
                
                # Agrupar productos por categorías
                categorias = {}
                for producto in todos_productos:
                    # Determinar categoría basada en el nombre del producto
                    nombre_lower = producto.nombre.lower()
                    if "extintor" in nombre_lower:
                        categoria = "🧯 **Extintores**"
                    elif "casco" in nombre_lower or "bota" in nombre_lower or "guante" in nombre_lower or "chaleco" in nombre_lower:
                        categoria = "🦺 **Equipos de Protección Personal**"
                    elif "linterna" in nombre_lower or "señal" in nombre_lower or "detector" in nombre_lower:
                        categoria = "🔦 **Señalización y Seguridad**"
                    elif "botiquín" in nombre_lower or "candado" in nombre_lower or "manta" in nombre_lower:
                        categoria = "🛡️ **Seguridad y Emergencias**"
                    elif "alicate" in nombre_lower or "martillo" in nombre_lower or "taladro" in nombre_lower:
                        categoria = "🔧 **Herramientas**"
                    elif "televisor" in nombre_lower:
                        categoria = "📺 **Equipos Audiovisuales**"
                    else:
                        categoria = "📦 **Otros Productos**"
                    
                    if categoria not in categorias:
                        categorias[categoria] = []
                    
                    disponibilidad = "✅ Disponible" if producto.stock > 10 else "⚠️ Stock limitado"
                    categorias[categoria].append(f"• {producto.nombre} - ${producto.precio:,.0f} ({disponibilidad})")
                
                # Construir respuesta formateada
                respuesta_partes = ["PRODUCTOS_DISPONIBLES: Catálogo completo de Sextinvalle:\n"]
                
                for categoria, productos_cat in categorias.items():
                    respuesta_partes.append(f"{categoria}:")
                    respuesta_partes.extend(productos_cat)
                    respuesta_partes.append("")  # Línea en blanco entre categorías
                
                return "\n".join(respuesta_partes)
                
            except Exception as e:
                logging.error(f"[retrieval_inventario] Error consultando productos para catálogo general: {e}")
                return "Error al obtener el catálogo de productos. Por favor, intenta de nuevo."
        
        # 2. BÚSQUEDA ESPECÍFICA DE PRODUCTOS
        # Extraer palabras clave del mensaje
        palabras_busqueda = mensaje_lower.split()
        
        # Filtrar palabras irrelevantes y mantener solo las importantes
        palabras_irrelevantes = {
            "tienen", "tienes", "hay", "venden", "vendes", "necesito", "quiero", 
            "busco", "me", "un", "una", "unos", "unas", "el", "la", "los", "las",
            "de", "del", "en", "con", "para", "por", "que", "qué", "como", "cómo",
            "dónde", "donde", "cuánto", "cuanto", "cuál", "cual", "cuáles", "cuales",
            "favor", "por", "ayuda", "ayudar", "información", "info", "ser", "más",
            "puede", "pueden", "podría", "podrías", "decir", "decirme", "saber",
            "hola", "buenos", "días", "tardes", "noches", "gracias"
        }
        
        # Limpiar signos de puntuación de las palabras
        import re
        palabras_limpias = []
        for palabra in palabras_busqueda:
            # Remover signos de puntuación
            palabra_limpia = re.sub(r'[¿?¡!.,;:()"]', '', palabra)
            if len(palabra_limpia) > 2 and palabra_limpia not in palabras_irrelevantes:
                palabras_limpias.append(palabra_limpia)
        
        palabras_relevantes = palabras_limpias
        
        logging.info(f"[retrieval_inventario] Palabras relevantes extraídas: {palabras_relevantes}")
        
        if not palabras_relevantes:
            return "¿Podrías ser más específico sobre qué producto estás buscando? Por ejemplo: 'extintores', 'cascos de seguridad', etc."
        
        # 3. BÚSQUEDA HÍBRIDA: Semántica + Texto
        productos_encontrados = []
        
        # 3.1 Búsqueda semántica con FAISS/Pinecone
        try:
            retriever = get_retriever(db)
            await retriever.sync_with_db()
            
            # Crear consulta optimizada para búsqueda semántica
            consulta_semantica = " ".join(palabras_relevantes)
            ids_semanticos = await retriever.search(consulta_semantica, top_k=5)
            
            if ids_semanticos:
                result = await db.execute(
                    select(Producto).where(
                        Producto.id.in_(ids_semanticos),
                        Producto.activo == True,
                        Producto.stock > 0
                    )
                )
                productos_semanticos = result.scalars().all()
                
                # Validar relevancia de resultados semánticos
                for producto in productos_semanticos:
                    nombre_producto = producto.nombre.lower()
                    descripcion_producto = (producto.descripcion or "").lower()
                    
                    # Un producto es relevante si contiene alguna palabra clave
                    es_relevante = any(
                        palabra in nombre_producto or palabra in descripcion_producto
                        for palabra in palabras_relevantes
                    )
                    
                    if es_relevante:
                        productos_encontrados.append(producto)
                        
                logging.info(f"[retrieval_inventario] Búsqueda semántica: {len(productos_semanticos)} encontrados, {len(productos_encontrados)} relevantes")
        
        except Exception as e:
            logging.warning(f"[retrieval_inventario] Búsqueda semántica falló: {e}")
        
        # 3.2 Búsqueda por texto como respaldo/complemento
        if len(productos_encontrados) < 3:
            condiciones_texto = []
            
            for palabra in palabras_relevantes:
                # Búsqueda exacta
                condiciones_texto.append(Producto.nombre.ilike(f"%{palabra}%"))
                condiciones_texto.append(Producto.descripcion.ilike(f"%{palabra}%"))
                
                # Manejo de plurales/singulares en español
                if palabra.endswith('es') and len(palabra) > 4:
                    # extintores -> extintor
                    singular = palabra[:-2]
                    condiciones_texto.append(Producto.nombre.ilike(f"%{singular}%"))
                    condiciones_texto.append(Producto.descripcion.ilike(f"%{singular}%"))
                elif palabra.endswith('s') and len(palabra) > 3 and not palabra.endswith('es'):
                    # cascos -> casco
                    singular = palabra[:-1]  
                    condiciones_texto.append(Producto.nombre.ilike(f"%{singular}%"))
                    condiciones_texto.append(Producto.descripcion.ilike(f"%{singular}%"))
                elif not palabra.endswith('s'):
                    # extintor -> extintores
                    plural_s = palabra + 's'
                    plural_es = palabra + 'es'
                    condiciones_texto.append(Producto.nombre.ilike(f"%{plural_s}%"))
                    condiciones_texto.append(Producto.descripcion.ilike(f"%{plural_s}%"))
                    condiciones_texto.append(Producto.nombre.ilike(f"%{plural_es}%"))
                    condiciones_texto.append(Producto.descripcion.ilike(f"%{plural_es}%"))
            
            if condiciones_texto:
                from sqlalchemy import or_
                result = await db.execute(
                    select(Producto).where(
                        or_(*condiciones_texto),
                        Producto.activo == True,
                        Producto.stock > 0
                    ).limit(10)
                )
                productos_texto = result.scalars().all()
                
                # Agregar productos de texto que no estén ya incluidos
                ids_existentes = {p.id for p in productos_encontrados}
                for p in productos_texto:
                    if p.id not in ids_existentes:
                        productos_encontrados.append(p)
                
                logging.info(f"[retrieval_inventario] Búsqueda por texto: {len(productos_texto)} adicionales encontrados")
        
        # 4. CONSTRUIR RESPUESTA
        if not productos_encontrados:
            sugerencia = "¿Podrías intentar con palabras como: 'extintores', 'cascos', 'guantes', 'botas', 'chalecos', 'linternas'?"
            return f"No encontramos productos que coincidan con tu búsqueda. {sugerencia}"
        
        # 5. AGRUPAR Y FORMATEAR RESULTADOS
        productos_agrupados = {}
        for p in productos_encontrados:
            # Extraer nombre base eliminando especificaciones
            nombre_base = p.nombre
            especificaciones = ["10 libras", "20 libras", "amarillo", "azul", "negro", "blanco", "verde", "rojo"]
            for esp in especificaciones:
                nombre_base = nombre_base.replace(esp, "").strip()
            
            # Limpiar espacios dobles
            nombre_base = re.sub(r'\s+', ' ', nombre_base).strip()
            
            if nombre_base not in productos_agrupados:
                productos_agrupados[nombre_base] = []
            productos_agrupados[nombre_base].append(p)
        
        # 6. FORMATEAR RESPUESTA FINAL
        contexto_partes = []
        
        for nombre_base, productos_grupo in productos_agrupados.items():
            if len(productos_grupo) == 1:
                # Producto único
                p = productos_grupo[0]
                disponibilidad = "✅ Disponible" if p.stock > 10 else "⚠️ Stock limitado"
                contexto_partes.append(f"• **{p.nombre}**: {p.descripcion} - ${p.precio:,.0f} ({disponibilidad})")
            else:
                # Múltiples variaciones
                contexto_partes.append(f"• **{nombre_base}** - Variaciones disponibles:")
                for p in sorted(productos_grupo, key=lambda x: x.precio):
                    disponibilidad = "✅ Disponible" if p.stock > 10 else "⚠️ Stock limitado"
                    especificacion = p.nombre.replace(nombre_base, "").strip()
                    if especificacion:
                        contexto_partes.append(f"  - {especificacion}: ${p.precio:,.0f} ({disponibilidad})")
                    else:
                        contexto_partes.append(f"  - Estándar: ${p.precio:,.0f} ({disponibilidad})")
        
        contexto_str = "\n".join(contexto_partes)
        logging.info(f"[retrieval_inventario] Respuesta final: {len(productos_encontrados)} productos en {len(productos_agrupados)} grupos")
        
        return contexto_str
        
    except Exception as e:
        logging.error(f"[retrieval_inventario] Error crítico: {str(e)}")
        return "Error al buscar productos. Por favor, intenta de nuevo o contacta con soporte."

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
    confirmaciones = ["sí", "si", "confirmo", "acepto", "está bien", "perfecto", "ok", "vale", "no", "nada más", "solo eso", "dame", "por favor", "correcto", "exacto", "así es", "claro"]
    if any(conf in mensaje_lower for conf in confirmaciones):
        return None
    
    # Excluir mensajes muy cortos que claramente son confirmaciones
    if len(mensaje.strip()) <= 8 and mensaje_lower in ["sí", "si", "ok", "vale", "bien", "correcto", "exacto", "claro"]:
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
    
    # Si el mensaje parece ser un correo electrónico
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', mensaje) and "correo" in campos_faltantes:
        return "correo"
    
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
