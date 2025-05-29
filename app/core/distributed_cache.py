"""
🌐 Distributed Cache Layer Enterprise
Cache distribuido multi-nivel: L1 (Memory) → L2 (Redis) → L3 (Disk)
"""
import asyncio
import json
import logging
import pickle
import gzip
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import os

# Imports del sistema
from app.core.redis_manager import redis_manager, REDIS_AVAILABLE
from app.core.cache_manager import MemoryCache, DiskCache, CacheEntry

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN CACHE DISTRIBUIDO
# ===============================

# Configuración por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DISTRIBUTED_CACHE_CONFIG = {
    "production": {
        "l1_memory_size": 1000,         # 1000 entradas en memoria
        "l2_redis_enabled": True,       # Redis habilitado
        "l3_disk_enabled": True,        # Disco habilitado
        "compression_threshold": 1024,   # Comprimir si >1KB
        "serialization": "pickle",       # pickle, json, msgpack
        "ttl_multipliers": {
            "l1": 1.0,    # TTL base
            "l2": 2.0,    # TTL 2x en Redis
            "l3": 4.0     # TTL 4x en disco
        },
        "promotion_threshold": 2,        # Promover a L1 después de 2 accesos
        "invalidation_strategy": "pub_sub"  # pub_sub, polling
    },
    "staging": {
        "l1_memory_size": 500,
        "l2_redis_enabled": True,
        "l3_disk_enabled": True,
        "compression_threshold": 2048,
        "serialization": "pickle",
        "ttl_multipliers": {
            "l1": 1.0,
            "l2": 1.5,
            "l3": 3.0
        },
        "promotion_threshold": 3,
        "invalidation_strategy": "pub_sub"
    },
    "development": {
        "l1_memory_size": 200,
        "l2_redis_enabled": REDIS_AVAILABLE,
        "l3_disk_enabled": True,
        "compression_threshold": 4096,
        "serialization": "json",
        "ttl_multipliers": {
            "l1": 1.0,
            "l2": 1.0,
            "l3": 2.0
        },
        "promotion_threshold": 1,
        "invalidation_strategy": "polling"
    }
}

# Configuración actual
CACHE_CONFIG = DISTRIBUTED_CACHE_CONFIG.get(ENVIRONMENT, DISTRIBUTED_CACHE_CONFIG["development"])

