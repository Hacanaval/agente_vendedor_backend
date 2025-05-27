from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
import logging
import io

from app.core.database import get_db
from app.services.csv_exporter import CSVExporter

router = APIRouter(prefix="/exportar", tags=["exportar"])

@router.get("/inventario")
async def exportar_inventario_csv(
    incluir_inactivos: bool = Query(False, description="Incluir productos inactivos"),
    solo_con_stock: bool = Query(False, description="Solo productos con stock > 0"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta el inventario completo a CSV.
    
    - **incluir_inactivos**: Incluir productos marcados como inactivos
    - **solo_con_stock**: Solo productos que tienen stock disponible
    """
    try:
        resultado = await CSVExporter.exportar_inventario(
            db=db,
            incluir_inactivos=incluir_inactivos,
            solo_con_stock=solo_con_stock
        )
        
        if not resultado["exito"]:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error exportando inventario"))
        
        # Crear respuesta de descarga
        csv_buffer = io.StringIO(resultado["csv_content"])
        
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),  # UTF-8 con BOM para Excel
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={resultado['nombre_archivo']}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint exportar inventario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/clientes")
async def exportar_clientes_csv(
    incluir_inactivos: bool = Query(False, description="Incluir clientes inactivos"),
    con_compras: bool = Query(False, description="Solo clientes que han realizado compras"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta la base de clientes a CSV.
    
    - **incluir_inactivos**: Incluir clientes marcados como inactivos
    - **con_compras**: Solo clientes que han realizado al menos una compra
    - **fecha_desde**: Filtrar por fecha de registro desde (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar por fecha de registro hasta (formato: YYYY-MM-DD)
    """
    try:
        # Parsear fechas si se proporcionan
        fecha_desde_dt = None
        fecha_hasta_dt = None
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                # Incluir todo el día
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        resultado = await CSVExporter.exportar_clientes(
            db=db,
            incluir_inactivos=incluir_inactivos,
            con_compras=con_compras,
            fecha_desde=fecha_desde_dt,
            fecha_hasta=fecha_hasta_dt
        )
        
        if not resultado["exito"]:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error exportando clientes"))
        
        # Crear respuesta de descarga
        csv_buffer = io.StringIO(resultado["csv_content"])
        
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={resultado['nombre_archivo']}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint exportar clientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/ventas")
async def exportar_ventas_csv(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    estado: Optional[str] = Query(None, description="Filtrar por estado específico"),
    incluir_detalles_cliente: bool = Query(True, description="Incluir información del cliente"),
    incluir_detalles_producto: bool = Query(True, description="Incluir información del producto"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta las ventas a CSV con detalles completos.
    
    - **fecha_desde**: Filtrar ventas desde esta fecha (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar ventas hasta esta fecha (formato: YYYY-MM-DD)
    - **estado**: Filtrar por estado específico (completada, pendiente, etc.)
    - **incluir_detalles_cliente**: Incluir información completa del cliente
    - **incluir_detalles_producto**: Incluir información completa del producto
    """
    try:
        # Parsear fechas si se proporcionan
        fecha_desde_dt = None
        fecha_hasta_dt = None
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        resultado = await CSVExporter.exportar_ventas(
            db=db,
            fecha_desde=fecha_desde_dt,
            fecha_hasta=fecha_hasta_dt,
            estado=estado,
            incluir_detalles_cliente=incluir_detalles_cliente,
            incluir_detalles_producto=incluir_detalles_producto
        )
        
        if not resultado["exito"]:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error exportando ventas"))
        
        # Crear respuesta de descarga
        csv_buffer = io.StringIO(resultado["csv_content"])
        
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={resultado['nombre_archivo']}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint exportar ventas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/conversaciones-rag")
async def exportar_conversaciones_rag_csv(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    tipo_mensaje: Optional[str] = Query(None, description="Filtrar por tipo de mensaje"),
    solo_con_rag: bool = Query(True, description="Solo mensajes que usaron RAG"),
    incluir_metadatos: bool = Query(True, description="Incluir metadatos detallados"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta las conversaciones y consultas RAG a CSV.
    
    - **fecha_desde**: Filtrar mensajes desde esta fecha (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar mensajes hasta esta fecha (formato: YYYY-MM-DD)
    - **tipo_mensaje**: Filtrar por tipo específico (inventario, venta, contexto, cliente)
    - **solo_con_rag**: Solo incluir mensajes que utilizaron el sistema RAG
    - **incluir_metadatos**: Incluir metadatos detallados en columnas separadas
    """
    try:
        # Parsear fechas si se proporcionan
        fecha_desde_dt = None
        fecha_hasta_dt = None
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        resultado = await CSVExporter.exportar_conversaciones_rag(
            db=db,
            fecha_desde=fecha_desde_dt,
            fecha_hasta=fecha_hasta_dt,
            tipo_mensaje=tipo_mensaje,
            solo_con_rag=solo_con_rag,
            incluir_metadatos=incluir_metadatos
        )
        
        if not resultado["exito"]:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error exportando conversaciones RAG"))
        
        # Crear respuesta de descarga
        csv_buffer = io.StringIO(resultado["csv_content"])
        
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={resultado['nombre_archivo']}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint exportar conversaciones RAG: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/reporte-completo")
async def exportar_reporte_completo_csv(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde para filtrar ventas (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta para filtrar ventas (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta un reporte completo con estadísticas generales del sistema.
    
    - **fecha_desde**: Filtrar ventas desde esta fecha para estadísticas (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar ventas hasta esta fecha para estadísticas (formato: YYYY-MM-DD)
    """
    try:
        # Parsear fechas si se proporcionan
        fecha_desde_dt = None
        fecha_hasta_dt = None
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido. Use YYYY-MM-DD")
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido. Use YYYY-MM-DD")
        
        resultado = await CSVExporter.exportar_reporte_completo(
            db=db,
            fecha_desde=fecha_desde_dt,
            fecha_hasta=fecha_hasta_dt
        )
        
        if not resultado["exito"]:
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error exportando reporte completo"))
        
        # Crear respuesta de descarga
        csv_buffer = io.StringIO(resultado["csv_content"])
        
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={resultado['nombre_archivo']}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en endpoint exportar reporte completo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/info")
async def obtener_info_exportacion(db: AsyncSession = Depends(get_db)):
    """
    Obtiene información sobre los datos disponibles para exportación.
    """
    try:
        from sqlalchemy import func
        from sqlalchemy.future import select
        from app.models.producto import Producto
        from app.models.cliente import Cliente
        from app.models.venta import Venta
        from app.models.mensaje import Mensaje
        
        # Contar registros disponibles
        info = {}
        
        # Productos
        result = await db.execute(select(func.count(Producto.id)))
        info["total_productos"] = result.scalar()
        
        result = await db.execute(select(func.count(Producto.id)).where(Producto.activo == True))
        info["productos_activos"] = result.scalar()
        
        result = await db.execute(select(func.count(Producto.id)).where(Producto.stock > 0))
        info["productos_con_stock"] = result.scalar()
        
        # Clientes
        result = await db.execute(select(func.count(Cliente.cedula)))
        info["total_clientes"] = result.scalar()
        
        result = await db.execute(select(func.count(Cliente.cedula)).where(Cliente.activo == True))
        info["clientes_activos"] = result.scalar()
        
        result = await db.execute(select(func.count(Cliente.cedula)).where(Cliente.total_compras > 0))
        info["clientes_con_compras"] = result.scalar()
        
        # Ventas
        result = await db.execute(select(func.count(Venta.id)))
        info["total_ventas"] = result.scalar()
        
        result = await db.execute(select(func.count(Venta.id)).where(Venta.estado == "completada"))
        info["ventas_completadas"] = result.scalar()
        
        # Mensajes/Conversaciones
        result = await db.execute(select(func.count(Mensaje.id)))
        info["total_mensajes"] = result.scalar()
        
        result = await db.execute(select(func.count(Mensaje.id)).where(
            Mensaje.tipo_mensaje.in_(["inventario", "venta", "contexto", "cliente"])
        ))
        info["mensajes_con_rag"] = result.scalar()
        
        # Fechas de rango
        result = await db.execute(select(func.min(Venta.fecha), func.max(Venta.fecha)))
        fecha_min, fecha_max = result.first()
        
        info["rango_fechas_ventas"] = {
            "fecha_minima": fecha_min.isoformat() if fecha_min else None,
            "fecha_maxima": fecha_max.isoformat() if fecha_max else None
        }
        
        return {
            "info_exportacion": info,
            "formatos_disponibles": ["CSV"],
            "endpoints_disponibles": [
                "/exportar/inventario",
                "/exportar/clientes", 
                "/exportar/ventas",
                "/exportar/conversaciones-rag",
                "/exportar/reporte-completo"
            ]
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo info de exportación: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor") 