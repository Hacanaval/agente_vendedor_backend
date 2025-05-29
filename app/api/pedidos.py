from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from app.core.database import get_db
from app.models.mensaje import Mensaje
from app.services.pedidos import PedidoManager
from typing import List, Optional
import json
from datetime import datetime, timedelta
from pydantic import BaseModel

# ✅ NUEVO: Schema para crear pedidos
class ProductoPedido(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: float

class PedidoCreate(BaseModel):
    chat_id: str
    productos: List[ProductoPedido]
    cliente_cedula: str
    cliente_nombre: str
    cliente_telefono: str
    observaciones: Optional[str] = None

router = APIRouter(prefix="/pedidos", tags=["pedidos"])

# ✅ NUEVO: Endpoint POST para crear pedidos
@router.post("/", summary="Crear nuevo pedido")
async def crear_pedido(
    data: PedidoCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo pedido desde el frontend"""
    try:
        # Calcular total
        total = sum(p.cantidad * p.precio_unitario for p in data.productos)
        
        # Preparar datos de productos
        productos_data = [
            {
                "producto_id": p.producto_id,
                "cantidad": p.cantidad,
                "precio_unitario": p.precio_unitario,
                "total": p.cantidad * p.precio_unitario
            }
            for p in data.productos
        ]
        
        # Preparar metadatos
        metadatos = {
            "productos": productos_data,
            "datos_cliente": {
                "cedula": data.cliente_cedula,
                "nombre": data.cliente_nombre,
                "telefono": data.cliente_telefono
            },
            "total": total,
            "observaciones": data.observaciones or "",
            "origen": "frontend"
        }
        
        # Crear mensaje de pedido
        mensaje = Mensaje(
            chat_id=data.chat_id,
            remitente="cliente",
            mensaje=f"Pedido creado desde frontend - Total: ${total}",
            tipo_mensaje="venta",
            estado_venta="pendiente",
            metadatos=metadatos,
            timestamp=datetime.now()
        )
        
        db.add(mensaje)
        await db.flush()
        await db.refresh(mensaje)
        await db.commit()
        
        return {
            "id": mensaje.id,
            "chat_id": data.chat_id,
            "estado": "pendiente",
            "total": total,
            "productos": productos_data,
            "cliente": {
                "cedula": data.cliente_cedula,
                "nombre": data.cliente_nombre,
                "telefono": data.cliente_telefono
            },
            "fecha": mensaje.timestamp.isoformat(),
            "message": "Pedido creado exitosamente"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear pedido: {str(e)}")

@router.get("/", summary="Listar todos los pedidos")
async def listar_pedidos(
    estado: Optional[str] = Query(None, description="Filtrar por estado: pendiente, recolectando_datos, cerrada, cancelada"),
    chat_id: Optional[str] = Query(None, description="Filtrar por chat_id específico"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    limit: int = Query(50, description="Límite de resultados"),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los pedidos con filtros opcionales"""
    try:
        query = select(Mensaje).where(
            Mensaje.tipo_mensaje == "venta",
            Mensaje.estado_venta.in_(["pendiente", "recolectando_datos", "cerrada", "cancelada"])
        )
        
        # Aplicar filtros
        if estado:
            query = query.where(Mensaje.estado_venta == estado)
        
        if chat_id:
            query = query.where(Mensaje.chat_id == chat_id)
        
        if fecha_desde:
            fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            query = query.where(Mensaje.timestamp >= fecha_desde_dt)
        
        if fecha_hasta:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Mensaje.timestamp < fecha_hasta_dt)
        
        query = query.order_by(Mensaje.timestamp.desc()).limit(limit)
        
        result = await db.execute(query)
        mensajes = result.scalars().all()
        
        pedidos = []
        for mensaje in mensajes:
            try:
                metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos or "{}")
                productos = metadatos.get("productos", [])
                datos_cliente = metadatos.get("datos_cliente", {})
                
                total = sum(p.get("total", 0) for p in productos)
                
                pedido = {
                    "id": mensaje.id,
                    "chat_id": mensaje.chat_id,
                    "estado": mensaje.estado_venta,
                    "fecha": mensaje.timestamp.isoformat(),
                    "productos": productos,
                    "datos_cliente": datos_cliente,
                    "total": total,
                    "cantidad_productos": len(productos)
                }
                pedidos.append(pedido)
            except Exception as e:
                # Si hay error parseando un pedido, lo saltamos
                continue
        
        return {
            "pedidos": pedidos,
            "total_encontrados": len(pedidos),
            "filtros_aplicados": {
                "estado": estado,
                "chat_id": chat_id,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar pedidos: {str(e)}")

@router.get("/{chat_id}", summary="Obtener pedidos de un chat específico")
async def obtener_pedidos_chat(
    chat_id: str,
    incluir_historial: bool = Query(False, description="Incluir historial completo de mensajes"),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene todos los pedidos de un chat específico"""
    try:
        # Obtener pedido actual
        pedido_actual = await PedidoManager.mostrar_pedido_actual(chat_id, db)
        
        # Obtener historial de pedidos cerrados
        query = select(Mensaje).where(
            Mensaje.chat_id == chat_id,
            Mensaje.tipo_mensaje == "venta",
            Mensaje.estado_venta == "cerrada"
        ).order_by(Mensaje.timestamp.desc())
        
        result = await db.execute(query)
        pedidos_cerrados = result.scalars().all()
        
        historial_pedidos = []
        for mensaje in pedidos_cerrados:
            try:
                metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos or "{}")
                productos = metadatos.get("productos", [])
                datos_cliente = metadatos.get("datos_cliente", {})
                total = sum(p.get("total", 0) for p in productos)
                
                pedido = {
                    "id": mensaje.id,
                    "fecha": mensaje.timestamp.isoformat(),
                    "productos": productos,
                    "datos_cliente": datos_cliente,
                    "total": total,
                    "estado": "cerrada"
                }
                historial_pedidos.append(pedido)
            except:
                continue
        
        respuesta = {
            "chat_id": chat_id,
            "pedido_actual": pedido_actual,
            "historial_pedidos": historial_pedidos,
            "total_pedidos_cerrados": len(historial_pedidos)
        }
        
        # Incluir historial completo si se solicita
        if incluir_historial:
            query_historial = select(Mensaje).where(
                Mensaje.chat_id == chat_id
            ).order_by(Mensaje.timestamp.desc()).limit(50)
            
            result_historial = await db.execute(query_historial)
            mensajes_historial = result_historial.scalars().all()
            
            respuesta["historial_conversacion"] = [
                {
                    "id": m.id,
                    "remitente": m.remitente,
                    "mensaje": m.mensaje,
                    "timestamp": m.timestamp.isoformat(),
                    "tipo_mensaje": m.tipo_mensaje,
                    "estado_venta": m.estado_venta
                }
                for m in mensajes_historial
            ]
        
        return respuesta
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener pedidos del chat: {str(e)}")

@router.put("/{chat_id}/estado", summary="Actualizar estado de pedido")
async def actualizar_estado_pedido(
    chat_id: str,
    nuevo_estado: str,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el estado de un pedido activo"""
    try:
        estados_validos = ["pendiente", "recolectando_datos", "cerrada", "cancelada"]
        if nuevo_estado not in estados_validos:
            raise HTTPException(
                status_code=400, 
                detail=f"Estado inválido. Estados válidos: {', '.join(estados_validos)}"
            )
        
        # Buscar pedido activo
        result = await db.execute(
            select(Mensaje).where(
                Mensaje.chat_id == chat_id,
                Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
            ).order_by(Mensaje.timestamp.desc()).limit(1)
        )
        mensaje = result.scalar_one_or_none()
        
        if not mensaje:
            raise HTTPException(status_code=404, detail="No se encontró pedido activo para este chat")
        
        mensaje.estado_venta = nuevo_estado
        await db.commit()
        
        return {
            "mensaje": f"Estado del pedido actualizado a '{nuevo_estado}'",
            "chat_id": chat_id,
            "pedido_id": mensaje.id,
            "nuevo_estado": nuevo_estado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar estado: {str(e)}")

@router.get("/estadisticas/resumen", summary="Estadísticas de pedidos")
async def estadisticas_pedidos(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas generales de pedidos"""
    try:
        query = select(Mensaje).where(
            Mensaje.tipo_mensaje == "venta",
            Mensaje.estado_venta.in_(["pendiente", "recolectando_datos", "cerrada", "cancelada"])
        )
        
        # Aplicar filtros de fecha
        if fecha_desde:
            fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            query = query.where(Mensaje.timestamp >= fecha_desde_dt)
        
        if fecha_hasta:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Mensaje.timestamp < fecha_hasta_dt)
        
        result = await db.execute(query)
        mensajes = result.scalars().all()
        
        # Calcular estadísticas
        estadisticas = {
            "total_pedidos": len(mensajes),
            "por_estado": {
                "pendiente": 0,
                "recolectando_datos": 0,
                "cerrada": 0,
                "cancelada": 0
            },
            "valor_total_ventas": 0,
            "promedio_por_pedido": 0,
            "chats_unicos": set()
        }
        
        for mensaje in mensajes:
            # Contar por estado
            estadisticas["por_estado"][mensaje.estado_venta] += 1
            
            # Agregar chat único
            estadisticas["chats_unicos"].add(mensaje.chat_id)
            
            # Calcular valores
            try:
                metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos or "{}")
                productos = metadatos.get("productos", [])
                total_pedido = sum(p.get("total", 0) for p in productos)
                estadisticas["valor_total_ventas"] += total_pedido
            except:
                continue
        
        # Calcular promedio
        if estadisticas["por_estado"]["cerrada"] > 0:
            estadisticas["promedio_por_pedido"] = estadisticas["valor_total_ventas"] / estadisticas["por_estado"]["cerrada"]
        
        # Convertir set a número
        estadisticas["chats_unicos"] = len(estadisticas["chats_unicos"])
        
        return estadisticas
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular estadísticas: {str(e)}")

@router.delete("/{chat_id}/cancelar", summary="Cancelar pedido activo")
async def cancelar_pedido(
    chat_id: str,
    motivo: Optional[str] = Query(None, description="Motivo de cancelación"),
    db: AsyncSession = Depends(get_db)
):
    """Cancela un pedido activo"""
    try:
        # Buscar pedido activo
        result = await db.execute(
            select(Mensaje).where(
                Mensaje.chat_id == chat_id,
                Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"])
            ).order_by(Mensaje.timestamp.desc()).limit(1)
        )
        mensaje = result.scalar_one_or_none()
        
        if not mensaje:
            raise HTTPException(status_code=404, detail="No se encontró pedido activo para cancelar")
        
        # Actualizar estado y agregar motivo
        mensaje.estado_venta = "cancelada"
        
        if motivo:
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos or "{}")
            metadatos["motivo_cancelacion"] = motivo
            metadatos["fecha_cancelacion"] = datetime.now().isoformat()
            mensaje.metadatos = metadatos
        
        await db.commit()
        
        return {
            "mensaje": "Pedido cancelado exitosamente",
            "chat_id": chat_id,
            "pedido_id": mensaje.id,
            "motivo": motivo
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cancelar pedido: {str(e)}") 