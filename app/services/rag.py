from __future__ import annotations
from typing import Any, Dict, Optional
import logging
import re
import asyncio
from sqlalchemy.future import select
from app.services.llm_client import generar_respuesta
from app.services.retrieval.retriever_factory import get_retriever
from app.models.producto import Producto
from app.models.mensaje import Mensaje
from app.services.prompts import prompt_ventas, prompt_empresa
from app.services.contextos import CONTEXTO_EMPRESA_SEXTINVALLE
from app.services.pedidos import PedidoManager
from app.services.rag_clientes import RAGClientes
from app.services.rag_ventas import RAGVentas
from app.core.exceptions import RAGException, TimeoutException, DatabaseException

# Configuración de timeouts
RAG_TIMEOUT_SECONDS = 15  # Reducido de 30 a 15 segundos
RETRIEVAL_TIMEOUT_SECONDS = 5  # Timeout específico para retrieval
LLM_TIMEOUT_SECONDS = 10  # Timeout específico para LLM

logger = logging.getLogger(__name__)

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
    timeout_seconds: int = RAG_TIMEOUT_SECONDS,
    **kwargs
) -> Dict[str, Any]:
    """
    Pipeline RAG centralizado: retrieval, generación y respuesta con sistemas especializados.
    """
    try:
        # Ejecutar con timeout global
        return await asyncio.wait_for(
            _consultar_rag_internal(
                mensaje, tipo, db, nombre_agente, nombre_empresa, 
                tono, instrucciones, usuario_id, llm, chat_id, **kwargs
            ),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout en consultar_rag después de {timeout_seconds}s para mensaje: {mensaje[:100]}")
        raise TimeoutException("consultar_rag", timeout_seconds)
    except Exception as e:
        logger.error(f"Error en consultar_rag: {str(e)}", exc_info=True)
        raise RAGException(
            message=f"Error en pipeline RAG: {str(e)[:100]}",
            rag_type=tipo,
            details={"mensaje_length": len(mensaje), "chat_id": chat_id}
        )


async def _consultar_rag_internal(
    mensaje: str,
    tipo: str,
    db,
    nombre_agente: str,
    nombre_empresa: str,
    tono: str,
    instrucciones: str,
    usuario_id: int,
    llm: str,
    chat_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Implementación interna del pipeline RAG con sistemas especializados.
    """
    try:
        logger.info(f"[RAG] Procesando consulta tipo '{tipo}': {mensaje[:50]}...")
        
        # Memoria conversacional reciente (últimos 10 mensajes)
        historial_contexto = ""
        
        if chat_id:
            try:
                # Timeout para consultas de historial
                result = await asyncio.wait_for(
                    db.execute(
                        select(Mensaje)
                        .where(Mensaje.chat_id == chat_id)
                        .order_by(Mensaje.timestamp.desc())
                        .limit(10)
                    ),
                    timeout=3.0  # Timeout corto para BD
                )
                historial = result.scalars().all()[::-1]  # Orden cronológico
                historial_contexto = "\n".join([
                    f"{m.remitente}: {m.mensaje}" + 
                    (f" (Estado: {m.estado_venta})" if m.estado_venta else "")
                    for m in historial
                ])
                logger.info(f"[RAG] Historial obtenido: {len(historial)} mensajes")
                
            except asyncio.TimeoutError:
                logger.warning("Timeout obteniendo historial, continuando sin historial")
                historial_contexto = ""
            except Exception as e:
                logger.error(f"Error obteniendo historial: {str(e)}")
                historial_contexto = ""

        # 🔥 SISTEMA RAG_VENTAS CENTRALIZADO - Para todas las consultas de venta/inventario
        if tipo in ["inventario", "venta", "producto", "compra"]:
            logger.info(f"[RAG] Delegando a RAG_VENTAS centralizado")
            
            # Obtener contexto de inventario 
            try:
                contexto_inventario = await asyncio.wait_for(
                    retrieval_inventario(mensaje, db),
                    timeout=RETRIEVAL_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout en retrieval de inventario")
                contexto_inventario = "No se pudo acceder al inventario por timeout"
            except Exception as e:
                logger.error(f"Error en retrieval de inventario: {e}")
                contexto_inventario = "Error accediendo al inventario"
            
            # DELEGAR A RAG_VENTAS
            return await RAGVentas.procesar_consulta_venta(
                mensaje=mensaje,
                chat_id=chat_id,
                db=db,
                contexto_inventario=contexto_inventario,
                historial_contexto=historial_contexto,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones,
                llm=llm
            )

        # 🔥 SISTEMA RAG_CLIENTES - Para consultas de cliente
        elif tipo == "cliente":
            logger.info(f"[RAG] Delegando a RAG_CLIENTES")
            try:
                return await RAGClientes.procesar_consulta_cliente(
                    mensaje, db, nombre_agente, nombre_empresa, tono, instrucciones, llm
                )
            except Exception as e:
                logger.error(f"Error en RAG_CLIENTES: {e}")
                return {
                    "respuesta": "Hubo un error procesando tu consulta de cliente. Por favor, intenta de nuevo.",
                    "estado_venta": None,
                    "tipo_mensaje": "cliente",
                    "metadatos": {"error": True, "subsistema": "RAG_CLIENTES"}
                }

        # 🔥 SISTEMA RAG_EMPRESA - Para consultas generales
        elif tipo in ["empresa", "general"]:
            logger.info(f"[RAG] Procesando consulta de empresa/general")
            try:
                contexto_empresa = await asyncio.wait_for(
                    retrieval_contexto_empresa(mensaje, db),
                    timeout=RETRIEVAL_TIMEOUT_SECONDS
                )
                
                # Generar respuesta usando contexto de empresa
                system_prompt, user_prompt = prompt_empresa(
                    contexto=contexto_empresa,
                    mensaje=mensaje,
                    nombre_agente=nombre_agente,
                    nombre_empresa=nombre_empresa,
                    tono=tono,
                    instrucciones=instrucciones
                )
                
                respuesta = await asyncio.wait_for(
                    generar_respuesta(user_prompt, llm, system_prompt, temperatura=0.5),
                    timeout=LLM_TIMEOUT_SECONDS
                )
                
                return {
                    "respuesta": respuesta,
                    "estado_venta": None,
                    "tipo_mensaje": "empresa",
                    "metadatos": {"contexto_empresa": bool(contexto_empresa)}
                }
                
            except asyncio.TimeoutError:
                logger.warning("Timeout en RAG_EMPRESA")
                return {
                    "respuesta": "Lo siento, el sistema está experimentando demoras. Estamos aquí para ayudarte con información sobre Sextinvalle.",
                    "estado_venta": None,
                    "tipo_mensaje": "empresa",
                    "metadatos": {"timeout": True}
                }
            except Exception as e:
                logger.error(f"Error en RAG_EMPRESA: {e}")
                return {
                    "respuesta": "Hubo un error procesando tu consulta. ¿En qué puedo ayudarte sobre Sextinvalle?",
                    "estado_venta": None,
                    "tipo_mensaje": "empresa", 
                    "metadatos": {"error": True, "subsistema": "RAG_EMPRESA"}
                }
        
        # Si no coincide con ningún tipo conocido, usar RAG_VENTAS por defecto
        else:
            logger.warning(f"[RAG] Tipo desconocido '{tipo}', delegando a RAG_VENTAS")
            try:
                contexto_inventario = await asyncio.wait_for(
                    retrieval_inventario(mensaje, db),
                    timeout=RETRIEVAL_TIMEOUT_SECONDS
                )
            except:
                contexto_inventario = ""
                
            return await RAGVentas.procesar_consulta_venta(
                mensaje=mensaje,
                chat_id=chat_id,
                db=db,
                contexto_inventario=contexto_inventario,
                historial_contexto=historial_contexto,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones,
                llm=llm
            )
                
    except Exception as e:
        logger.error(f"Error crítico en _consultar_rag_internal: {str(e)}", exc_info=True)
        return {
            "respuesta": "Lo siento, ocurrió un error interno. Por favor, intenta nuevamente o contacta soporte.",
            "estado_venta": None,
            "tipo_mensaje": "error",
            "metadatos": {"error_critico": True, "tipo_original": tipo}
        }

async def retrieval_inventario(mensaje: str, db):
    """
    Recupera productos relevantes usando búsqueda optimizada.
    Versión mejorada que soluciona problemas de contexto.
    """
    try:
        logger.info(f"[retrieval_inventario] Procesando consulta: '{mensaje}'")
        
        # 1. DETECTAR CONSULTAS GENERALES (mostrar todo)
        consultas_generales = [
            "qué tienen", "que tienen", "productos disponibles", "qué productos", 
            "que productos", "catálogo", "inventario", "lista", "productos",
            "todo lo que tienen", "mostrar productos", "ver productos", "precios"
        ]
        
        mensaje_lower = mensaje.lower()
        es_consulta_general = any(patron in mensaje_lower for patron in consultas_generales)
        
        if es_consulta_general:
            logger.info(f"[retrieval_inventario] DETECTADA CONSULTA GENERAL")
            
            # Obtener productos activos de la base de datos
            try:
                result = await db.execute(
                    select(Producto).where(
                        Producto.activo == True,
                        Producto.stock > 0
                    ).order_by(Producto.nombre).limit(20)
                )
                productos = result.scalars().all()
                
                if not productos:
                    return "Lo siento, actualmente no tenemos productos disponibles en nuestro inventario."
                
                # Respuesta simple y directa
                respuesta_partes = ["PRODUCTOS_DISPONIBLES: Nuestros productos principales:\n"]
                
                for producto in productos:
                    disponibilidad = "✅ Disponible" if producto.stock > 10 else "⚠️ Stock limitado"
                    respuesta_partes.append(f"• {producto.nombre} - ${producto.precio:,.0f} ({disponibilidad})")
                
                return "\n".join(respuesta_partes)
                
            except Exception as e:
                logger.error(f"[retrieval_inventario] Error consultando productos: {e}")
                return "Error al obtener el catálogo de productos. Por favor, intenta de nuevo."
        
        # 2. BÚSQUEDA ESPECÍFICA DE PRODUCTOS - MEJORADA
        # Extraer solo palabras clave relevantes, ignorando palabras comunes
        palabras_irrelevantes = {
            "hola", "necesito", "información", "sobre", "quiero", "quisiera", 
            "me", "puedes", "podrías", "ayudar", "con", "para", "del", "de", "la", "el",
            "busco", "buscando", "tengo", "dime", "cuales", "cuáles", "son", "hay"
        }
        
        # Filtrar palabras relevantes de al menos 3 caracteres y que no sean irrelevantes
        palabras_busqueda = [
            palabra for palabra in mensaje_lower.split() 
            if len(palabra) >= 3 and palabra not in palabras_irrelevantes
        ]
        
        if not palabras_busqueda:
            return "¿Podrías ser más específico sobre qué producto estás buscando?"
        
        # Mapeo mejorado de sinónimos
        sinonimos = {
            "extintor": ["extintor", "extintores", "pqs", "co2", "fuego", "incendio"],
            "extintores": ["extintor", "extintores", "pqs", "co2", "fuego", "incendio"],
            "casco": ["casco", "cascos", "seguridad", "protección"],
            "cascos": ["casco", "cascos", "seguridad", "protección"],
            "guante": ["guante", "guantes", "nitrilo", "seguridad", "protección"],
            "guantes": ["guante", "guantes", "nitrilo", "seguridad", "protección"],
            "bota": ["bota", "botas", "seguridad", "acero", "protección"],
            "botas": ["bota", "botas", "seguridad", "acero", "protección"],
            "gafa": ["gafa", "gafas", "lente", "lentes", "seguridad", "protección"],
            "gafas": ["gafa", "gafas", "lente", "lentes", "seguridad", "protección"],
            "chaleco": ["chaleco", "chalecos", "reflectivo", "visibilidad"],
            "señal": ["señal", "señales", "salida", "evacuación", "seguridad"]
        }
        
        # Expandir palabras con sinónimos solo para palabras clave principales
        palabras_expandidas = set()
        palabras_principales = []
        
        for palabra in palabras_busqueda:
            palabras_principales.append(palabra)
            palabras_expandidas.add(palabra)
            if palabra in sinonimos:
                palabras_expandidas.update(sinonimos[palabra])
        
        logger.info(f"[retrieval_inventario] Palabras clave detectadas: {palabras_principales}")
        logger.info(f"[retrieval_inventario] Palabras expandidas con sinónimos: {list(palabras_expandidas)}")
        
        # Búsqueda inteligente: priorizar coincidencias exactas de palabras clave
        try:
            from sqlalchemy import or_, and_
            
            # Crear condiciones de búsqueda
            condiciones_principales = []
            condiciones_expandidas = []
            
            # Buscar palabras principales (mayor prioridad)
            for palabra in palabras_principales:
                condiciones_principales.extend([
                    Producto.nombre.ilike(f"%{palabra}%"),
                    Producto.descripcion.ilike(f"%{palabra}%")
                ])
            
            # Buscar palabras expandidas (menor prioridad)
            for palabra in palabras_expandidas:
                condiciones_expandidas.extend([
                    Producto.nombre.ilike(f"%{palabra}%"),
                    Producto.descripcion.ilike(f"%{palabra}%")
                ])
            
            # Primera búsqueda: coincidencias principales
            productos_encontrados = []
            if condiciones_principales:
                result = await db.execute(
                    select(Producto).where(
                        or_(*condiciones_principales),
                        Producto.activo == True,
                        Producto.stock > 0
                    ).limit(8)
                )
                productos_encontrados = result.scalars().all()
            
            # Si no hay suficientes resultados, buscar con sinónimos
            if len(productos_encontrados) < 3 and condiciones_expandidas:
                result = await db.execute(
                    select(Producto).where(
                        or_(*condiciones_expandidas),
                        Producto.activo == True,
                        Producto.stock > 0
                    ).limit(10)
                )
                productos_expandidos = result.scalars().all()
                
                # Combinar resultados eliminando duplicados
                ids_existentes = {p.id for p in productos_encontrados}
                for p in productos_expandidos:
                    if p.id not in ids_existentes and len(productos_encontrados) < 10:
                        productos_encontrados.append(p)
            
            if not productos_encontrados:
                return f"No encontramos productos relacionados con: {', '.join(palabras_principales)}. ¿Podrías intentar con otras palabras?"
            
            # Formatear respuesta
            respuesta_partes = []
            for p in productos_encontrados:
                disponibilidad = "✅ Disponible" if p.stock > 10 else "⚠️ Stock limitado"
                descripcion = p.descripcion if p.descripcion else "Sin descripción"
                respuesta_partes.append(f"• **{p.nombre}**: {descripcion} - ${p.precio:,.0f} ({disponibilidad})")
            
            return "\n".join(respuesta_partes)
                
        except Exception as e:
            logger.error(f"[retrieval_inventario] Error en búsqueda específica: {e}")
            return "Error al buscar productos. Por favor, intenta de nuevo."
        
    except Exception as e:
        logger.error(f"[retrieval_inventario] Error crítico: {str(e)}")
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
        logger.info(f"Números encontrados en '{mensaje}': {numeros}, cantidad_raw: {cantidad_raw}")
        
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
            logger.info(f"Producto encontrado: {mejor_candidato['producto']['nombre']} (Score: {mejor_candidato['score_total']}, Específicas: {mejor_candidato['coincidencias_especificas']})")
            
            # Si hay múltiples candidatos con score similar, registrar para posible ambigüedad
            candidatos_similares = [c for c in productos_candidatos if c["score_total"] >= mejor_candidato["score_total"] * 0.8]
            if len(candidatos_similares) > 1:
                logger.warning(f"Múltiples productos similares encontrados: {[c['producto']['nombre'] for c in candidatos_similares[:3]]}")
            
            return mejor_candidato["producto"], cantidad
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error extrayendo producto y cantidad: {e}")
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
