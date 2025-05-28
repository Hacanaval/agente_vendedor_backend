"""
Sistema de Rate Limiting Enterprise
Protección inteligente contra abuso y sobrecarga del sistema
"""
import time
import asyncio
import logging
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN DE LÍMITES
# ===============================

class RateLimitType(Enum):
    """Tipos de límites de rate limiting"""
    PER_IP = "per_ip"
    PER_USER = "per_user"
    GLOBAL = "global"
    PER_ENDPOINT = "per_endpoint"

@dataclass
class RateLimit:
    """Configuración de un límite de rate"""
    requests: int                    # Número de requests permitidos
    window_seconds: int             # Ventana de tiempo en segundos
    burst_multiplier: float = 1.5   # Multiplicador para ráfagas
    enabled: bool = True            # Si está habilitado
    
    @property
    def burst_limit(self) -> int:
        """Límite de ráfaga"""
        return int(self.requests * self.burst_multiplier)

# ===============================
# CONFIGURACIÓN POR DEFECTO
# ===============================

DEFAULT_RATE_LIMITS = {
    # Endpoints críticos de chat
    "chat_message": RateLimit(30, 60),      # 30 mensajes por minuto
    "chat_websocket": RateLimit(60, 60),    # 60 mensajes WS por minuto
    
    # Búsquedas y consultas
    "search_products": RateLimit(100, 60),   # 100 búsquedas por minuto
    "search_semantic": RateLimit(50, 60),    # 50 búsquedas semánticas por minuto
    
    # Gestión de embeddings
    "embeddings_init": RateLimit(5, 300),    # 5 inicializaciones por 5 minutos
    "embeddings_rebuild": RateLimit(1, 3600), # 1 rebuild por hora
    
    # APIs de gestión
    "create_product": RateLimit(20, 60),     # 20 productos por minuto
    "update_product": RateLimit(50, 60),     # 50 updates por minuto
    "delete_product": RateLimit(10, 60),     # 10 deletes por minuto
    
    # Exportaciones
    "export_data": RateLimit(5, 300),        # 5 exportaciones por 5 minutos
    
    # Límites globales por IP
    "global_per_ip": RateLimit(200, 60),     # 200 requests por minuto por IP
    
    # Límites de autenticación
    "auth_login": RateLimit(5, 300),         # 5 intentos de login por 5 minutos
    "auth_register": RateLimit(3, 600),      # 3 registros por 10 minutos
}

# ===============================
# STORAGE BACKENDS
# ===============================

class RateLimitStorage:
    """Backend base para almacenamiento de rate limiting"""
    
    async def get_count(self, key: str, window_seconds: int) -> int:
        """Obtiene el conteo actual para una clave"""
        raise NotImplementedError
    
    async def increment(self, key: str, window_seconds: int) -> int:
        """Incrementa el conteo y retorna el nuevo valor"""
        raise NotImplementedError
    
    async def reset(self, key: str) -> None:
        """Resetea el conteo para una clave"""
        raise NotImplementedError

