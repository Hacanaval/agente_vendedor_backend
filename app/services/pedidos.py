from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.mensaje import Mensaje
import json
import logging

class PedidoManager:
    """Maneja el estado de pedidos y recolección de datos del cliente"""
    
    CAMPOS_REQUERIDOS = [
        "nombre_completo",
        "cedula", 
        "telefono",
        "direccion",
        "barrio",
        "indicaciones_adicionales"
    ]
    
    @staticmethod
    async def obtener_estado_pedido(chat_id: str, db: AsyncSession) -> Dict:
        """Obtiene el estado actual del pedido para un chat"""
        try:
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje = result.scalar_one_or_none()
            
            if not mensaje or not mensaje.metadatos:
                return {"tiene_pedido": False}
            
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
            
            return {
                "tiene_pedido": True,
                "estado": mensaje.estado_venta,
                "productos": metadatos.get("productos", []),
                "datos_cliente": metadatos.get("datos_cliente", {}),
                "campos_faltantes": PedidoManager._obtener_campos_faltantes(metadatos.get("datos_cliente", {}))
            }
        except Exception as e:
            logging.error(f"Error obteniendo estado de pedido: {e}")
            return {"tiene_pedido": False}
    
    @staticmethod
    def _obtener_campos_faltantes(datos_cliente: Dict) -> List[str]:
        """Obtiene los campos que faltan por recolectar"""
        return [campo for campo in PedidoManager.CAMPOS_REQUERIDOS if not datos_cliente.get(campo)]
    
    @staticmethod
    async def agregar_producto_pedido(chat_id: str, producto: str, cantidad: int, precio: float, db: AsyncSession) -> Dict:
        """Agrega un producto al pedido actual o crea uno nuevo"""
        try:
            estado_actual = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            nuevo_producto = {
                "producto": producto,
                "cantidad": cantidad,
                "precio": precio,
                "total": cantidad * precio
            }
            
            if estado_actual["tiene_pedido"]:
                # Actualizar pedido existente
                productos = estado_actual["productos"]
                productos.append(nuevo_producto)
                
                # Buscar el último mensaje de pedido
                result = await db.execute(
                    select(Mensaje)
                    .where(
                        Mensaje.chat_id == chat_id,
                        Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
                    )
                    .order_by(Mensaje.timestamp.desc())
                    .limit(1)
                )
                mensaje = result.scalar_one()
                
                metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
                metadatos["productos"] = productos
                mensaje.metadatos = metadatos
                
            else:
                # Crear nuevo pedido
                metadatos = {
                    "productos": [nuevo_producto],
                    "datos_cliente": {}
                }
                
                mensaje = Mensaje(
                    chat_id=chat_id,
                    remitente="sistema",
                    mensaje=f"Pedido iniciado: {producto} x{cantidad}",
                    estado_venta="pendiente",
                    tipo_mensaje="venta",
                    metadatos=metadatos
                )
                db.add(mensaje)
            
            await db.commit()
            
            total_pedido = sum(p["total"] for p in metadatos["productos"])
            
            return {
                "exito": True,
                "productos": metadatos["productos"],
                "total": total_pedido
            }
            
        except Exception as e:
            logging.error(f"Error agregando producto al pedido: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def actualizar_datos_cliente(chat_id: str, campo: str, valor: str, db: AsyncSession) -> Dict:
        """Actualiza un campo de datos del cliente"""
        try:
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje = result.scalar_one_or_none()
            
            if not mensaje:
                return {"exito": False, "error": "No hay pedido activo"}
            
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
            
            if "datos_cliente" not in metadatos:
                metadatos["datos_cliente"] = {}
            
            metadatos["datos_cliente"][campo] = valor
            mensaje.metadatos = metadatos
            mensaje.estado_venta = "recolectando_datos"
            
            campos_faltantes = PedidoManager._obtener_campos_faltantes(metadatos["datos_cliente"])
            
            await db.commit()
            
            return {
                "exito": True,
                "campos_faltantes": campos_faltantes,
                "datos_completos": len(campos_faltantes) == 0
            }
            
        except Exception as e:
            logging.error(f"Error actualizando datos del cliente: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def finalizar_pedido(chat_id: str, db: AsyncSession) -> Dict:
        """Finaliza el pedido marcándolo como cerrado"""
        try:
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje = result.scalar_one_or_none()
            
            if not mensaje:
                return {"exito": False, "error": "No hay pedido activo"}
            
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
            campos_faltantes = PedidoManager._obtener_campos_faltantes(metadatos.get("datos_cliente", {}))
            
            if campos_faltantes:
                return {"exito": False, "error": "Faltan datos del cliente", "campos_faltantes": campos_faltantes}
            
            mensaje.estado_venta = "cerrada"
            await db.commit()
            
            return {
                "exito": True,
                "pedido": metadatos
            }
            
        except Exception as e:
            logging.error(f"Error finalizando pedido: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def mostrar_pedido_actual(chat_id: str, db: AsyncSession) -> Optional[Dict]:
        """Muestra el resumen del pedido actual"""
        try:
            estado = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            if not estado["tiene_pedido"]:
                return None
            
            productos = estado["productos"]
            datos_cliente = estado["datos_cliente"]
            total = sum(p["total"] for p in productos)
            
            resumen = {
                "productos": productos,
                "total": total,
                "datos_cliente": datos_cliente,
                "estado": estado["estado"],
                "campos_faltantes": estado["campos_faltantes"]
            }
            
            return resumen
            
        except Exception as e:
            logging.error(f"Error mostrando pedido actual: {e}")
            return None 