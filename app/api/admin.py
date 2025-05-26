from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_
from app.core.database import get_db
from typing import Dict, Any, List, Optional
from app.models.mensaje import Mensaje
from app.models.venta import Venta
from app.models.producto import Producto
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/admin", tags=["admin"])

# ----------- Dashboard de Ventas -----------

@router.get("/dashboard/ventas", response_model=Dict[str, Any])
async def dashboard_ventas(
    dias: int = Query(default=30, description="Número de días hacia atrás"),
    db: AsyncSession = Depends(get_db)
):
    """
    Dashboard principal de ventas con métricas y estadísticas
    """
    try:
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        # Ventas totales en el período
        result_ventas = await db.execute(
            select(
                func.count(Venta.id).label("total_ventas"),
                func.sum(Venta.total).label("ingresos_totales"),
                func.avg(Venta.total).label("ticket_promedio")
            ).where(Venta.timestamp >= fecha_inicio)
        )
        metricas_ventas = result_ventas.first()
        
        # Productos más vendidos
        result_productos = await db.execute(
            select(
                Producto.nombre,
                func.sum(Venta.cantidad).label("cantidad_vendida"),
                func.sum(Venta.total).label("ingresos_producto")
            )
            .join(Venta, Producto.id == Venta.producto_id)
            .where(Venta.timestamp >= fecha_inicio)
            .group_by(Producto.id, Producto.nombre)
            .order_by(desc("cantidad_vendida"))
            .limit(10)
        )
        productos_top = [
            {
                "producto": row.nombre,
                "cantidad_vendida": row.cantidad_vendida,
                "ingresos": float(row.ingresos_producto)
            }
            for row in result_productos.scalars().all()
        ]
        
        # Ventas por día (últimos 7 días)
        result_diarias = await db.execute(
            select(
                func.date(Venta.timestamp).label("fecha"),
                func.count(Venta.id).label("ventas"),
                func.sum(Venta.total).label("ingresos")
            )
            .where(Venta.timestamp >= datetime.now() - timedelta(days=7))
            .group_by(func.date(Venta.timestamp))
            .order_by("fecha")
        )
        ventas_diarias = [
            {
                "fecha": row.fecha.isoformat(),
                "ventas": row.ventas,
                "ingresos": float(row.ingresos)
            }
            for row in result_diarias.scalars().all()
        ]
        
        # Conversaciones activas (con pedidos pendientes)
        result_activas = await db.execute(
            select(func.count(func.distinct(Mensaje.chat_id)))
            .where(
                and_(
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"]),
                    Mensaje.timestamp >= fecha_inicio
                )
            )
        )
        conversaciones_activas = result_activas.scalar() or 0
        
        return {
            "periodo": f"Últimos {dias} días",
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": datetime.now().isoformat(),
            "metricas": {
                "total_ventas": metricas_ventas.total_ventas or 0,
                "ingresos_totales": float(metricas_ventas.ingresos_totales or 0),
                "ticket_promedio": float(metricas_ventas.ticket_promedio or 0),
                "conversaciones_activas": conversaciones_activas
            },
            "productos_top": productos_top,
            "ventas_diarias": ventas_diarias
        }
        
    except Exception as e:
        logging.error(f"Error en dashboard de ventas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener datos del dashboard")

# ----------- Lista de Ventas -----------