class MemoryRateLimitStorage(RateLimitStorage):
    """
    Storage en memoria para rate limiting
    Ideal para desarrollo y despliegues single-instance
    """
    
    def __init__(self):
        self._storage: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def get_count(self, key: str, window_seconds: int) -> int:
        """Obtiene el conteo actual limpiando entradas expiradas"""
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            
            # Limpiar entradas expiradas
            queue = self._storage[key]
            while queue and queue[0] < cutoff:
                queue.popleft()
            
            return len(queue)
    
    async def increment(self, key: str, window_seconds: int) -> int:
        """Incrementa el conteo y limpia entradas expiradas"""
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            
            # Limpiar entradas expiradas
            queue = self._storage[key]
            while queue and queue[0] < cutoff:
                queue.popleft()
            
            # Agregar nueva entrada
            queue.append(now)
            
            return len(queue)
    
    async def reset(self, key: str) -> None:
        """Resetea el conteo para una clave"""
        async with self._lock:
            if key in self._storage:
                self._storage[key].clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del storage"""
        return {
            "type": "memory",
            "total_keys": len(self._storage),
            "total_entries": sum(len(queue) for queue in self._storage.values())
        }

# ===============================
# RATE LIMITER PRINCIPAL
# ===============================

class RateLimiter:
    """
    Sistema de Rate Limiting Enterprise con múltiples estrategias
    """
    
    def __init__(self, storage: Optional[RateLimitStorage] = None):
        self.storage = storage or MemoryRateLimitStorage()
        self.limits = DEFAULT_RATE_LIMITS.copy()
        self.enabled = True
        
        # Estadísticas
        self._stats = {
            "requests_checked": 0,
            "requests_blocked": 0,
            "last_reset": datetime.now()
        }
        
        logger.info("🛡️ Rate Limiter inicializado")
    
    def configure_limit(self, name: str, limit: RateLimit) -> None:
        """Configura un límite específico"""
        self.limits[name] = limit
        logger.info(f"🔧 Límite configurado: {name} = {limit.requests}/{limit.window_seconds}s")
    
    def disable_limit(self, name: str) -> None:
        """Deshabilita un límite específico"""
        if name in self.limits:
            self.limits[name].enabled = False
            logger.info(f"❌ Límite deshabilitado: {name}")
    
    def enable_limit(self, name: str) -> None:
        """Habilita un límite específico"""
        if name in self.limits:
            self.limits[name].enabled = True
            logger.info(f"✅ Límite habilitado: {name}")
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        limit_name: str,
        request: Optional[Request] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si se puede permitir una request
        
        Returns:
            (allowed: bool, info: dict)
        """
        self._stats["requests_checked"] += 1
        
        if not self.enabled:
            return True, {"status": "disabled"}
        
        if limit_name not in self.limits:
            logger.warning(f"⚠️ Límite no encontrado: {limit_name}")
            return True, {"status": "limit_not_found"}
        
        limit = self.limits[limit_name]
        if not limit.enabled:
            return True, {"status": "limit_disabled"}
        
        # Crear clave única
        key = f"rl:{limit_name}:{identifier}"
        
        # Verificar límite
        current_count = await self.storage.increment(key, limit.window_seconds)
        
        # Información del estado
        info = {
            "limit_name": limit_name,
            "identifier": identifier,
            "current_count": current_count,
            "limit": limit.requests,
            "burst_limit": limit.burst_limit,
            "window_seconds": limit.window_seconds,
            "reset_time": datetime.now() + timedelta(seconds=limit.window_seconds)
        }
        
        # Verificar si excede el límite
        if current_count <= limit.requests:
            return True, {**info, "status": "allowed"}
        elif current_count <= limit.burst_limit:
            return True, {**info, "status": "burst_allowed"}
        else:
            self._stats["requests_blocked"] += 1
            return False, {**info, "status": "rate_limited"}
    
    async def reset_limit(self, identifier: str, limit_name: str) -> None:
        """Resetea un límite específico"""
        key = f"rl:{limit_name}:{identifier}"
        await self.storage.reset(key)
        logger.info(f"🔄 Límite reseteado: {limit_name} para {identifier}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del rate limiter"""
        return {
            "enabled": self.enabled,
            "total_limits": len(self.limits),
            "enabled_limits": sum(1 for l in self.limits.values() if l.enabled),
            "requests_checked": self._stats["requests_checked"],
            "requests_blocked": self._stats["requests_blocked"],
            "block_rate": (self._stats["requests_blocked"] / max(self._stats["requests_checked"], 1)) * 100,
            "storage_stats": self.storage.get_stats() if hasattr(self.storage, 'get_stats') else {},
            "last_reset": self._stats["last_reset"].isoformat()
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del rate limiter
rate_limiter = RateLimiter()

# ===============================
# UTILIDADES PARA FASTAPI
# ===============================

def get_client_identifier(request: Request) -> str:
    """
    Obtiene un identificador único del cliente
    Prioriza user_id > API key > IP
    """
    # Prioridad 1: User ID si está autenticado
    if hasattr(request.state, 'user_id') and request.state.user_id:
        return f"user:{request.state.user_id}"
    
    # Prioridad 2: API Key si está presente
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Hash del API key para privacidad
        hashed = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"apikey:{hashed}"
    
    # Prioridad 3: IP del cliente
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    return f"ip:{ip}"

async def check_rate_limit_middleware(
    request: Request, 
    limit_name: str,
    identifier: Optional[str] = None
) -> Optional[JSONResponse]:
    """
    Middleware para verificar rate limiting
    Retorna JSONResponse si está bloqueado, None si está permitido
    """
    if not identifier:
        identifier = get_client_identifier(request)
    
    allowed, info = await rate_limiter.check_rate_limit(identifier, limit_name, request)
    
    if not allowed:
        # Headers estándar de rate limiting
        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(max(0, info["limit"] - info["current_count"])),
            "X-RateLimit-Reset": str(int(info["reset_time"].timestamp())),
            "X-RateLimit-Window": str(info["window_seconds"]),
            "Retry-After": str(info["window_seconds"])
        }
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {info['limit']} per {info['window_seconds']} seconds",
                "limit_info": {
                    "limit": info["limit"],
                    "current": info["current_count"],
                    "window_seconds": info["window_seconds"],
                    "reset_time": info["reset_time"].isoformat()
                }
            },
            headers=headers
        )
    
    return None

# ===============================
# DECORADORES
# ===============================

def rate_limit(limit_name: str, identifier_func: Optional[callable] = None):
    """
    Decorador para aplicar rate limiting a funciones
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Buscar el request en los argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Si no hay request, ejecutar sin rate limiting
                return await func(*args, **kwargs)
            
            # Obtener identificador
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = get_client_identifier(request)
            
            # Verificar rate limit
            response = await check_rate_limit_middleware(request, limit_name, identifier)
            if response:
                return response
            
            # Ejecutar función original
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# ===============================
# GESTIÓN DE CONFIGURACIÓN
# ===============================

def load_rate_limits_from_config(config: Dict[str, Any]) -> None:
    """Carga configuración de rate limits desde un diccionario"""
    for name, config_data in config.items():
        if isinstance(config_data, dict):
            limit = RateLimit(
                requests=config_data.get("requests", 100),
                window_seconds=config_data.get("window_seconds", 60),
                burst_multiplier=config_data.get("burst_multiplier", 1.5),
                enabled=config_data.get("enabled", True)
            )
            rate_limiter.configure_limit(name, limit)

def export_rate_limits_config() -> Dict[str, Any]:
    """Exporta la configuración actual de rate limits"""
    return {
        name: {
            "requests": limit.requests,
            "window_seconds": limit.window_seconds,
            "burst_multiplier": limit.burst_multiplier,
            "enabled": limit.enabled
        }
        for name, limit in rate_limiter.limits.items()
    } 