from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete   # solo select y delete aquí
from sqlalchemy import func                    # func siempre desde sqlalchemy base
from app.core.database import get_db
from app.models.logs import Logs
from app.models.producto import Producto
from app.models.venta import Venta
from typing import List, Optional
import logging
from datetime import datetime

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/", response_model=List[dict])
async def listar_logs(
    modelo: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Logs).where(Logs.empresa_id == 1)  # TODO: Volver a multiempresa en producción
        if modelo:
            query = query.where(Logs.modelo == modelo)
        if accion:
            query = query.where(Logs.accion == accion)
        result = await db.execute(query.order_by(Logs.fecha.desc()))
        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "empresa_id": log.empresa_id,
                "usuario_id": getattr(log, "usuario_id", None),
                "modelo": log.modelo,
                "accion": log.accion,
                "detalle": log.detalle,
                "fecha": log.fecha
            }
            for log in logs
        ]
    except Exception as e:
        logging.error(f"Error al listar logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al listar logs")

@router.get("/metrics/uso", tags=["metrics"])
async def metricas_uso(
    fecha_inicio: Optional[datetime] = Query(None),
    fecha_fin: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve métricas de uso (consultas de chat y ventas) por empresa.
    """
    # TODO: Volver a proteger por rol en producción
    try:
        filtros = [Logs.empresa_id == 1]
        if fecha_inicio:
            filtros.append(Logs.fecha >= fecha_inicio)
        if fecha_fin:
            filtros.append(Logs.fecha <= fecha_fin)
        # Consultas de chat
        query_chat = select(func.count()).where(
            Logs.modelo == "chat",
            Logs.accion == "consulta_rag",
            *filtros
        )
        result_chat = await db.execute(query_chat)
        total_chat = result_chat.scalar() or 0
        # Ventas
        query_ventas = select(func.count()).where(
            Logs.modelo == "venta",
            Logs.accion == "vendido",
            *filtros
        )
        result_ventas = await db.execute(query_ventas)
        total_ventas = result_ventas.scalar() or 0
        return {
            "empresa_id": 1,
            "total_consultas_chat": total_chat,
            "total_ventas": total_ventas,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }
    except Exception as e:
        logging.error(f"Error al obtener métricas de uso: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al obtener métricas de uso")

@router.post("/admin/reset_empresa", tags=["admin"])
async def reset_empresa(
    db: AsyncSession = Depends(get_db)
):
    """
    Borra todos los productos, ventas y logs de la empresa actual. Solo admin.
    """
    # TODO: Volver a proteger por rol en producción
    try:
        empresa_id = 1
        # Borrar ventas
        ventas_del = await db.execute(delete(Venta).where(Venta.empresa_id == empresa_id))
        # Borrar productos
        productos_del = await db.execute(delete(Producto).where(Producto.empresa_id == empresa_id))
        # Borrar logs
        logs_del = await db.execute(delete(Logs).where(Logs.empresa_id == empresa_id))
        await db.commit()
        return {
            "empresa_id": empresa_id,
            "ventas_borradas": ventas_del.rowcount,
            "productos_borrados": productos_del.rowcount,
            "logs_borrados": logs_del.rowcount
        }
    except Exception as e:
        logging.error(f"Error al resetear empresa: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al resetear empresa")

@router.post("/admin/reset_global", tags=["admin"])
async def reset_global(
    db: AsyncSession = Depends(get_db)
):
    """
    Borra TODOS los productos, ventas y logs de TODAS las empresas. Solo superadmin (email == 'hacanaval@hotmail.com' o 'hugocanaval34@gmail.com').
    """
    # TODO: Volver a proteger por superadmin en producción
    try:
        ventas_del = await db.execute(delete(Venta))
        productos_del = await db.execute(delete(Producto))
        logs_del = await db.execute(delete(Logs))
        await db.commit()
        return {
            "reset_global": True,
            "ventas_borradas": ventas_del.rowcount,
            "productos_borrados": productos_del.rowcount,
            "logs_borrados": logs_del.rowcount
        }
    except Exception as e:
        logging.error(f"Error en reset global: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en reset global")