@router.get("/ventas", response_model=List[Dict[str, Any]])
async def listar_ventas(
    limite: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    estado: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas las ventas con paginación y filtros
    """
    try:
        query = select(
            Venta.id,
            Venta.cantidad,
            Venta.total,
            Venta.estado,
            Venta.timestamp,
            Venta.chat_id,
            Venta.detalle,
            Producto.nombre.label("producto_nombre")
        ).join(Producto, Venta.producto_id == Producto.id)
        
        if estado:
            query = query.where(Venta.estado == estado)
        
        query = query.order_by(desc(Venta.timestamp)).offset(offset).limit(limite)
        
        result = await db.execute(query)
        ventas = []
        
        for row in result.all():
            venta_data = {
                "id": row.id,
                "producto": row.producto_nombre,
                "cantidad": row.cantidad,
                "total": float(row.total),
                "estado": row.estado,
                "timestamp": row.timestamp.isoformat(),
                "chat_id": row.chat_id,
                "cliente": {}
            }
            
            # Extraer datos del cliente del detalle
            if row.detalle and isinstance(row.detalle, dict):
                datos_cliente = row.detalle.get("datos_cliente", {})
                venta_data["cliente"] = {
                    "nombre": datos_cliente.get("nombre_completo", ""),
                    "telefono": datos_cliente.get("telefono", ""),
                    "direccion": datos_cliente.get("direccion", "")
                }
            
            ventas.append(venta_data)
        
        return ventas
        
    except Exception as e:
        logging.error(f"Error listando ventas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener lista de ventas")

# ----------- Conversaciones -----------

@router.get("/conversaciones", response_model=List[Dict[str, Any]])
async def listar_conversaciones(
    limite: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    estado: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista conversaciones con información de pedidos
    """
    try:
        # Obtener conversaciones únicas con su último mensaje
        subquery = (
            select(
                Mensaje.chat_id,
                func.max(Mensaje.timestamp).label("ultimo_mensaje")
            )
            .group_by(Mensaje.chat_id)
            .subquery()
        )
        
        query = (
            select(
                Mensaje.chat_id,
                Mensaje.estado_venta,
                Mensaje.timestamp,
                Mensaje.metadatos,
                func.count(func.distinct(Mensaje.id)).label("total_mensajes")
            )
            .join(subquery, and_(
                Mensaje.chat_id == subquery.c.chat_id,
                Mensaje.timestamp == subquery.c.ultimo_mensaje
            ))
            .group_by(Mensaje.chat_id, Mensaje.estado_venta, Mensaje.timestamp, Mensaje.metadatos)
        )
        
        if estado:
            query = query.where(Mensaje.estado_venta == estado)
        
        query = query.order_by(desc(Mensaje.timestamp)).offset(offset).limit(limite)
        
        result = await db.execute(query)
        conversaciones = []
        
        for row in result.all():
            conv_data = {
                "chat_id": row.chat_id,
                "estado": row.estado_venta,
                "ultimo_mensaje": row.timestamp.isoformat(),
                "total_mensajes": row.total_mensajes,
                "pedido": None
            }
            
            # Extraer información del pedido si existe
            if row.metadatos and isinstance(row.metadatos, dict):
                productos = row.metadatos.get("productos", [])
                if productos:
                    total_pedido = sum(p.get("total", 0) for p in productos)
                    conv_data["pedido"] = {
                        "productos": len(productos),
                        "total": total_pedido,
                        "items": productos
                    }
            
            conversaciones.append(conv_data)
        
        return conversaciones
        
    except Exception as e:
        logging.error(f"Error listando conversaciones: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener conversaciones")

# ----------- Inventario -----------

@router.get("/inventario", response_model=List[Dict[str, Any]])
async def estado_inventario(
    limite: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    stock_bajo: bool = Query(default=False, description="Solo productos con stock bajo"),
    db: AsyncSession = Depends(get_db)
):
    """
    Estado actual del inventario
    """
    try:
        query = select(
            Producto.id,
            Producto.nombre,
            Producto.precio,
            Producto.stock,
            Producto.activo,
            Producto.descripcion
        )
        
        if stock_bajo:
            query = query.where(Producto.stock <= 10)  # Definir stock bajo como <= 10
        
        query = query.where(Producto.activo == True).order_by(Producto.nombre).offset(offset).limit(limite)
        
        result = await db.execute(query)
        productos = []
        
        for row in result.all():
            # Calcular ventas del último mes para este producto
            fecha_mes = datetime.now() - timedelta(days=30)
            result_ventas = await db.execute(
                select(
                    func.sum(Venta.cantidad).label("vendido_mes"),
                    func.count(Venta.id).label("transacciones_mes")
                ).where(
                    and_(
                        Venta.producto_id == row.id,
                        Venta.timestamp >= fecha_mes
                    )
                )
            )
            ventas_mes = result_ventas.first()
            
            producto_data = {
                "id": row.id,
                "nombre": row.nombre,
                "precio": float(row.precio),
                "stock": row.stock,
                "activo": row.activo,
                "descripcion": row.descripcion,
                "estado_stock": "bajo" if row.stock <= 10 else "normal" if row.stock <= 50 else "alto",
                "ventas_mes": {
                    "cantidad": ventas_mes.vendido_mes or 0,
                    "transacciones": ventas_mes.transacciones_mes or 0
                }
            }
            
            productos.append(producto_data)
        
        return productos
        
    except Exception as e:
        logging.error(f"Error obteniendo inventario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener estado del inventario")

# ----------- Estadísticas Generales -----------

@router.get("/estadisticas", response_model=Dict[str, Any])
async def estadisticas_generales(db: AsyncSession = Depends(get_db)):
    """
    Estadísticas generales del sistema
    """
    try:
        # Total de productos activos
        result_productos = await db.execute(
            select(func.count(Producto.id)).where(Producto.activo == True)
        )
        total_productos = result_productos.scalar()
        
        # Total de conversaciones únicas
        result_conversaciones = await db.execute(
            select(func.count(func.distinct(Mensaje.chat_id)))
        )
        total_conversaciones = result_conversaciones.scalar()
        
        # Total de ventas
        result_ventas_total = await db.execute(
            select(
                func.count(Venta.id).label("total"),
                func.sum(Venta.total).label("ingresos")
            )
        )
        ventas_total = result_ventas_total.first()
        
        # Productos con stock bajo
        result_stock_bajo = await db.execute(
            select(func.count(Producto.id)).where(
                and_(Producto.activo == True, Producto.stock <= 10)
            )
        )
        productos_stock_bajo = result_stock_bajo.scalar()
        
        # Conversaciones activas (últimas 24 horas)
        fecha_24h = datetime.now() - timedelta(hours=24)
        result_activas = await db.execute(
            select(func.count(func.distinct(Mensaje.chat_id)))
            .where(Mensaje.timestamp >= fecha_24h)
        )
        conversaciones_24h = result_activas.scalar()
        
        return {
            "productos": {
                "total_activos": total_productos,
                "stock_bajo": productos_stock_bajo
            },
            "conversaciones": {
                "total": total_conversaciones,
                "activas_24h": conversaciones_24h
            },
            "ventas": {
                "total": ventas_total.total or 0,
                "ingresos_totales": float(ventas_total.ingresos or 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas")

# ----------- Health Check -----------

@router.get("/health")
async def admin_health_check():
    """Health check para endpoints de administración"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "admin_api"
    } 