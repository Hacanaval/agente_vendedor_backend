"""
Cache Manager Enterprise
Sistema de cache multi-nivel con TTL inteligente y métricas avanzadas
"""
import asyncio
import json
import hashlib
import pickle
import logging
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
import gzip
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN ENTERPRISE
# ===============================

# Configuración de cache por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Configuración PRODUCCIÓN
    MEMORY_CACHE_SIZE = 1000        # 1000 entradas en memoria
    DISK_CACHE_SIZE_MB = 500        # 500MB en disco
    DEFAULT_TTL = 3600              # 1 hora por defecto
    COMPRESSION_ENABLED = True      # Compresión en producción
elif ENVIRONMENT == "testing":
    # Configuración TESTING
    MEMORY_CACHE_SIZE = 100
    DISK_CACHE_SIZE_MB = 50
    DEFAULT_TTL = 300
    COMPRESSION_ENABLED = False
else:
    # Configuración DESARROLLO
    MEMORY_CACHE_SIZE = 500
    DISK_CACHE_SIZE_MB = 200
    DEFAULT_TTL = 1800
    COMPRESSION_ENABLED = False

# TTL por tipo de contenido
CACHE_TTL_CONFIG = {
    "productos": 3600,              # 1 hora - productos cambian poco
    "embeddings": 86400,            # 24 horas - embeddings estables
    "llm_responses": 1800,          # 30 minutos - respuestas LLM
    "search_results": 600,          # 10 minutos - resultados búsqueda
    "user_sessions": 7200,          # 2 horas - sesiones usuario
    "system_config": 3600,          # 1 hora - configuración sistema
    "health_checks": 60,            # 1 minuto - health checks
    "rate_limits": 300,             # 5 minutos - rate limiting
}

# Directorio de cache en disco
CACHE_DIR = Path("cache_storage")
CACHE_DIR.mkdir(exist_ok=True)

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class CacheLevel(Enum):
    """Niveles de cache disponibles"""
    MEMORY = "memory"       # L1: Ultra rápido (1-5ms)
    DISK = "disk"          # L2: Rápido (10-50ms)
    # REDIS = "redis"      # L3: Distribuido (futuro)

class CacheStrategy(Enum):
    """Estrategias de cache"""
    LRU = "lru"            # Least Recently Used
    TTL = "ttl"            # Time To Live
    HYBRID = "hybrid"      # LRU + TTL

