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
        
        # ✅ CORREGIDO: Manejo más robusto de consultas con verificación de existencia
        try:
            # Ventas totales en el período - verificar que tabla Venta existe
            result_ventas = await db.execute(
                select(
                    func.count(Venta.id).label("total_ventas"),
                    func.sum(Venta.total).label("ingresos_totales"),
                    func.avg(Venta.total).label("ticket_promedio")
                ).where(Venta.fecha >= fecha_inicio)  # Usar 'fecha' en lugar de 'timestamp'
            )
            metricas_ventas = result_ventas.first()
        except Exception as e:
            logging.warning(f"Error consultando ventas: {e}. Usando valores por defecto.")
            # Valores por defecto si no hay tabla de ventas o está vacía
            metricas_ventas = type('MockMetricas', (), {
                'total_ventas': 0,
                'ingresos_totales': 0.0,
                'ticket_promedio': 0.0
            })()
        
        # Productos más vendidos - con manejo de errores
        productos_top = []
        try:
            result_productos = await db.execute(
                select(
                    Producto.nombre,
                    func.sum(Venta.cantidad).label("cantidad_vendida"),
                    func.sum(Venta.total).label("ingresos_producto")
                )
                .join(Venta, Producto.id == Venta.producto_id)
                .where(Venta.fecha >= fecha_inicio)
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
                for row in result_productos.all()
            ]
        except Exception as e:
            logging.warning(f"Error consultando productos top: {e}")
            productos_top = []
        
        # Ventas por día - con manejo de errores
        ventas_diarias = []
        try:
            result_diarias = await db.execute(
                select(
                    func.date(Venta.fecha).label("fecha"),
                    func.count(Venta.id).label("ventas"),
                    func.sum(Venta.total).label("ingresos")
                )
                .where(Venta.fecha >= datetime.now() - timedelta(days=7))
                .group_by(func.date(Venta.fecha))
                .order_by("fecha")
            )
            ventas_diarias = [
                {
                    "fecha": row.fecha.isoformat() if hasattr(row.fecha, 'isoformat') else str(row.fecha),
                    "ventas": row.ventas,
                    "ingresos": float(row.ingresos)
                }
                for row in result_diarias.all()
            ]
        except Exception as e:
            logging.warning(f"Error consultando ventas diarias: {e}")
            ventas_diarias = []
        
        # Conversaciones activas
        conversaciones_activas = 0
        try:
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
        except Exception as e:
            logging.warning(f"Error consultando conversaciones activas: {e}")
            conversaciones_activas = 0
        
        return {
            "periodo": f"Últimos {dias} días",
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": datetime.now().isoformat(),
            "metricas": {
                "total_ventas": getattr(metricas_ventas, 'total_ventas', 0) or 0,
                "ingresos_totales": float(getattr(metricas_ventas, 'ingresos_totales', 0) or 0),
                "ticket_promedio": float(getattr(metricas_ventas, 'ticket_promedio', 0) or 0),
                "conversaciones_activas": conversaciones_activas
            },
            "productos_top": productos_top,
            "ventas_diarias": ventas_diarias,
            "status": "ok"
        }
        
    except Exception as e:
        logging.error(f"Error en dashboard de ventas: {str(e)}")
        # Retornar estructura mínima en caso de error
        return {
            "periodo": f"Últimos {dias} días",
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": datetime.now().isoformat(),
            "metricas": {
                "total_ventas": 0,
                "ingresos_totales": 0.0,
                "ticket_promedio": 0.0,
                "conversaciones_activas": 0
            },
            "productos_top": [],
            "ventas_diarias": [],
            "status": "error",
            "error": str(e)
        }

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
            # ✅ CORREGIDO: Calcular ventas del último mes con manejo de errores
            ventas_mes_data = {"cantidad": 0, "transacciones": 0}
            try:
                fecha_mes = datetime.now() - timedelta(days=30)
                result_ventas = await db.execute(
                    select(
                        func.sum(Venta.cantidad).label("vendido_mes"),
                        func.count(Venta.id).label("transacciones_mes")
                    ).where(
                        and_(
                            Venta.producto_id == row.id,
                            Venta.fecha >= fecha_mes  # Usar 'fecha' en lugar de 'timestamp'
                        )
                    )
                )
                ventas_mes = result_ventas.first()
                if ventas_mes:
                    ventas_mes_data = {
                        "cantidad": ventas_mes.vendido_mes or 0,
                        "transacciones": ventas_mes.transacciones_mes or 0
                    }
            except Exception as e:
                logging.warning(f"Error calculando ventas para producto {row.id}: {e}")
                # Mantener valores por defecto
            
            producto_data = {
                "id": row.id,
                "nombre": row.nombre,
                "precio": float(row.precio),
                "stock": row.stock,
                "activo": row.activo,
                "descripcion": row.descripcion or "",
                "estado_stock": "bajo" if row.stock <= 10 else "normal" if row.stock <= 50 else "alto",
                "ventas_mes": ventas_mes_data
            }
            
            productos.append(producto_data)
        
        return productos
        
    except Exception as e:
        logging.error(f"Error obteniendo inventario: {str(e)}")
        # Retornar lista vacía en caso de error
        return []

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