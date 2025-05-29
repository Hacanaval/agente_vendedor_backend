from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.services.csv_exporter import CSVExporter
from app.services.file_storage import file_storage
from app.models.responses import FileResponse
from app.core.exceptions import RAGException

router = APIRouter(prefix="/exportar", tags=["exportar"])
logger = logging.getLogger(__name__)

@router.get("/inventario", response_model=FileResponse)
async def exportar_inventario_csv(
    incluir_inactivos: bool = Query(False, description="Incluir productos inactivos"),
    solo_con_stock: bool = Query(False, description="Solo productos con stock > 0"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta el inventario completo a CSV y lo almacena en S3/storage.
    Retorna URL de descarga con expiración en lugar de streaming directo.
    
    - **incluir_inactivos**: Incluir productos marcados como inactivos
    - **solo_con_stock**: Solo productos que tienen stock disponible
    """
    try:
        logger.info(f"Iniciando exportación de inventario - inactivos: {incluir_inactivos}, solo_stock: {solo_con_stock}")
        
        resultado = await CSVExporter.exportar_inventario(
            db=db,
            incluir_inactivos=incluir_inactivos,
            solo_con_stock=solo_con_stock
        )
        
        if not resultado["exito"]:
            raise RAGException(
                message=resultado.get("error", "Error exportando inventario"),
                rag_type="csv_export",
                details={"export_type": "inventario"}
            )
        
        # Almacenar archivo usando el nuevo sistema
        file_response = await file_storage.store_file(
            content=resultado["csv_content"],
            filename=resultado["nombre_archivo"],
            content_type="text/csv",
            expiration_hours=24  # Archivo expira en 24 horas
        )
        
        logger.info(f"Inventario exportado exitosamente: {file_response.file_name}")
        return file_response
        
    except RAGException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint exportar inventario: {e}")
        raise RAGException(
            message=f"Error interno exportando inventario: {str(e)[:100]}",
            rag_type="csv_export",
            details={"export_type": "inventario"}
        )

@router.get("/clientes", response_model=FileResponse)
async def exportar_clientes_csv(
    incluir_inactivos: bool = Query(False, description="Incluir clientes inactivos"),
    con_compras: bool = Query(False, description="Solo clientes que han realizado compras"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta la base de clientes a CSV y lo almacena en S3/storage.
    
    - **incluir_inactivos**: Incluir clientes marcados como inactivos
    - **con_compras**: Solo clientes que han realizado al menos una compra
    - **fecha_desde**: Filtrar por fecha de registro desde (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar por fecha de registro hasta (formato: YYYY-MM-DD)
    """
    try:
        logger.info(f"Iniciando exportación de clientes - desde: {fecha_desde}, hasta: {fecha_hasta}")
        
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
            raise RAGException(
                message=resultado.get("error", "Error exportando clientes"),
                rag_type="csv_export",
                details={"export_type": "clientes"}
            )
        
        # Almacenar archivo
        file_response = await file_storage.store_file(
            content=resultado["csv_content"],
            filename=resultado["nombre_archivo"],
            content_type="text/csv",
            expiration_hours=24
        )
        
        logger.info(f"Clientes exportados exitosamente: {file_response.file_name}")
        return file_response
        
    except HTTPException:
        raise
    except RAGException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint exportar clientes: {e}")
        raise RAGException(
            message=f"Error interno exportando clientes: {str(e)[:100]}",
            rag_type="csv_export",
            details={"export_type": "clientes"}
        )

@router.get("/ventas", response_model=FileResponse)
async def exportar_ventas_csv(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    estado: Optional[str] = Query(None, description="Filtrar por estado específico"),
    incluir_detalles_cliente: bool = Query(True, description="Incluir información del cliente"),
    incluir_detalles_producto: bool = Query(True, description="Incluir información del producto"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta las ventas a CSV con detalles completos y lo almacena en S3/storage.
    
    - **fecha_desde**: Filtrar ventas desde esta fecha (formato: YYYY-MM-DD)
    - **fecha_hasta**: Filtrar ventas hasta esta fecha (formato: YYYY-MM-DD)
    - **estado**: Filtrar por estado específico (completada, pendiente, etc.)
    - **incluir_detalles_cliente**: Incluir información completa del cliente
    - **incluir_detalles_producto**: Incluir información completa del producto
    """
    try:
        logger.info(f"Iniciando exportación de ventas - desde: {fecha_desde}, hasta: {fecha_hasta}, estado: {estado}")
        
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
            raise RAGException(
                message=resultado.get("error", "Error exportando ventas"),
                rag_type="csv_export",
                details={"export_type": "ventas"}
            )
        
        # Almacenar archivo
        file_response = await file_storage.store_file(
            content=resultado["csv_content"],
            filename=resultado["nombre_archivo"],
            content_type="text/csv",
            expiration_hours=48  # Ventas pueden ser archivos más grandes, más tiempo
        )
        
        logger.info(f"Ventas exportadas exitosamente: {file_response.file_name}")
        return file_response
        
    except HTTPException:
        raise
    except RAGException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint exportar ventas: {e}")
        raise RAGException(
            message=f"Error interno exportando ventas: {str(e)[:100]}",
            rag_type="csv_export",
            details={"export_type": "ventas"}
        )

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
    ✅ ENDPOINT SIMPLIFICADO para exportar conversaciones RAG
    """
    try:
        # ✅ VERSIÓN SIMPLIFICADA - JSON response directa
        from sqlalchemy.future import select
        
        # Intentar obtener mensajes de la base de datos
        try:
            # Importar modelo en el momento de uso para evitar dependencias circulares
            from app.models.mensaje import Mensaje
            
            query = select(Mensaje).order_by(Mensaje.timestamp.desc()).limit(100)
            
            result = await db.execute(query)
            mensajes = result.scalars().all()
            
            conversaciones_data = []
            for mensaje in mensajes:
                conversacion = {
                    "id": mensaje.id,
                    "chat_id": mensaje.chat_id or "",
                    "timestamp": mensaje.timestamp.isoformat() if mensaje.timestamp else "",
                    "remitente": mensaje.remitente or "",
                    "mensaje": mensaje.mensaje or "",
                    "tipo_mensaje": mensaje.tipo_mensaje or "",
                    "estado_venta": getattr(mensaje, 'estado_venta', '') or ""
                }
                conversaciones_data.append(conversacion)
            
            return {
                "success": True,
                "total_conversaciones": len(conversaciones_data),
                "conversaciones": conversaciones_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as db_error:
            # ✅ FALLBACK MÍNIMO si hay problemas con base de datos
            return {
                "success": False,
                "error": f"Error accediendo a conversaciones: {str(db_error)[:100]}",
                "total_conversaciones": 0,
                "conversaciones": [],
                "fallback": True,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        # ✅ RESPUESTA DE ERROR FINAL
        return {
            "success": False,
            "error": f"Error interno: {str(e)[:100]}",
            "total_conversaciones": 0,
            "conversaciones": [],
            "timestamp": datetime.now().isoformat()
        }

@router.get("/reporte-completo", response_model=FileResponse)
async def exportar_reporte_completo_csv(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde para filtrar ventas (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta para filtrar ventas (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un reporte completo con múltiples hojas de cálculo en formato CSV y lo almacena en S3/storage.
    Incluye: inventario, clientes, ventas y conversaciones RAG.
    
    - **fecha_desde**: Fecha desde para filtrar ventas y conversaciones (formato: YYYY-MM-DD)
    - **fecha_hasta**: Fecha hasta para filtrar ventas y conversaciones (formato: YYYY-MM-DD)
    
    **Nota**: Este endpoint puede tomar varios minutos para completarse con grandes volúmenes de datos.
    Se recomienda usar filtros de fecha para optimizar el rendimiento.
    """
    try:
        logger.info(f"Iniciando exportación de reporte completo - desde: {fecha_desde}, hasta: {fecha_hasta}")
        
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
            raise RAGException(
                message=resultado.get("error", "Error generando reporte completo"),
                rag_type="csv_export",
                details={"export_type": "reporte_completo"}
            )
        
        # Almacenar archivo con tiempo de expiración extendido por ser reporte completo
        file_response = await file_storage.store_file(
            content=resultado["csv_content"],
            filename=resultado["nombre_archivo"],
            content_type="text/csv",
            expiration_hours=168  # 7 días para reportes completos
        )
        
        logger.info(f"Reporte completo exportado exitosamente: {file_response.file_name}")
        return file_response
        
    except HTTPException:
        raise
    except RAGException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint exportar reporte completo: {e}")
        raise RAGException(
            message=f"Error interno generando reporte: {str(e)[:100]}",
            rag_type="csv_export",
            details={"export_type": "reporte_completo"}
        )

@router.get("/info")
async def obtener_info_exportacion(db: AsyncSession = Depends(get_db)):
    """
    Obtiene información sobre las capacidades de exportación y el estado del sistema de almacenamiento.
    Útil para verificar la configuración y las opciones disponibles.
    """
    try:
        # Obtener estadísticas de la base de datos
        stats = await CSVExporter.obtener_estadisticas_exportacion(db)
        
        # Información del sistema de almacenamiento
        storage_info = file_storage.get_storage_info()
        
        return {
            "message": "Información de exportación obtenida correctamente",
            "estadisticas_bd": stats,
            "sistema_almacenamiento": storage_info,
            "formatos_soportados": ["CSV"],
            "timeouts_configurados": {
                "inventario": "24 horas",
                "clientes": "24 horas", 
                "ventas": "48 horas",
                "conversaciones_rag": "72 horas",
                "reporte_completo": "168 horas (7 días)"
            },
            "nota": "Los archivos se almacenan temporalmente y se eliminan automáticamente después del tiempo de expiración configurado."
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo info de exportación: {e}")
        raise RAGException(
            message=f"Error obteniendo información: {str(e)[:100]}",
            rag_type="info_export",
            details={}
        )

@router.post("/cleanup")
async def limpiar_archivos_expirados():
    """
    Limpia manualmente archivos expirados del almacenamiento local.
    Para S3/MinIO se recomienda configurar lifecycle policies.
    
    **Nota**: Solo disponible para almacenamiento local.
    """
    try:
        resultado = await file_storage.cleanup_expired_files()
        return resultado
        
    except Exception as e:
        logger.error(f"Error en limpieza de archivos: {e}")
        raise RAGException(
            message=f"Error en limpieza: {str(e)[:100]}",
            rag_type="file_cleanup",
            details={}
        ) 