@dataclass
class CacheEntry:
    """Entrada de cache con metadata"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: Optional[int] = None
    access_count: int = 0
    size_bytes: int = 0
    content_type: str = "unknown"
    compressed: bool = False
    
    @property
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        if self.ttl_seconds is None:
            return False
        
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Edad de la entrada en segundos"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def touch(self):
        """Actualiza el tiempo de acceso"""
        self.accessed_at = datetime.now()
        self.access_count += 1

# ===============================
# CACHE BACKENDS
# ===============================

class MemoryCache:
    """Cache en memoria con LRU y TTL"""
    
    def __init__(self, max_size: int = MEMORY_CACHE_SIZE):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Estadísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_removals": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del cache"""
        async with self._lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None
            
            entry = self.cache[key]
            
            # Verificar expiración
            if entry.is_expired:
                del self.cache[key]
                self.stats["expired_removals"] += 1
                self.stats["misses"] += 1
                return None
            
            # Actualizar acceso (LRU)
            entry.touch()
            self.cache.move_to_end(key)
            
            self.stats["hits"] += 1
            return entry.value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        content_type: str = "unknown"
    ) -> bool:
        """Almacena un valor en el cache"""
        async with self._lock:
            # Calcular tamaño aproximado
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = 1024  # Estimación por defecto
            
            # Crear entrada
            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes,
                content_type=content_type
            )
            
            # Eviction si es necesario
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats["evictions"] += 1
            
            # Almacenar
            self.cache[key] = entry
            return True
    
    async def delete(self, key: str) -> bool:
        """Elimina una entrada del cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> int:
        """Limpia todo el cache"""
        async with self._lock:
            count = len(self.cache)
            self.cache.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / max(total_requests, 1)) * 100
        
        return {
            "level": "memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "total_size_bytes": sum(entry.size_bytes for entry in self.cache.values()),
            **self.stats
        }

class DiskCache:
    """Cache en disco con compresión opcional"""
    
    def __init__(self, cache_dir: Path = CACHE_DIR, max_size_mb: int = DISK_CACHE_SIZE_MB):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = asyncio.Lock()
        
        # Estadísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "errors": 0
        }
    
    def _get_file_path(self, key: str) -> Path:
        """Obtiene la ruta del archivo para una clave"""
        # Hash de la clave para evitar problemas con caracteres especiales
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del cache en disco"""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            self.stats["misses"] += 1
            return None
        
        try:
            async with self._lock:
                # Leer archivo
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # Descomprimir si es necesario
                if COMPRESSION_ENABLED:
                    try:
                        data = gzip.decompress(data)
                    except:
                        pass  # No estaba comprimido
                
                # Deserializar
                entry_data = pickle.loads(data)
                entry = CacheEntry(**entry_data)
                
                # Verificar expiración
                if entry.is_expired:
                    file_path.unlink(missing_ok=True)
                    self.stats["misses"] += 1
                    return None
                
                self.stats["hits"] += 1
                return entry.value
                
        except Exception as e:
            logger.error(f"Error leyendo cache de disco {key}: {e}")
            self.stats["errors"] += 1
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        content_type: str = "unknown"
    ) -> bool:
        """Almacena un valor en el cache de disco"""
        try:
            async with self._lock:
                # Crear entrada
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl_seconds=ttl_seconds,
                    content_type=content_type
                )
                
                # Serializar
                entry_dict = {
                    "key": entry.key,
                    "value": entry.value,
                    "created_at": entry.created_at,
                    "accessed_at": entry.accessed_at,
                    "ttl_seconds": entry.ttl_seconds,
                    "access_count": entry.access_count,
                    "size_bytes": entry.size_bytes,
                    "content_type": entry.content_type,
                    "compressed": COMPRESSION_ENABLED
                }
                
                data = pickle.dumps(entry_dict)
                
                # Comprimir si está habilitado
                if COMPRESSION_ENABLED:
                    data = gzip.compress(data)
                
                # Escribir archivo
                file_path = self._get_file_path(key)
                with open(file_path, 'wb') as f:
                    f.write(data)
                
                self.stats["writes"] += 1
                return True
                
        except Exception as e:
            logger.error(f"Error escribiendo cache de disco {key}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Elimina una entrada del cache de disco"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error eliminando cache de disco {key}: {e}")
            return False
    
    async def clear(self) -> int:
        """Limpia todo el cache de disco"""
        try:
            count = 0
            for file_path in self.cache_dir.glob("*.cache"):
                file_path.unlink()
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error limpiando cache de disco: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache de disco"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / max(total_requests, 1)) * 100
        
        # Calcular tamaño total en disco
        total_size = 0
        file_count = 0
        try:
            for file_path in self.cache_dir.glob("*.cache"):
                total_size += file_path.stat().st_size
                file_count += 1
        except:
            pass
        
        return {
            "level": "disk",
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "hit_rate": hit_rate,
            "compression_enabled": COMPRESSION_ENABLED,
            **self.stats
        }

# ===============================
# CACHE MANAGER PRINCIPAL
# ===============================

class CacheManagerEnterprise:
    """
    Gestor de cache enterprise con múltiples niveles y estrategias inteligentes
    """
    
    def __init__(self):
        # Backends de cache
        self.memory_cache = MemoryCache()
        self.disk_cache = DiskCache()
        
        # Configuración
        self.default_ttl = DEFAULT_TTL
        self.ttl_config = CACHE_TTL_CONFIG.copy()
        
        # Estadísticas globales
        self.global_stats = {
            "total_requests": 0,
            "total_hits": 0,
            "total_misses": 0,
            "start_time": datetime.now()
        }
        
        # Tareas en background
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("🗄️ Cache Manager Enterprise inicializado")
    
    async def start(self):
        """Inicia las tareas en background"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_entries())
        logger.info("🚀 Cache Manager Enterprise iniciado")
    
    async def stop(self):
        """Detiene el cache manager"""
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Cache Manager Enterprise detenido")
    
    def _get_ttl_for_content(self, content_type: str) -> int:
        """Obtiene el TTL apropiado para un tipo de contenido"""
        return self.ttl_config.get(content_type, self.default_ttl)
    
    def _generate_cache_key(self, namespace: str, key: str, **kwargs) -> str:
        """Genera una clave de cache única"""
        # Incluir parámetros adicionales en la clave
        if kwargs:
            key_parts = [namespace, key] + [f"{k}:{v}" for k, v in sorted(kwargs.items())]
            combined_key = "|".join(str(part) for part in key_parts)
        else:
            combined_key = f"{namespace}|{key}"
        
        # Hash para claves muy largas
        if len(combined_key) > 200:
            return f"{namespace}|{hashlib.sha256(combined_key.encode()).hexdigest()}"
        
        return combined_key
    
    async def get(
        self, 
        namespace: str, 
        key: str, 
        **kwargs
    ) -> Optional[Any]:
        """
        Obtiene un valor del cache (multi-nivel)
        
        Args:
            namespace: Namespace del cache (ej: "productos", "embeddings")
            key: Clave específica
            **kwargs: Parámetros adicionales para la clave
        """
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        self.global_stats["total_requests"] += 1
        
        # L1: Intentar memoria primero
        value = await self.memory_cache.get(cache_key)
        if value is not None:
            self.global_stats["total_hits"] += 1
            return value
        
        # L2: Intentar disco
        value = await self.disk_cache.get(cache_key)
        if value is not None:
            # Promover a memoria para próximos accesos
            ttl = self._get_ttl_for_content(namespace)
            await self.memory_cache.set(cache_key, value, ttl, namespace)
            self.global_stats["total_hits"] += 1
            return value
        
        self.global_stats["total_misses"] += 1
        return None
    
    async def set(
        self, 
        namespace: str, 
        key: str, 
        value: Any,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Almacena un valor en el cache (multi-nivel)
        """
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        
        # Usar TTL específico o por defecto del namespace
        if ttl_seconds is None:
            ttl_seconds = self._get_ttl_for_content(namespace)
        
        # Almacenar en ambos niveles
        memory_success = await self.memory_cache.set(
            cache_key, value, ttl_seconds, namespace
        )
        
        disk_success = await self.disk_cache.set(
            cache_key, value, ttl_seconds, namespace
        )
        
        return memory_success or disk_success
    
    async def delete(self, namespace: str, key: str, **kwargs) -> bool:
        """Elimina una entrada del cache (todos los niveles)"""
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        
        memory_deleted = await self.memory_cache.delete(cache_key)
        disk_deleted = await self.disk_cache.delete(cache_key)
        
        return memory_deleted or disk_deleted
    
    async def clear_namespace(self, namespace: str) -> int:
        """Limpia todas las entradas de un namespace"""
        # Para simplificar, limpiamos todo el cache
        # En una implementación más avanzada, filtrarías por namespace
        memory_cleared = await self.memory_cache.clear()
        disk_cleared = await self.disk_cache.clear()
        
        return memory_cleared + disk_cleared
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalida entradas que coincidan con un patrón"""
        count = 0
        
        # Invalidar en memoria
        keys_to_delete = []
        for key in self.memory_cache.cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            await self.memory_cache.delete(key)
            count += 1
        
        # Invalidar en disco
        try:
            for file_path in self.disk_cache.cache_dir.glob("*.cache"):
                # Leer el archivo para obtener la clave original
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    
                    # Descomprimir si es necesario
                    if COMPRESSION_ENABLED:
                        try:
                            data = gzip.decompress(data)
                        except:
                            pass
                    
                    # Deserializar para obtener la clave
                    entry_data = pickle.loads(data)
                    original_key = entry_data.get("key", "")
                    
                    # Si la clave contiene el patrón, eliminar
                    if pattern in original_key:
                        file_path.unlink()
                        count += 1
                        
                except Exception:
                    # Si hay error leyendo el archivo, continuar
                    continue
                    
        except Exception as e:
            logger.error(f"Error invalidando patrón en disco: {e}")
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del cache"""
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.disk_cache.get_stats()
        
        total_requests = self.global_stats["total_requests"]
        global_hit_rate = (self.global_stats["total_hits"] / max(total_requests, 1)) * 100
        
        uptime = datetime.now() - self.global_stats["start_time"]
        
        return {
            "global": {
                "hit_rate": global_hit_rate,
                "total_requests": total_requests,
                "total_hits": self.global_stats["total_hits"],
                "total_misses": self.global_stats["total_misses"],
                "uptime_seconds": uptime.total_seconds()
            },
            "levels": {
                "memory": memory_stats,
                "disk": disk_stats
            },
            "configuration": {
                "default_ttl": self.default_ttl,
                "ttl_config": self.ttl_config,
                "compression_enabled": COMPRESSION_ENABLED,
                "environment": ENVIRONMENT
            }
        }
    
    async def _cleanup_expired_entries(self):
        """Tarea en background para limpiar entradas expiradas"""
        while self._running:
            try:
                # Limpiar memoria (automático con TTL)
                # Limpiar disco (verificar archivos expirados)
                
                await asyncio.sleep(300)  # Cada 5 minutos
                
            except Exception as e:
                logger.error(f"Error en cleanup de cache: {e}")
                await asyncio.sleep(300)

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del cache manager
cache_manager = CacheManagerEnterprise()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def get_cached(namespace: str, key: str, **kwargs) -> Optional[Any]:
    """Función de conveniencia para obtener del cache"""
    return await cache_manager.get(namespace, key, **kwargs)

async def set_cached(
    namespace: str, 
    key: str, 
    value: Any, 
    ttl_seconds: Optional[int] = None,
    **kwargs
) -> bool:
    """Función de conveniencia para almacenar en cache"""
    return await cache_manager.set(namespace, key, value, ttl_seconds, **kwargs)

async def delete_cached(namespace: str, key: str, **kwargs) -> bool:
    """Función de conveniencia para eliminar del cache"""
    return await cache_manager.delete(namespace, key, **kwargs)

def cache_key_for_search(query: str, filters: Dict = None) -> str:
    """Genera clave de cache para búsquedas"""
    if filters:
        filter_str = "|".join(f"{k}:{v}" for k, v in sorted(filters.items()))
        return f"search:{query}|{filter_str}"
    return f"search:{query}"

def cache_key_for_llm(prompt: str, model: str = "gemini", temperature: float = 0.7) -> str:
    """Genera clave de cache para respuestas LLM"""
    # Hash del prompt para claves más cortas
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    return f"llm:{model}:t{temperature}:{prompt_hash}" 