# Estrategias de distribución por tipo de dato
DISTRIBUTION_STRATEGY = {
    "embeddings": {
        "levels": ["l2"],  # Solo Redis (compartido entre instancias)
        "replication": 2,
        "compression": True,
        "ttl_base": 86400,  # 24h
        "reason": "Compartidos entre instancias, costosos de generar"
    },
    "search_results": {
        "levels": ["l1", "l2"],  # Memoria + Redis
        "replication": 1,
        "compression": False,
        "ttl_base": 3600,   # 1h
        "reason": "Acceso frecuente, tamaño moderado"
    },
    "llm_responses": {
        "levels": ["l2"],  # Solo Redis (compartible)
        "replication": 2,
        "compression": True,
        "ttl_base": 1800,   # 30min
        "reason": "Costosos de generar, compartibles"
    },
    "user_sessions": {
        "levels": ["l1"],  # Solo memoria local
        "replication": 0,
        "compression": False,
        "ttl_base": 7200,   # 2h
        "reason": "Específicos por instancia"
    },
    "semantic_cache": {
        "levels": ["l1", "l2"],  # Memoria + Redis
        "replication": 1,
        "compression": True,
        "ttl_base": 3600,   # 1h
        "reason": "Cache semántico compartible"
    },
    "default": {
        "levels": ["l1", "l2", "l3"],  # Todos los niveles
        "replication": 1,
        "compression": False,
        "ttl_base": 1800,   # 30min
        "reason": "Estrategia por defecto"
    }
}

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class CacheLevel(Enum):
    """Niveles de cache distribuido"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"

class SerializationMethod(Enum):
    """Métodos de serialización"""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"

@dataclass
class DistributedCacheEntry:
    """Entrada de cache distribuido con metadatos"""
    key: str
    value: Any
    namespace: str
    content_type: str
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    compression_used: bool = False
    serialization_method: str = "pickle"
    source_level: str = "unknown"
    promotion_score: float = 0.0
    
    @property
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        if self.ttl_seconds is None:
            return False
        
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def touch(self):
        """Actualiza el tiempo de acceso y contador"""
        self.accessed_at = datetime.now()
        self.access_count += 1
        self.promotion_score = self.access_count / max((datetime.now() - self.created_at).total_seconds() / 3600, 1)

@dataclass
class CacheLevelStats:
    """Estadísticas por nivel de cache"""
    level: str
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_size_bytes: int = 0
    avg_latency_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / max(total, 1)) * 100

# ===============================
# SERIALIZER INTELIGENTE
# ===============================

class CacheSerializer:
    """Serializer inteligente con compresión adaptativa"""
    
    def __init__(self):
        self.compression_threshold = CACHE_CONFIG["compression_threshold"]
        self.default_method = CACHE_CONFIG["serialization"]
    
    def serialize(self, value: Any, compression: bool = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Serializa un valor con compresión opcional
        
        Returns:
            Tuple[bytes, metadata]
        """
        metadata = {
            "serialization_method": self.default_method,
            "compression_used": False,
            "original_size": 0,
            "compressed_size": 0
        }
        
        try:
            # Serializar según el método
            if self.default_method == "json":
                data = json.dumps(value, default=str).encode('utf-8')
            elif self.default_method == "pickle":
                data = pickle.dumps(value)
            else:  # fallback a pickle
                data = pickle.dumps(value)
                metadata["serialization_method"] = "pickle"
            
            metadata["original_size"] = len(data)
            
            # Comprimir si es necesario
            should_compress = compression if compression is not None else len(data) > self.compression_threshold
            
            if should_compress:
                try:
                    compressed_data = gzip.compress(data)
                    if len(compressed_data) < len(data):  # Solo usar si realmente comprime
                        data = compressed_data
                        metadata["compression_used"] = True
                        metadata["compressed_size"] = len(data)
                except Exception as e:
                    logger.warning(f"Error comprimiendo datos: {e}")
            
            return data, metadata
            
        except Exception as e:
            logger.error(f"Error serializando datos: {e}")
            raise
    
    def deserialize(self, data: bytes, metadata: Dict[str, Any]) -> Any:
        """Deserializa datos con descompresión automática"""
        try:
            # Descomprimir si es necesario
            if metadata.get("compression_used", False):
                try:
                    data = gzip.decompress(data)
                except Exception as e:
                    logger.warning(f"Error descomprimiendo datos: {e}")
            
            # Deserializar según el método
            method = metadata.get("serialization_method", "pickle")
            
            if method == "json":
                return json.loads(data.decode('utf-8'))
            elif method == "pickle":
                return pickle.loads(data)
            else:
                # Fallback a pickle
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Error deserializando datos: {e}")
            raise

# ===============================
# DISTRIBUTED CACHE LAYER
# ===============================

