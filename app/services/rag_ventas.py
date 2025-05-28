"""
Sistema RAG especializado para Ventas y Procesamiento de Pedidos
Este módulo centraliza toda la lógica de ventas que está dispersa en rag.py
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.producto import Producto
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.services.pedidos import PedidoManager
from app.services.llm_client import generar_respuesta
from app.services.prompts import prompt_ventas
from app.core.exceptions import RAGException

logger = logging.getLogger(__name__)

class RAGVentas:
    """Sistema RAG especializado para ventas y gestión de pedidos"""
    
    # Palabras clave para detección de intenciones
    PALABRAS_INTENCION_COMPRA = [
        "quiero", "necesito", "comprar", "cotizar", "precio de", 
        "también", "además", "agregar", "añadir"
    ]
    
    PALABRAS_CONFIRMACION = [
        "sí", "si", "confirmo", "acepto", "está bien", "perfecto", 
        "solo eso", "nada más", "dame", "ok", "listo"
    ]
    
    PALABRAS_CANCELACION = [
        "no", "cancelar", "borrar", "eliminar", "no quiero", "cambiar"
    ]

    @staticmethod
    async def procesar_consulta_venta(
        mensaje: str,
        chat_id: str,
        db: AsyncSession,
        contexto_inventario: str = "",
        historial_contexto: str = "",
        nombre_agente: str = "Agente Vendedor",
        nombre_empresa: str = "Sextinvalle",
        tono: str = "amigable",
        instrucciones: str = "",
        llm: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Procesa una consulta de venta de manera integral
        
        Args:
            mensaje: Mensaje del usuario
            chat_id: ID del chat
            db: Sesión de base de datos
            contexto_inventario: Contexto de productos obtenido
            historial_contexto: Historial conversacional
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con respuesta, estado_venta, tipo_mensaje y metadatos
        """
        try:
            logger.info(f"[RAGVentas] Procesando consulta de venta: {mensaje[:50]}...")
            
            # 1. Obtener estado actual del pedido
            estado_pedido = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            # 2. Verificar si es consulta de pedido actual
            if await RAGVentas._es_consulta_pedido_actual(mensaje):
                return await RAGVentas._mostrar_pedido_actual(chat_id, db)
            
            # 3. Si hay pedido activo con datos faltantes, procesarlo primero
            if estado_pedido["tiene_pedido"] and estado_pedido.get("campos_faltantes"):
                # Verificar si es intención de agregar más productos
                if await RAGVentas._es_intencion_agregar_producto(mensaje, db):
                    # Procesar como nueva compra
                    return await RAGVentas._procesar_nueva_compra(
                        mensaje, chat_id, db, contexto_inventario, 
                        historial_contexto, nombre_agente, nombre_empresa, tono, instrucciones, llm
                    )
                else:
                    # Procesar como datos del cliente
                    return await RAGVentas._procesar_datos_cliente(mensaje, chat_id, db)
            
            # 4. Procesar según tipo de intención
            if await RAGVentas._es_intencion_compra(mensaje):
                return await RAGVentas._procesar_nueva_compra(
                    mensaje, chat_id, db, contexto_inventario,
                    historial_contexto, nombre_agente, nombre_empresa, tono, instrucciones, llm
                )
            
            elif await RAGVentas._es_confirmacion_pedido(mensaje):
                return await RAGVentas._confirmar_pedido(chat_id, db)
            
            elif await RAGVentas._es_cancelacion(mensaje):
                return await RAGVentas._cancelar_pedido(chat_id, db)
            
            else:
                # Consulta general de ventas sin intención específica
                return await RAGVentas._respuesta_general_ventas(
                    mensaje, contexto_inventario, historial_contexto,
                    nombre_agente, nombre_empresa, tono, instrucciones, llm
                )
                
        except Exception as e:
            logger.error(f"[RAGVentas] Error procesando consulta: {e}")
            return {
                "respuesta": "Lo siento, hubo un error procesando tu consulta de venta. Por favor, intenta de nuevo.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"error": True, "error_details": str(e)[:100]}
            }

    @staticmethod
    async def _es_consulta_pedido_actual(mensaje: str) -> bool:
        """Detecta si el usuario quiere ver su pedido actual"""
        palabras_pedido = [
            "mi pedido", "pedido actual", "mostrar pedido", "ver pedido", 
            "resumen pedido", "qué tengo", "estado pedido"
        ]
        return any(palabra in mensaje.lower() for palabra in palabras_pedido)

    @staticmethod
    async def _mostrar_pedido_actual(chat_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Muestra el pedido actual del cliente"""
        try:
            pedido_actual = await asyncio.wait_for(
                PedidoManager.mostrar_pedido_actual(chat_id, db),
                timeout=5.0
            )
            
            if pedido_actual:
                productos_texto = "\n".join([
                    f"- {p['producto']} x{p['cantidad']} = ${p['total']:,.0f}"
                    for p in pedido_actual['productos']
                ])
                
                respuesta_pedido = f"📋 **Tu pedido actual:**\n\n**Productos:**\n{productos_texto}\n\n**Total: ${pedido_actual['total']:,.0f}**"
                
                datos_cliente = pedido_actual.get('datos_cliente', {})
                if datos_cliente:
                    datos_texto = "\n".join([f"- {k}: {v}" for k, v in datos_cliente.items() if v])
                    respuesta_pedido += f"\n\n**Datos registrados:**\n{datos_texto}"
                
                if pedido_actual.get('campos_faltantes'):
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
                    "metadatos": {}
                }
                
        except asyncio.TimeoutError:
            logger.warning("Timeout obteniendo pedido actual")
            return {
                "respuesta": "Hubo una demora obteniendo tu pedido. Por favor, intenta de nuevo.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"timeout": True}
            }

    @staticmethod
    async def _es_intencion_agregar_producto(mensaje: str, db: AsyncSession) -> bool:
        """Detecta si el mensaje es para agregar un producto"""
        palabras_agregar = ["también", "además", "agregar", "añadir", "quiero", "necesito", "comprar"]
        es_agregar = any(palabra in mensaje.lower() for palabra in palabras_agregar)
        
        if es_agregar:
            # Verificar si menciona un producto específico
            producto_detectado, _ = await RAGVentas._extraer_producto_cantidad(mensaje, db)
            return producto_detectado is not None
        
        return False

    @staticmethod
    async def _es_intencion_compra(mensaje: str) -> bool:
        """Detecta intención de compra en el mensaje"""
        return any(palabra in mensaje.lower() for palabra in RAGVentas.PALABRAS_INTENCION_COMPRA)

    @staticmethod
    async def _es_confirmacion_pedido(mensaje: str) -> bool:
        """Detecta confirmación de pedido"""
        confirmacion_basica = any(palabra in mensaje.lower() for palabra in RAGVentas.PALABRAS_CONFIRMACION)
        confirmacion_especial = "dame" in mensaje.lower() and any(
            palabra in mensaje.lower() for palabra in ["unidades", "unidad"]
        )
        return confirmacion_basica or confirmacion_especial

    @staticmethod
    async def _es_cancelacion(mensaje: str) -> bool:
        """Detecta intención de cancelar"""
        return any(palabra in mensaje.lower() for palabra in RAGVentas.PALABRAS_CANCELACION)

    @staticmethod
    async def _procesar_nueva_compra(
        mensaje: str, chat_id: str, db: AsyncSession, contexto_inventario: str,
        historial_contexto: str, nombre_agente: str, nombre_empresa: str, 
        tono: str, instrucciones: str, llm: str
    ) -> Dict[str, Any]:
        """Procesa una nueva compra o agregado de producto"""
        try:
            logger.info(f"[RAGVentas] Detectada intención de compra: {mensaje}")
            
            # Extraer producto y cantidad
            producto_detectado, cantidad_detectada = await RAGVentas._extraer_producto_cantidad(mensaje, db)
            
            # Manejar errores de validación
            if isinstance(producto_detectado, dict) and "error" in producto_detectado:
                return {
                    "respuesta": producto_detectado["error"],
                    "estado_venta": None,
                    "tipo_mensaje": "venta",
                    "metadatos": {"error_validacion": True}
                }
            
            if producto_detectado and cantidad_detectada:
                # Agregar producto al pedido
                resultado_pedido = await PedidoManager.agregar_producto(
                    chat_id, producto_detectado["id"], cantidad_detectada, db
                )
                
                if resultado_pedido["exito"]:
                    estado_venta = "pendiente"
                    metadatos = {
                        "productos": resultado_pedido["productos"],
                        "total": resultado_pedido["total"]
                    }
                    
                    # Generar respuesta natural
                    es_agregar_adicional = any(
                        palabra in mensaje.lower() for palabra in ["también", "además", "agregar", "añadir"]
                    )
                    
                    if es_agregar_adicional:
                        respuesta = f"Perfecto, he agregado {cantidad_detectada} {producto_detectado['nombre']} a tu pedido.\n\n"
                        respuesta += f"Tu pedido ahora incluye {len(resultado_pedido['productos'])} productos por un total de ${resultado_pedido['total']:,.0f}.\n\n"
                        respuesta += "¿Te gustaría agregar algo más o procedemos con este pedido?"
                    else:
                        respuesta = f"Excelente, he agregado {cantidad_detectada} {producto_detectado['nombre']} a tu pedido por un total de ${resultado_pedido['total']:,.0f}.\n\n"
                        respuesta += "¿Deseas agregar algún otro producto o procedemos con este pedido?"
                    
                    return {
                        "respuesta": respuesta,
                        "estado_venta": estado_venta,
                        "tipo_mensaje": "venta",
                        "metadatos": metadatos
                    }
                else:
                    return {
                        "respuesta": f"Lo siento, hubo un problema agregando el producto: {resultado_pedido.get('error', 'Error desconocido')}",
                        "estado_venta": None,
                        "tipo_mensaje": "venta",
                        "metadatos": {"error": True}
                    }
            else:
                # No se detectó producto válido, generar respuesta informativa
                return await RAGVentas._respuesta_general_ventas(
                    mensaje, contexto_inventario, historial_contexto,
                    nombre_agente, nombre_empresa, tono, instrucciones, llm
                )
                
        except Exception as e:
            logger.error(f"[RAGVentas] Error procesando nueva compra: {e}")
            return {
                "respuesta": "Lo siento, hubo un error procesando tu compra. Por favor, intenta de nuevo.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"error": True}
            }

    @staticmethod
    async def _procesar_datos_cliente(mensaje: str, chat_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Procesa datos del cliente para completar pedido"""
        try:
            resultado = await PedidoManager.actualizar_datos_cliente(chat_id, mensaje, db)
            
            if resultado["exito"]:
                respuesta = resultado["mensaje"]
                estado_venta = "listo_para_finalizar" if resultado["datos_completos"] else "recolectando_datos"
                metadatos = resultado
                
                # Si todos los datos están completos, finalizar pedido
                if resultado["datos_completos"] and resultado.get("pedido_finalizado"):
                    estado_venta = "cerrada"
                    respuesta = resultado.get(
                        "mensaje_finalizacion", 
                        "Tu pedido ha sido registrado exitosamente. Pronto te contactaremos para coordinar la entrega. ¡Gracias por confiar en Sextinvalle!"
                    )
                    
                    if resultado.get("ventas_creadas"):
                        logger.info(f"Pedido finalizado con {resultado['total_ventas']} ventas creadas")
                
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
                    return {
                        "respuesta": "Hubo un error procesando tu información. Por favor, intenta de nuevo.",
                        "estado_venta": "recolectando_datos",
                        "tipo_mensaje": "venta",
                        "metadatos": {"error": True}
                    }
                    
        except Exception as e:
            logger.error(f"[RAGVentas] Error procesando datos cliente: {e}")
            return {
                "respuesta": "Hubo un error procesando tu información. Por favor, intenta de nuevo.",
                "estado_venta": "recolectando_datos",
                "tipo_mensaje": "venta",
                "metadatos": {"error": True}
            }

    @staticmethod
    async def _confirmar_pedido(chat_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Confirma un pedido e inicia recolección de datos"""
        try:
            estado_actual = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            if estado_actual["tiene_pedido"]:
                estado_venta = "recolectando_datos"
                metadatos = estado_actual
                
                # Solicitar el primer campo faltante
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
                else:
                    # Ya tiene todos los datos, finalizar directamente
                    resultado_finalizacion = await PedidoManager.finalizar_pedido(chat_id, db)
                    
                    if resultado_finalizacion["exito"]:
                        return {
                            "respuesta": "Tu pedido ha sido registrado exitosamente. Pronto te contactaremos para coordinar la entrega. ¡Gracias por confiar en Sextinvalle!",
                            "estado_venta": "cerrada",
                            "tipo_mensaje": "venta",
                            "metadatos": resultado_finalizacion
                        }
                    else:
                        return {
                            "respuesta": f"Hubo un problema finalizando el pedido: {resultado_finalizacion.get('error', 'Error desconocido')}",
                            "estado_venta": "pendiente",
                            "tipo_mensaje": "venta",
                            "metadatos": {"error": True}
                        }
            else:
                return {
                    "respuesta": "No tienes ningún pedido activo para confirmar. ¿Te gustaría ver nuestros productos disponibles?",
                    "estado_venta": None,
                    "tipo_mensaje": "venta",
                    "metadatos": {}
                }
                
        except Exception as e:
            logger.error(f"[RAGVentas] Error confirmando pedido: {e}")
            return {
                "respuesta": "Hubo un error confirmando tu pedido. Por favor, intenta de nuevo.",
                "estado_venta": "pendiente",
                "tipo_mensaje": "venta",
                "metadatos": {"error": True}
            }

    @staticmethod
    async def _cancelar_pedido(chat_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Cancela el pedido actual"""
        try:
            estado_actual = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            if estado_actual["tiene_pedido"]:
                # Eliminar mensajes del pedido actual
                await PedidoManager.cancelar_pedido(chat_id, db)
                
                return {
                    "respuesta": "Tu pedido ha sido cancelado. ¿Te gustaría explorar nuestros productos nuevamente?",
                    "estado_venta": None,
                    "tipo_mensaje": "venta",
                    "metadatos": {"pedido_cancelado": True}
                }
            else:
                return {
                    "respuesta": "No tienes ningún pedido activo para cancelar. ¿Te gustaría ver nuestros productos disponibles?",
                    "estado_venta": None,
                    "tipo_mensaje": "venta",
                    "metadatos": {}
                }
                
        except Exception as e:
            logger.error(f"[RAGVentas] Error cancelando pedido: {e}")
            return {
                "respuesta": "Hubo un error cancelando el pedido. Por favor, intenta de nuevo.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"error": True}
            }

    @staticmethod
    async def _respuesta_general_ventas(
        mensaje: str, contexto_inventario: str, historial_contexto: str,
        nombre_agente: str, nombre_empresa: str, tono: str, instrucciones: str, llm: str
    ) -> Dict[str, Any]:
        """Genera respuesta general de ventas usando LLM"""
        try:
            # Preparar contexto completo
            instrucciones_extra = instrucciones + (
                "\nIMPORTANTE:\n"
                "1. Si el contexto empieza con 'PRODUCTOS_DISPONIBLES:', presenta toda esa lista de productos de manera organizada y atractiva.\n"
                "2. Si no hay productos específicos para una búsqueda, responde claramente que no tenemos productos disponibles para esa consulta particular.\n"
                "3. No inventes ni sugieras productos fuera del inventario proporcionado.\n"
                f"4. HISTORIAL CONVERSACIONAL RECIENTE:\n{historial_contexto}\n"
                "5. Si el usuario hace preguntas generales sobre precios o productos sin especificar, usa el contexto anterior para entender a qué se refiere.\n"
            )
            
            system_prompt, user_prompt = prompt_ventas(
                contexto=contexto_inventario,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones_extra
            )
            
            respuesta = await asyncio.wait_for(
                generar_respuesta(user_prompt, llm, system_prompt, temperatura=0.3),
                timeout=15.0  # Timeout más generoso
            )
            
            # Determinar estado de venta basado en la respuesta
            estado_venta = None
            if any(x in respuesta.lower() for x in ["¿deseas", "quieres confirmar", "te gustaría agregarlo", "confirmar pedido"]):
                estado_venta = "pendiente"
            elif any(x in mensaje.lower() for x in ["cotización", "precio", "costo"]):
                estado_venta = "iniciada"
            
            return {
                "respuesta": respuesta,
                "estado_venta": estado_venta,
                "tipo_mensaje": "venta",
                "metadatos": {}
            }
            
        except asyncio.TimeoutError:
            logger.warning("Timeout en respuesta general de ventas")
            return {
                "respuesta": "Lo siento, el sistema está experimentando demoras. Por favor, intenta tu consulta nuevamente o contacta directamente con nosotros.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"timeout": True}
            }
        except Exception as e:
            logger.error(f"[RAGVentas] Error en respuesta general: {e}")
            return {
                "respuesta": "Lo siento, hubo un problema procesando tu consulta. Por favor, intenta de nuevo.",
                "estado_venta": None,
                "tipo_mensaje": "venta",
                "metadatos": {"error": True}
            }

    @staticmethod
    async def _extraer_producto_cantidad(mensaje: str, db: AsyncSession) -> Tuple[Optional[Dict], Optional[int]]:
        """
        Extrae producto y cantidad del mensaje
        
        Returns:
            Tuple de (producto_dict, cantidad) o (None, None) si no se encuentra
        """
        try:
            # Obtener todos los productos para búsqueda
            result = await db.execute(select(Producto).where(Producto.activo == True))
            productos = result.scalars().all()
            
            # Extraer cantidad del mensaje
            cantidad_match = re.search(r'(\d+)\s*(?:unidades?|uds?|piezas?)?', mensaje.lower())
            cantidad = int(cantidad_match.group(1)) if cantidad_match else 1
            
            # Validar cantidad
            if cantidad <= 0:
                return {"error": "La cantidad debe ser mayor a 0"}, None
            if cantidad > 1000:
                return {"error": "La cantidad no puede ser mayor a 1000 unidades"}, None
            
            # Buscar producto mencionado
            producto_encontrado = None
            mensaje_lower = mensaje.lower()
            
            for producto in productos:
                nombre_lower = producto.nombre.lower()
                
                # Coincidencia exacta del nombre
                if nombre_lower in mensaje_lower:
                    producto_encontrado = producto
                    break
                
                # Coincidencia por palabras clave del nombre
                palabras_producto = nombre_lower.split()
                if len(palabras_producto) > 1:
                    if all(palabra in mensaje_lower for palabra in palabras_producto):
                        producto_encontrado = producto
                        break
            
            if producto_encontrado:
                # Verificar stock
                if producto_encontrado.stock < cantidad:
                    return {
                        "error": f"Lo siento, solo tenemos {producto_encontrado.stock} unidades disponibles de {producto_encontrado.nombre}"
                    }, None
                
                return {
                    "id": producto_encontrado.id,
                    "nombre": producto_encontrado.nombre,
                    "precio": producto_encontrado.precio,
                    "stock": producto_encontrado.stock
                }, cantidad
            
            return None, None
            
        except Exception as e:
            logger.error(f"[RAGVentas] Error extrayendo producto y cantidad: {e}")
            return {"error": "Error procesando producto y cantidad"}, None

    @staticmethod
    async def obtener_estadisticas_ventas(db: AsyncSession) -> Dict[str, Any]:
        """Obtiene estadísticas de ventas para reporting"""
        try:
            from sqlalchemy import func
            
            # Total de ventas
            result = await db.execute(select(func.count(Venta.id)))
            total_ventas = result.scalar()
            
            # Ventas por estado
            estados = {}
            result = await db.execute(
                select(Venta.estado, func.count(Venta.id))
                .group_by(Venta.estado)
            )
            for estado, count in result.all():
                if estado:
                    estados[estado] = count
            
            # Producto más vendido
            result = await db.execute(
                select(Venta.producto_id, Producto.nombre, func.count(Venta.id).label('total'))
                .join(Producto, Venta.producto_id == Producto.id)
                .group_by(Venta.producto_id, Producto.nombre)
                .order_by(func.count(Venta.id).desc())
                .limit(1)
            )
            
            producto_top = result.first()
            
            return {
                "total_ventas": total_ventas,
                "ventas_por_estado": estados,
                "producto_mas_vendido": {
                    "nombre": producto_top.nombre if producto_top else "N/A",
                    "id": producto_top.producto_id if producto_top else None
                },
                "sistema_funcionando": True
            }
            
        except Exception as e:
            logger.error(f"[RAGVentas] Error obteniendo estadísticas: {e}")
            return {
                "total_ventas": 0,
                "ventas_por_estado": {},
                "producto_mas_vendido": {"nombre": "N/A", "id": None},
                "sistema_funcionando": False,
                "error": str(e)
            } 