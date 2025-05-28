"""
Sistema centralizado de manejo de excepciones
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY
import logging
from datetime import datetime

from app.models.responses import ErrorResponse, StatusEnum

logger = logging.getLogger(__name__)


class BaseAPIException(Exception):
    """Excepción base para el API"""
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(BaseAPIException):
    """Excepción para errores de validación"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFound(BaseAPIException):
    """Excepción para recursos no encontrados"""
    
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} con identificador '{identifier}' no encontrado"
        super().__init__(
            message=message,
            status_code=HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class BadRequest(BaseAPIException):
    """Excepción para solicitudes incorrectas"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            details=details
        )


class RAGException(BaseAPIException):
    """Excepción específica para errores de RAG"""
    
    def __init__(self, message: str, rag_type: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["rag_type"] = rag_type
        super().__init__(
            message=f"Error en RAG {rag_type}: {message}",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="RAG_ERROR",
            details=details
        )


class DatabaseException(BaseAPIException):
    """Excepción para errores de base de datos"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["operation"] = operation
        super().__init__(
            message=f"Error de base de datos en {operation}: {message}",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details
        )


class EmbeddingException(BaseAPIException):
    """Excepción para errores de embeddings"""
    
    def __init__(self, message: str, text_length: Optional[int] = None):
        details = {}
        if text_length:
            details["text_length"] = text_length
        super().__init__(
            message=f"Error generando embedding: {message}",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="EMBEDDING_ERROR",
            details=details
        )


class TimeoutException(BaseAPIException):
    """Excepción para timeouts"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"Timeout en operación '{operation}' después de {timeout_seconds} segundos",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="TIMEOUT_ERROR",
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


# Manejadores de excepciones globales
async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """Manejador para errores de validación"""
    logger.warning(f"Validation error: {exc.message}", extra={"details": exc.details})
    
    response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def not_found_exception_handler(request: Request, exc: NotFound) -> JSONResponse:
    """Manejador para recursos no encontrados"""
    logger.info(f"Resource not found: {exc.message}")
    
    response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def bad_request_exception_handler(request: Request, exc: BadRequest) -> JSONResponse:
    """Manejador para solicitudes incorrectas"""
    logger.warning(f"Bad request: {exc.message}", extra={"details": exc.details})
    
    response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def rag_exception_handler(request: Request, exc: RAGException) -> JSONResponse:
    """Manejador para errores de RAG"""
    logger.error(f"RAG error: {exc.message}", extra={"details": exc.details})
    
    response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def database_exception_handler(request: Request, exc: DatabaseException) -> JSONResponse:
    """Manejador para errores de base de datos"""
    logger.error(f"Database error: {exc.message}", extra={"details": exc.details})
    
    response = ErrorResponse(
        message="Error interno del servidor",  # No exponer detalles de BD
        error_code=exc.error_code,
        error_details={"operation": exc.details.get("operation", "unknown")},
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def timeout_exception_handler(request: Request, exc: TimeoutException) -> JSONResponse:
    """Manejador para timeouts"""
    logger.warning(f"Timeout error: {exc.message}", extra={"details": exc.details})
    
    response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejador general para excepciones no controladas"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    response = ErrorResponse(
        message="Error interno del servidor",
        error_code="INTERNAL_ERROR",
        error_details={"type": type(exc).__name__},
        timestamp=datetime.now()
    )
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump()
    )


# Función para registrar todos los manejadores
def register_exception_handlers(app):
    """Registrar todos los manejadores de excepciones en la app"""
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(NotFound, not_found_exception_handler)
    app.add_exception_handler(BadRequest, bad_request_exception_handler)
    app.add_exception_handler(RAGException, rag_exception_handler)
    app.add_exception_handler(DatabaseException, database_exception_handler)
    app.add_exception_handler(TimeoutException, timeout_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler) 