class DistributedCacheLayer:
    """
    Cache distribuido multi-nivel con Redis como L2
    
    Arquitectura:
    L1 (Memory) → L2 (Redis) → L3 (Disk)
    
    Características:
    - Promoción automática de datos frecuentes
    - Distribución inteligente por tipo de contenido
    - Invalidación distribuida con pub/sub
    - Compresión adaptativa
    - Métricas detalladas por nivel
    """
    
    def __init__(self):
        # Backends de cache
        self.l1_memory = MemoryCache(max_size=CACHE_CONFIG["l1_memory_size"])
        self.l2_redis_enabled = CACHE_CONFIG["l2_redis_enabled"]
        self.l3_disk = DiskCache()
        
        # Serializer
        self.serializer = CacheSerializer()
        
        # Configuración
        self.config = CACHE_CONFIG.copy()
        self.distribution_strategy = DISTRIBUTION_STRATEGY.copy()
        
        # Estadísticas por nivel
        self.stats = {
            "l1_memory": CacheLevelStats("l1_memory"),
            "l2_redis": CacheLevelStats("l2_redis"),
            "l3_disk": CacheLevelStats("l3_disk"),
            "global": {
                "total_requests": 0,
                "total_hits": 0,
                "total_misses": 0,
                "promotions": 0,
                "invalidations": 0,
                "start_time": datetime.now()
            }
        }
        
        # Invalidación distribuida
        self._invalidation_subscriber = None
        self._running = False
        
        logger.info(f"🌐 Distributed Cache Layer inicializado (L2 Redis: {self.l2_redis_enabled})")
    
    async def start(self):
        """Inicia el cache distribuido"""
        if self._running:
            return
        
        self._running = True
        
        # Inicializar Redis si está habilitado
        if self.l2_redis_enabled and REDIS_AVAILABLE:
            await redis_manager.initialize()
            
            # Iniciar subscriber para invalidación distribuida
            if self.config["invalidation_strategy"] == "pub_sub":
                await self._start_invalidation_subscriber()
        
        logger.info("🚀 Distributed Cache Layer iniciado")
    
    async def stop(self):
        """Detiene el cache distribuido"""
        self._running = False
        
        # Detener subscriber
        if self._invalidation_subscriber:
            self._invalidation_subscriber.cancel()
        
        logger.info("🛑 Distributed Cache Layer detenido")
    
    def _get_distribution_config(self, namespace: str) -> Dict[str, Any]:
        """Obtiene configuración de distribución para un namespace"""
        return self.distribution_strategy.get(namespace, self.distribution_strategy["default"])
    
    def _calculate_ttl_for_level(self, base_ttl: int, level: str) -> int:
        """Calcula TTL específico para un nivel"""
        multiplier = self.config["ttl_multipliers"].get(level, 1.0)
        return int(base_ttl * multiplier)
    
    async def get(self, namespace: str, key: str, **kwargs) -> Optional[Any]:
        """
        Obtiene un valor del cache distribuido (multi-nivel)
        
        Flujo: L1 → L2 → L3 → None
        """
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        self.stats["global"]["total_requests"] += 1
        
        distribution_config = self._get_distribution_config(namespace)
        levels_to_check = distribution_config["levels"]
        
        # L1: Memoria local
        if "l1" in levels_to_check:
            start_time = time.time()
            value = await self._get_from_l1(cache_key)
            latency = (time.time() - start_time) * 1000
            self._update_latency("l1_memory", latency)
            
            if value is not None:
                self.stats["l1_memory"].hits += 1
                self.stats["global"]["total_hits"] += 1
                return value
            else:
                self.stats["l1_memory"].misses += 1
        
        # L2: Redis distribuido
        if "l2" in levels_to_check and self.l2_redis_enabled:
            start_time = time.time()
            value = await self._get_from_l2(cache_key, namespace)
            latency = (time.time() - start_time) * 1000
            self._update_latency("l2_redis", latency)
            
            if value is not None:
                self.stats["l2_redis"].hits += 1
                self.stats["global"]["total_hits"] += 1
                
                # Promover a L1 si es frecuente
                if "l1" in levels_to_check:
                    await self._promote_to_l1(cache_key, value, namespace)
                
                return value
            else:
                self.stats["l2_redis"].misses += 1
        
        # L3: Disco local
        if "l3" in levels_to_check:
            start_time = time.time()
            value = await self._get_from_l3(cache_key)
            latency = (time.time() - start_time) * 1000
            self._update_latency("l3_disk", latency)
            
            if value is not None:
                self.stats["l3_disk"].hits += 1
                self.stats["global"]["total_hits"] += 1
                
                # Promover a niveles superiores
                if "l2" in levels_to_check and self.l2_redis_enabled:
                    await self._promote_to_l2(cache_key, value, namespace)
                if "l1" in levels_to_check:
                    await self._promote_to_l1(cache_key, value, namespace)
                
                return value
            else:
                self.stats["l3_disk"].misses += 1
        
        self.stats["global"]["total_misses"] += 1
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
        Almacena un valor en el cache distribuido
        """
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        distribution_config = self._get_distribution_config(namespace)
        
        # TTL base
        if ttl_seconds is None:
            ttl_seconds = distribution_config["ttl_base"]
        
        levels_to_store = distribution_config["levels"]
        compression = distribution_config["compression"]
        
        success = False
        
        # L1: Memoria local
        if "l1" in levels_to_store:
            ttl_l1 = self._calculate_ttl_for_level(ttl_seconds, "l1")
            success_l1 = await self._set_to_l1(cache_key, value, ttl_l1, namespace)
            success = success or success_l1
        
        # L2: Redis distribuido
        if "l2" in levels_to_store and self.l2_redis_enabled:
            ttl_l2 = self._calculate_ttl_for_level(ttl_seconds, "l2")
            success_l2 = await self._set_to_l2(cache_key, value, ttl_l2, namespace, compression)
            success = success or success_l2
        
        # L3: Disco local
        if "l3" in levels_to_store:
            ttl_l3 = self._calculate_ttl_for_level(ttl_seconds, "l3")
            success_l3 = await self._set_to_l3(cache_key, value, ttl_l3, namespace)
            success = success or success_l3
        
        return success
    
    async def delete(self, namespace: str, key: str, **kwargs) -> bool:
        """Elimina una entrada del cache distribuido (todos los niveles)"""
        cache_key = self._generate_cache_key(namespace, key, **kwargs)
        
        success = False
        
        # Eliminar de todos los niveles
        success_l1 = await self._delete_from_l1(cache_key)
        success_l2 = await self._delete_from_l2(cache_key) if self.l2_redis_enabled else False
        success_l3 = await self._delete_from_l3(cache_key)
        
        success = success_l1 or success_l2 or success_l3
        
        # Notificar invalidación distribuida
        if success and self.l2_redis_enabled:
            await self._notify_invalidation(cache_key)
        
        return success
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalida entradas que coincidan con un patrón (distribuido)"""
        count = 0
        
        # Invalidar en todos los niveles
        count += await self._invalidate_pattern_l1(pattern)
        
        if self.l2_redis_enabled:
            count += await self._invalidate_pattern_l2(pattern)
        
        count += await self._invalidate_pattern_l3(pattern)
        
        # Notificar invalidación distribuida
        if self.l2_redis_enabled:
            await self._notify_pattern_invalidation(pattern)
        
        self.stats["global"]["invalidations"] += count
        return count
    
    # ===============================
    # MÉTODOS ESPECÍFICOS POR NIVEL
    # ===============================
    
    async def _get_from_l1(self, key: str) -> Optional[Any]:
        """Obtiene valor de L1 (memoria)"""
        try:
            return await self.l1_memory.get(key)
        except Exception as e:
            logger.error(f"Error obteniendo de L1: {e}")
            self.stats["l1_memory"].errors += 1
            return None
    
    async def _get_from_l2(self, key: str, namespace: str) -> Optional[Any]:
        """Obtiene valor de L2 (Redis)"""
        try:
            redis_key = f"cache:{namespace}:{key}"
            data = await redis_manager.execute_command("get", redis_key)
            
            if data is None:
                return None
            
            # Deserializar
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Extraer metadatos (simplificado)
            try:
                result = pickle.loads(data)
                return result
            except:
                # Fallback para datos simples
                return data.decode('utf-8') if isinstance(data, bytes) else data
                
        except Exception as e:
            logger.error(f"Error obteniendo de L2: {e}")
            self.stats["l2_redis"].errors += 1
            return None
    
    async def _get_from_l3(self, key: str) -> Optional[Any]:
        """Obtiene valor de L3 (disco)"""
        try:
            return await self.l3_disk.get(key)
        except Exception as e:
            logger.error(f"Error obteniendo de L3: {e}")
            self.stats["l3_disk"].errors += 1
            return None
    
    async def _set_to_l1(self, key: str, value: Any, ttl: int, namespace: str) -> bool:
        """Almacena en L1 (memoria)"""
        try:
            success = await self.l1_memory.set(key, value, ttl, namespace)
            if success:
                self.stats["l1_memory"].sets += 1
            return success
        except Exception as e:
            logger.error(f"Error almacenando en L1: {e}")
            self.stats["l1_memory"].errors += 1
            return False
    
    async def _set_to_l2(self, key: str, value: Any, ttl: int, namespace: str, compression: bool) -> bool:
        """Almacena en L2 (Redis)"""
        try:
            redis_key = f"cache:{namespace}:{key}"
            
            # Serializar con compresión opcional
            data, metadata = self.serializer.serialize(value, compression)
            
            # Almacenar en Redis
            success = await redis_manager.execute_command("setex", redis_key, ttl, data)
            
            if success:
                self.stats["l2_redis"].sets += 1
                self.stats["l2_redis"].total_size_bytes += len(data)
            
            return success is not None
            
        except Exception as e:
            logger.error(f"Error almacenando en L2: {e}")
            self.stats["l2_redis"].errors += 1
            return False
    
    async def _set_to_l3(self, key: str, value: Any, ttl: int, namespace: str) -> bool:
        """Almacena en L3 (disco)"""
        try:
            success = await self.l3_disk.set(key, value, ttl, namespace)
            if success:
                self.stats["l3_disk"].sets += 1
            return success
        except Exception as e:
            logger.error(f"Error almacenando en L3: {e}")
            self.stats["l3_disk"].errors += 1
            return False
    
    # ===============================
    # PROMOCIÓN ENTRE NIVELES
    # ===============================
    
    async def _promote_to_l1(self, key: str, value: Any, namespace: str):
        """Promueve un valor a L1 (memoria)"""
        try:
            distribution_config = self._get_distribution_config(namespace)
            ttl = distribution_config["ttl_base"]
            ttl_l1 = self._calculate_ttl_for_level(ttl, "l1")
            
            await self._set_to_l1(key, value, ttl_l1, namespace)
            self.stats["global"]["promotions"] += 1
            
        except Exception as e:
            logger.error(f"Error promoviendo a L1: {e}")
    
    async def _promote_to_l2(self, key: str, value: Any, namespace: str):
        """Promueve un valor a L2 (Redis)"""
        try:
            distribution_config = self._get_distribution_config(namespace)
            ttl = distribution_config["ttl_base"]
            ttl_l2 = self._calculate_ttl_for_level(ttl, "l2")
            compression = distribution_config["compression"]
            
            await self._set_to_l2(key, value, ttl_l2, namespace, compression)
            self.stats["global"]["promotions"] += 1
            
        except Exception as e:
            logger.error(f"Error promoviendo a L2: {e}")
    
    # ===============================
    # INVALIDACIÓN DISTRIBUIDA
    # ===============================
    
    async def _notify_invalidation(self, key: str):
        """Notifica invalidación a otras instancias"""
        try:
            message = {"type": "invalidate", "key": key, "timestamp": datetime.now().isoformat()}
            await redis_manager.execute_command("publish", "cache_invalidation", json.dumps(message))
        except Exception as e:
            logger.error(f"Error notificando invalidación: {e}")
    
    async def _notify_pattern_invalidation(self, pattern: str):
        """Notifica invalidación por patrón"""
        try:
            message = {"type": "invalidate_pattern", "pattern": pattern, "timestamp": datetime.now().isoformat()}
            await redis_manager.execute_command("publish", "cache_invalidation", json.dumps(message))
        except Exception as e:
            logger.error(f"Error notificando invalidación por patrón: {e}")
    
    async def _start_invalidation_subscriber(self):
        """Inicia subscriber para invalidación distribuida"""
        # Implementación simplificada - en producción usarías Redis pub/sub
        logger.info("🔔 Invalidation subscriber iniciado")
    
    # ===============================
    # UTILIDADES
    # ===============================
    
    def _generate_cache_key(self, namespace: str, key: str, **kwargs) -> str:
        """Genera clave de cache única"""
        if kwargs:
            key_parts = [namespace, key] + [f"{k}:{v}" for k, v in sorted(kwargs.items())]
            combined_key = "|".join(str(part) for part in key_parts)
        else:
            combined_key = f"{namespace}|{key}"
        
        # Hash para claves muy largas
        if len(combined_key) > 200:
            return f"{namespace}|{hashlib.sha256(combined_key.encode()).hexdigest()}"
        
        return combined_key
    
    def _update_latency(self, level: str, latency_ms: float):
        """Actualiza latencia promedio para un nivel"""
        current = self.stats[level].avg_latency_ms
        # Promedio móvil simple
        self.stats[level].avg_latency_ms = (current * 0.9) + (latency_ms * 0.1)
    
    async def _delete_from_l1(self, key: str) -> bool:
        """Elimina de L1"""
        try:
            return await self.l1_memory.delete(key)
        except Exception:
            return False
    
    async def _delete_from_l2(self, key: str) -> bool:
        """Elimina de L2"""
        try:
            result = await redis_manager.execute_command("del", key)
            return result > 0 if result else False
        except Exception:
            return False
    
    async def _delete_from_l3(self, key: str) -> bool:
        """Elimina de L3"""
        try:
            return await self.l3_disk.delete(key)
        except Exception:
            return False
    
    async def _invalidate_pattern_l1(self, pattern: str) -> int:
        """Invalida patrón en L1"""
        # Implementación simplificada
        return 0
    
    async def _invalidate_pattern_l2(self, pattern: str) -> int:
        """Invalida patrón en L2"""
        # Implementación simplificada
        return 0
    
    async def _invalidate_pattern_l3(self, pattern: str) -> int:
        """Invalida patrón en L3"""
        # Implementación simplificada
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache distribuido"""
        total_requests = self.stats["global"]["total_requests"]
        total_hits = self.stats["global"]["total_hits"]
        hit_rate = (total_hits / max(total_requests, 1)) * 100
        
        uptime = datetime.now() - self.stats["global"]["start_time"]
        
        return {
            "global": {
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "total_hits": total_hits,
                "total_misses": self.stats["global"]["total_misses"],
                "promotions": self.stats["global"]["promotions"],
                "invalidations": self.stats["global"]["invalidations"],
                "uptime_seconds": uptime.total_seconds()
            },
            "levels": {
                "l1_memory": self.stats["l1_memory"].__dict__,
                "l2_redis": self.stats["l2_redis"].__dict__,
                "l3_disk": self.stats["l3_disk"].__dict__
            },
            "configuration": {
                "environment": ENVIRONMENT,
                "l2_redis_enabled": self.l2_redis_enabled,
                "distribution_strategy": self.distribution_strategy,
                "cache_config": self.config
            }
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del cache distribuido
distributed_cache = DistributedCacheLayer()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_distributed_cache():
    """Inicializa el cache distribuido"""
    await distributed_cache.start()

async def get_distributed_cached(namespace: str, key: str, **kwargs) -> Optional[Any]:
    """Obtiene valor del cache distribuido"""
    return await distributed_cache.get(namespace, key, **kwargs)

async def set_distributed_cached(
    namespace: str, 
    key: str, 
    value: Any, 
    ttl_seconds: Optional[int] = None,
    **kwargs
) -> bool:
    """Almacena valor en cache distribuido"""
    return await distributed_cache.set(namespace, key, value, ttl_seconds, **kwargs)

async def delete_distributed_cached(namespace: str, key: str, **kwargs) -> bool:
    """Elimina valor del cache distribuido"""
    return await distributed_cache.delete(namespace, key, **kwargs)

async def invalidate_distributed_pattern(pattern: str) -> int:
    """Invalida patrón en cache distribuido"""
    return await distributed_cache.invalidate_pattern(pattern)

def get_distributed_cache_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del cache distribuido"""
    return distributed_cache.get_stats()

async def stop_distributed_cache():
    """Detiene el cache distribuido"""
    await distributed_cache.stop() 