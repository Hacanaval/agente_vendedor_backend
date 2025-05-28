"""
Endpoint para servir archivos estáticos y descargables
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse as FastAPIFileResponse
from pathlib import Path as PathLib
import logging
import os

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)

# Directorio base para archivos servidos
EXPORTS_DIR = PathLib("exports")
EXPORTS_DIR.mkdir(exist_ok=True)

@router.get("/exports/{filename}")
async def download_export_file(
    filename: str = Path(..., description="Nombre del archivo a descargar")
):
    """
    Descarga un archivo exportado del almacenamiento local.
    
    **Nota**: Solo funciona para almacenamiento local. Para S3/MinIO se usan URLs presignadas.
    """
    try:
        # Validar nombre de archivo para evitar path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=400, 
                detail="Nombre de archivo inválido"
            )
        
        file_path = EXPORTS_DIR / filename
        
        # Verificar que el archivo existe
        if not file_path.exists():
            raise HTTPException(
                status_code=404, 
                detail="Archivo no encontrado"
            )
        
        # Verificar que es un archivo (no directorio)
        if not file_path.is_file():
            raise HTTPException(
                status_code=400, 
                detail="Ruta no válida"
            )
        
        logger.info(f"Sirviendo archivo: {filename}")
        
        # Determinar tipo de contenido basado en extensión
        content_type = "application/octet-stream"
        if filename.lower().endswith('.csv'):
            content_type = "text/csv; charset=utf-8"
        elif filename.lower().endswith('.xlsx'):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.lower().endswith('.pdf'):
            content_type = "application/pdf"
        
        return FastAPIFileResponse(
            path=str(file_path),
            filename=filename,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sirviendo archivo {filename}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )

@router.get("/storage/info")
async def get_storage_info():
    """
    Obtiene información sobre el almacenamiento de archivos local.
    """
    try:
        # Contar archivos en directorio de exports
        files_count = len(list(EXPORTS_DIR.glob("*")))
        
        # Calcular tamaño total
        total_size = sum(f.stat().st_size for f in EXPORTS_DIR.glob("*") if f.is_file())
        
        return {
            "storage_type": "local",
            "exports_directory": str(EXPORTS_DIR.absolute()),
            "files_count": files_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory_exists": EXPORTS_DIR.exists()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo info de almacenamiento: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error obteniendo información de almacenamiento"
        ) 