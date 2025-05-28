"""
Modelos de respuesta consistentes para el API
"""
from __future__ import annotations
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class StatusEnum(str, Enum):
    """Estados posibles de las respuestas"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"


class TipoMensajeEnum(str, Enum):
    """Tipos de mensaje del chatbot"""
    SALUDO = "saludo"
    INVENTARIO = "inventario" 
    VENTA = "venta"
    CLIENTE = "cliente"
    DESPEDIDA = "despedida"
    GENERAL = "general"
    ERROR = "error"


class BaseResponse(BaseModel):
    """Respuesta base para todas las APIs"""
    status: StatusEnum = Field(default=StatusEnum.SUCCESS)
    message: str = Field(default="Operación exitosa")
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = Field(default=None)


class DataResponse(BaseResponse):
    """Respuesta con datos"""
    data: Any = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ListResponse(BaseResponse):
    """Respuesta para listas de datos"""
    data: List[Any] = Field(default_factory=list)
    total: int = Field(default=0)
    page: Optional[int] = Field(default=None)
    page_size: Optional[int] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatResponse(BaseResponse):
    """Respuesta específica para el chat"""
    respuesta: str = Field(..., description="Respuesta del chatbot")
    tipo_mensaje: TipoMensajeEnum = Field(default=TipoMensajeEnum.GENERAL)
    chat_id: str = Field(..., description="ID de la conversación")
    metadatos: Dict[str, Any] = Field(default_factory=dict)
    sugerencias: Optional[List[str]] = Field(default=None)


class ErrorResponse(BaseResponse):
    """Respuesta para errores"""
    status: StatusEnum = Field(default=StatusEnum.ERROR)
    error_code: Optional[str] = Field(default=None)
    error_details: Optional[Dict[str, Any]] = Field(default=None)
    stack_trace: Optional[str] = Field(default=None, include=False)  # Solo en desarrollo


class FileResponse(BaseResponse):
    """Respuesta para archivos almacenados"""
    file_path: str = Field(..., description="Ruta del archivo almacenado")
    file_name: str = Field(..., description="Nombre original del archivo")
    file_size: int = Field(..., description="Tamaño del archivo en bytes")
    download_url: str = Field(..., description="URL de descarga del archivo")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración del archivo")


class ExportInfoResponse(BaseResponse):
    """Respuesta para información de exportación"""
    info_exportacion: Dict[str, Any] = Field(default_factory=dict)
    estadisticas: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HealthResponse(BaseResponse):
    """Respuesta para health checks"""
    service_name: str = Field(..., description="Nombre del servicio")
    version: str = Field(..., description="Versión del servicio")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Estado de dependencias")


class ValidationErrorResponse(BaseResponse):
    """Respuesta para errores de validación"""
    status: StatusEnum = Field(default=StatusEnum.ERROR)
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)


# Tipos de respuesta para usar en FastAPI
ResponseType = Union[
    DataResponse,
    ListResponse, 
    ChatResponse,
    ErrorResponse,
    FileResponse,
    ExportInfoResponse,
    HealthResponse,
    ValidationErrorResponse
] 