"""
Servicio de almacenamiento de archivos con soporte para S3 y almacenamiento local
"""
from __future__ import annotations
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import os
import logging
import tempfile
import hashlib
from pathlib import Path
import aiofiles

# Importaciones condicionales para S3
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from app.models.responses import FileResponse, StatusEnum

logger = logging.getLogger(__name__)


class FileStorageService:
    """
    Servicio de almacenamiento de archivos con múltiples backends:
    1. S3 (AWS)
    2. MinIO (S3-compatible)
    3. Almacenamiento local (fallback)
    """
    
    def __init__(self):
        self.storage_backend = self._detect_storage_backend()
        self.local_storage_path = Path("exports")
        self.local_storage_path.mkdir(exist_ok=True)
        
        # Configuración de expiración por defecto
        self.default_expiration_hours = 24
        
    def _detect_storage_backend(self) -> str:
        """Detecta automáticamente qué backend de almacenamiento usar"""
        
        # 1. Verificar AWS S3
        if S3_AVAILABLE and os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    region_name=os.getenv("AWS_REGION", "us-east-1")
                )
                self.s3_bucket = os.getenv("S3_BUCKET_NAME", "agente-vendedor-exports")
                logger.info("Almacenamiento configurado: AWS S3")
                return "s3"
            except Exception as e:
                logger.warning(f"Error configurando S3: {e}")
        
        # 2. Verificar MinIO
        if MINIO_AVAILABLE and os.getenv("MINIO_ENDPOINT"):
            try:
                self.minio_client = Minio(
                    os.getenv("MINIO_ENDPOINT"),
                    access_key=os.getenv("MINIO_ACCESS_KEY"),
                    secret_key=os.getenv("MINIO_SECRET_KEY"),
                    secure=os.getenv("MINIO_SECURE", "true").lower() == "true"
                )
                self.minio_bucket = os.getenv("MINIO_BUCKET_NAME", "agente-vendedor-exports")
                logger.info("Almacenamiento configurado: MinIO")
                return "minio"
            except Exception as e:
                logger.warning(f"Error configurando MinIO: {e}")
        
        # 3. Fallback a almacenamiento local
        logger.info("Almacenamiento configurado: Local (fallback)")
        return "local"
    
    async def store_file(
        self,
        content: str,
        filename: str,
        content_type: str = "text/csv",
        expiration_hours: Optional[int] = None
    ) -> FileResponse:
        """
        Almacena un archivo y devuelve información de acceso
        
        Args:
            content: Contenido del archivo como string
            filename: Nombre del archivo
            content_type: Tipo MIME del archivo
            expiration_hours: Horas hasta que expire (None = sin expiración)
        
        Returns:
            FileResponse con información del archivo almacenado
        """
        
        expiration_hours = expiration_hours or self.default_expiration_hours
        expires_at = datetime.now() + timedelta(hours=expiration_hours)
        
        # Generar hash único para el archivo
        file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{file_hash}_{filename}"
        
        try:
            if self.storage_backend == "s3":
                return await self._store_s3(content, unique_filename, content_type, expires_at)
            elif self.storage_backend == "minio":
                return await self._store_minio(content, unique_filename, content_type, expires_at)
            else:
                return await self._store_local(content, unique_filename, content_type, expires_at)
                
        except Exception as e:
            logger.error(f"Error almacenando archivo {filename}: {e}")
            # Fallback a almacenamiento local si falla el backend principal
            if self.storage_backend != "local":
                logger.info("Fallback a almacenamiento local")
                return await self._store_local(content, unique_filename, content_type, expires_at)
            raise
    
    async def _store_s3(
        self, 
        content: str, 
        filename: str, 
        content_type: str, 
        expires_at: datetime
    ) -> FileResponse:
        """Almacena archivo en AWS S3"""
        
        try:
            # Asegurar que el bucket existe
            try:
                self.s3_client.head_bucket(Bucket=self.s3_bucket)
            except ClientError:
                self.s3_client.create_bucket(Bucket=self.s3_bucket)
            
            # Subir archivo
            key = f"exports/{filename}"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType=content_type,
                Metadata={
                    'expires_at': expires_at.isoformat(),
                    'original_filename': filename
                }
            )
            
            # Generar URL de descarga con expiración
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.s3_bucket, 'Key': key},
                ExpiresIn=int(expires_at.timestamp() - datetime.now().timestamp())
            )
            
            return FileResponse(
                status=StatusEnum.SUCCESS,
                message="Archivo almacenado correctamente en S3",
                file_path=f"s3://{self.s3_bucket}/{key}",
                file_name=filename,
                file_size=len(content.encode('utf-8')),
                download_url=download_url,
                expires_at=expires_at
            )
            
        except Exception as e:
            logger.error(f"Error almacenando en S3: {e}")
            raise
    
    async def _store_minio(
        self, 
        content: str, 
        filename: str, 
        content_type: str, 
        expires_at: datetime
    ) -> FileResponse:
        """Almacena archivo en MinIO"""
        
        try:
            # Asegurar que el bucket existe
            if not self.minio_client.bucket_exists(self.minio_bucket):
                self.minio_client.make_bucket(self.minio_bucket)
            
            # Crear archivo temporal para subir
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Subir archivo
                object_name = f"exports/{filename}"
                self.minio_client.fput_object(
                    self.minio_bucket,
                    object_name,
                    temp_file_path,
                    content_type=content_type,
                    metadata={
                        'expires_at': expires_at.isoformat(),
                        'original_filename': filename
                    }
                )
                
                # Generar URL de descarga con expiración
                expiration_delta = expires_at - datetime.now()
                download_url = self.minio_client.presigned_get_object(
                    self.minio_bucket,
                    object_name,
                    expires=expiration_delta
                )
                
                return FileResponse(
                    status=StatusEnum.SUCCESS,
                    message="Archivo almacenado correctamente en MinIO",
                    file_path=f"minio://{self.minio_bucket}/{object_name}",
                    file_name=filename,
                    file_size=len(content.encode('utf-8')),
                    download_url=download_url,
                    expires_at=expires_at
                )
                
            finally:
                # Limpiar archivo temporal
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error almacenando en MinIO: {e}")
            raise
    
    async def _store_local(
        self, 
        content: str, 
        filename: str, 
        content_type: str, 
        expires_at: datetime
    ) -> FileResponse:
        """Almacena archivo localmente"""
        
        try:
            file_path = self.local_storage_path / filename
            
            # Escribir archivo
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # En almacenamiento local, la URL de descarga es relativa
            base_url = os.getenv("BASE_URL", "http://localhost:8001")
            download_url = f"{base_url}/files/exports/{filename}"
            
            return FileResponse(
                status=StatusEnum.SUCCESS,
                message="Archivo almacenado correctamente (local)",
                file_path=str(file_path),
                file_name=filename,
                file_size=len(content.encode('utf-8')),
                download_url=download_url,
                expires_at=expires_at
            )
            
        except Exception as e:
            logger.error(f"Error almacenando localmente: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Elimina un archivo del almacenamiento
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        
        try:
            if file_path.startswith("s3://"):
                # Eliminar de S3
                bucket, key = file_path.replace("s3://", "").split("/", 1)
                self.s3_client.delete_object(Bucket=bucket, Key=key)
                
            elif file_path.startswith("minio://"):
                # Eliminar de MinIO
                bucket, object_name = file_path.replace("minio://", "").split("/", 1)
                self.minio_client.remove_object(bucket, object_name)
                
            else:
                # Eliminar archivo local
                if os.path.exists(file_path):
                    os.unlink(file_path)
            
            logger.info(f"Archivo eliminado: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando archivo {file_path}: {e}")
            return False
    
    async def cleanup_expired_files(self) -> Dict[str, Any]:
        """
        Limpia archivos expirados (solo en almacenamiento local)
        Para S3/MinIO se recomienda configurar lifecycle policies
        
        Returns:
            Estadísticas de limpieza
        """
        
        if self.storage_backend != "local":
            return {
                "message": f"Limpieza automática no implementada para {self.storage_backend}",
                "files_deleted": 0
            }
        
        deleted_count = 0
        current_time = datetime.now()
        
        try:
            for file_path in self.local_storage_path.glob("*"):
                if file_path.is_file():
                    # Extraer timestamp del nombre del archivo
                    parts = file_path.name.split("_")
                    if len(parts) >= 2:
                        try:
                            file_timestamp = datetime.strptime(parts[0], "%Y%m%d")
                            file_datetime = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                            
                            # Eliminar si es más viejo que el período de expiración
                            if current_time - file_datetime > timedelta(hours=self.default_expiration_hours):
                                file_path.unlink()
                                deleted_count += 1
                                logger.info(f"Archivo expirado eliminado: {file_path.name}")
                                
                        except ValueError:
                            # Si no se puede parsear la fecha, eliminar archivos muy viejos
                            file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_age > timedelta(hours=self.default_expiration_hours * 2):
                                file_path.unlink()
                                deleted_count += 1
                                logger.info(f"Archivo muy viejo eliminado: {file_path.name}")
            
            return {
                "message": f"Limpieza completada. {deleted_count} archivos eliminados",
                "files_deleted": deleted_count,
                "storage_backend": self.storage_backend
            }
            
        except Exception as e:
            logger.error(f"Error en limpieza de archivos: {e}")
            return {
                "message": f"Error en limpieza: {str(e)}",
                "files_deleted": deleted_count
            }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Retorna información sobre la configuración de almacenamiento"""
        
        info = {
            "storage_backend": self.storage_backend,
            "default_expiration_hours": self.default_expiration_hours,
            "s3_available": S3_AVAILABLE,
            "minio_available": MINIO_AVAILABLE
        }
        
        if self.storage_backend == "s3":
            info.update({
                "s3_bucket": self.s3_bucket,
                "s3_region": os.getenv("AWS_REGION", "us-east-1")
            })
        elif self.storage_backend == "minio":
            info.update({
                "minio_endpoint": os.getenv("MINIO_ENDPOINT"),
                "minio_bucket": self.minio_bucket
            })
        else:
            info.update({
                "local_storage_path": str(self.local_storage_path),
                "base_url": os.getenv("BASE_URL", "http://localhost:8001")
            })
        
        return info


# Instancia global del servicio
file_storage = FileStorageService() 