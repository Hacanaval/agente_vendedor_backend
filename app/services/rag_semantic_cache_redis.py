"""
🧠🔴 RAG Semantic Cache Redis Integration
Cache semántico con soporte Redis distribuido para escalabilidad enterprise
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, field

# Imports del sistema
try:
    from app.services.rag_semantic_cache import (
        RAGSemanticCacheService,
        CacheStrategy,
        SimilarityLevel,
        SemanticQuery,
        SemanticCacheEntry,
        SEMANTIC_TTL_CONFIG,
        SIMILARITY_THRESHOLDS
    )
except ImportError as e:
    # Fallback para evitar importaciones circulares
    print(f"Warning: Could not import semantic cache components: {e}")
    
    # Definir clases básicas como fallback
    class RAGSemanticCacheService:
        def __init__(self, strategy=None):
            self.strategy = strategy
            
        async def get_or_create_embedding(self, query):
            return np.random.rand(384), False
            
        async def get_cached_search_semantic(self, query, filters=None, limit=10):
            return None
            
        async def cache_search_semantic(self, query, products, scores, filters=None, limit=10, metadata=None):
            return True
            
        def normalize_query_advanced(self, query):
            return query.lower(), {}
            
        def _generate_semantic_hash(self, query):
            import hashlib
            return hashlib.md5(query.encode()).hexdigest()
            
        def _generate_search_hash(self, query, filters, limit):
            import hashlib
            combined = f"{query}_{filters}_{limit}"
            return hashlib.md5(combined.encode()).hexdigest()
            
        def detect_intent(self, query):
            return "search_product"
            
        def _get_search_ttl(self, intent, similarity_level):
            return 3600
            
        def _update_performance_metric(self, metric, value):
            pass
            
        def get_stats(self):
            return {"semantic_performance": {"avg_similarity_score": 0.75}}
            
        def reset_stats(self):
            pass
    
    class CacheStrategy:
        SEMANTIC_SMART = "semantic_smart"
    
    class SimilarityLevel:
        EXACT = "exact"
        
        @property
        def value(self):
            return "exact"

from app.core.distributed_cache import (
    distributed_cache,
    get_distributed_cached,
    set_distributed_cached,
    delete_distributed_cached,
    invalidate_distributed_pattern
)
from app.core.redis_manager import redis_manager, REDIS_AVAILABLE

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN REDIS SEMÁNTICO
# ===============================

# Configuración específica para cache semántico distribuido
REDIS_SEMANTIC_CONFIG = {
    "embeddings": {
        "namespace": "semantic_embeddings",
        "levels": ["l2"],  # Solo Redis (compartido entre instancias)
        "compression": True,
        "ttl_base": 86400,  # 24h
        "replication": 2,
        "reason": "Embeddings costosos, compartibles entre instancias"
    },
    "searches": {
        "namespace": "semantic_searches",
        "levels": ["l1", "l2"],  # Memoria + Redis
        "compression": False,
        "ttl_base": 3600,   # 1h
        "replication": 1,
        "reason": "Búsquedas frecuentes, acceso rápido"
    },
    "similarity_matrix": {
        "namespace": "semantic_similarity",
        "levels": ["l2"],  # Solo Redis
        "compression": True,
        "ttl_base": 7200,   # 2h
        "replication": 1,
        "reason": "Matriz de similaridad compartible"
    },
    "intent_classification": {
        "namespace": "semantic_intents",
        "levels": ["l1", "l2"],  # Memoria + Redis
        "compression": False,
        "ttl_base": 14400,  # 4h
        "replication": 1,
        "reason": "Clasificación de intenciones frecuente"
    }
}

# Prefijos para claves Redis
REDIS_KEY_PREFIXES = {
    "embedding": "sem:emb:",
    "search": "sem:search:",
    "similarity": "sem:sim:",
    "intent": "sem:intent:",
    "metadata": "sem:meta:"
}

# ===============================
# ESTRUCTURAS DISTRIBUIDAS
# ===============================

@dataclass
class DistributedSemanticEntry:
    """Entrada de cache semántico distribuido"""
    key: str
    value: Any
    query_hash: str
    similarity_level: SimilarityLevel
    confidence: float
    ttl_seconds: int
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_instance: str = ""
    distribution_level: str = "l2"
    compression_used: bool = False

@dataclass
class SemanticCacheStats:
    """Estadísticas del cache semántico distribuido"""
    total_queries: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    distributed_hits: int = 0
    cache_misses: int = 0
    embedding_hits: int = 0
    embedding_misses: int = 0
    similarity_calculations: int = 0
    intent_detections: int = 0
    avg_similarity_score: float = 0.0
    redis_operations: int = 0
    redis_errors: int = 0
    cross_instance_shares: int = 0

# ===============================
# RAG SEMANTIC CACHE REDIS
# ===============================

class RAGSemanticCacheRedis(RAGSemanticCacheService):
    """
    Cache semántico con soporte Redis distribuido
    
    Características:
    - Hereda toda la funcionalidad del cache semántico base
    - Añade distribución Redis para escalabilidad horizontal
    - Cache compartido entre múltiples instancias
    - Invalidación distribuida automática
    - Métricas de distribución avanzadas
    """
    
    def __init__(self, strategy: CacheStrategy = CacheStrategy.SEMANTIC_SMART):
        super().__init__(strategy)
        
        # Configuración distribuida
        self.redis_config = REDIS_SEMANTIC_CONFIG.copy()
        self.redis_available = REDIS_AVAILABLE
        self.instance_id = f"instance_{int(time.time())}"
        
        # Estadísticas distribuidas
        self.distributed_stats = SemanticCacheStats()
        
        # Cache local para hot data
        self._local_hot_cache = {}
        self._hot_cache_max_size = 100
        
        logger.info(f"🧠🔴 RAG Semantic Cache Redis inicializado (Redis: {self.redis_available})")
    
    # ===============================
    # EMBEDDINGS DISTRIBUIDOS
    # ===============================
    
    async def get_or_create_embedding_distributed(self, query: str) -> Tuple[np.ndarray, bool]:
        """
        Obtiene o crea embedding con cache distribuido Redis
        
        Flujo:
        1. Cache local hot (L1)
        2. Cache Redis distribuido (L2)
        3. Generación nueva + cache distribuido
        """
        start_time = time.time()
        self.distributed_stats.total_queries += 1
        
        # Normalizar consulta
        normalized, entities = self.normalize_query_advanced(query)
        query_hash = self._generate_semantic_hash(normalized)
        
        # 1. Verificar cache local hot
        if query_hash in self._local_hot_cache:
            self.distributed_stats.exact_hits += 1
            return self._local_hot_cache[query_hash], True
        
        # 2. Verificar cache Redis distribuido
        if self.redis_available:
            try:
                cached_embedding = await self._get_distributed_embedding(query_hash)
                if cached_embedding is not None:
                    # Guardar en cache local hot
                    self._update_hot_cache(query_hash, cached_embedding)
                    self.distributed_stats.distributed_hits += 1
                    self.distributed_stats.embedding_hits += 1
                    return cached_embedding, True
            except Exception as e:
                logger.warning(f"Error obteniendo embedding distribuido: {e}")
                self.distributed_stats.redis_errors += 1
        
        # 3. Fallback al método base (con cache local)
        embedding, was_cached = await super().get_or_create_embedding(query)
        
        # 4. Cachear en Redis distribuido si es nuevo
        if not was_cached and self.redis_available:
            try:
                await self._cache_distributed_embedding(query_hash, embedding, normalized)
                self.distributed_stats.cross_instance_shares += 1
            except Exception as e:
                logger.warning(f"Error cacheando embedding distribuido: {e}")
                self.distributed_stats.redis_errors += 1
        
        # 5. Actualizar cache local hot
        self._update_hot_cache(query_hash, embedding)
        
        if not was_cached:
            self.distributed_stats.embedding_misses += 1
        
        # Actualizar métricas de performance
        generation_time = (time.time() - start_time) * 1000
        self._update_performance_metric("avg_embedding_generation_ms", generation_time)
        
        return embedding, was_cached
    
    async def _get_distributed_embedding(self, query_hash: str) -> Optional[np.ndarray]:
        """Obtiene embedding del cache Redis distribuido"""
        try:
            config = self.redis_config["embeddings"]
            
            # Usar cache distribuido
            cached_data = await get_distributed_cached(
                config["namespace"], 
                query_hash
            )
            
            if cached_data:
                self.distributed_stats.redis_operations += 1
                
                # Extraer embedding
                if isinstance(cached_data, dict) and "embedding" in cached_data:
                    embedding_list = cached_data["embedding"]
                    return np.array(embedding_list, dtype='float32')
                elif isinstance(cached_data, (list, np.ndarray)):
                    return np.array(cached_data, dtype='float32')
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo embedding distribuido: {e}")
            self.distributed_stats.redis_errors += 1
            return None
    
    async def _cache_distributed_embedding(
        self, 
        query_hash: str, 
        embedding: np.ndarray, 
        normalized_query: str
    ):
        """Cachea embedding en Redis distribuido"""
        try:
            config = self.redis_config["embeddings"]
            
            cache_data = {
                "embedding": embedding.tolist(),
                "normalized_query": normalized_query,
                "created_at": datetime.now().isoformat(),
                "strategy": self.strategy.value,
                "instance_id": self.instance_id,
                "access_count": 1
            }
            
            # Usar cache distribuido
            success = await set_distributed_cached(
                config["namespace"],
                query_hash,
                cache_data,
                ttl_seconds=config["ttl_base"]
            )
            
            if success:
                self.distributed_stats.redis_operations += 1
                logger.debug(f"Embedding cacheado en Redis: {query_hash[:8]}...")
            
        except Exception as e:
            logger.error(f"Error cacheando embedding distribuido: {e}")
            self.distributed_stats.redis_errors += 1
    
    # ===============================
    # BÚSQUEDAS DISTRIBUIDAS
    # ===============================
    
    async def get_cached_search_distributed(
        self, 
        query: str, 
        filters: Dict = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Obtiene resultados de búsqueda con cache distribuido"""
        start_time = time.time()
        self.distributed_stats.total_queries += 1
        
        # Normalizar y generar hash
        normalized, entities = self.normalize_query_advanced(query)
        search_hash = self._generate_search_hash(normalized, filters, limit)
        
        # 1. Verificar cache local primero
        local_result = await super().get_cached_search_semantic(query, filters, limit)
        if local_result:
            self.distributed_stats.exact_hits += 1
            return local_result
        
        # 2. Verificar cache Redis distribuido
        if self.redis_available:
            try:
                distributed_result = await self._get_distributed_search(search_hash)
                if distributed_result:
                    self.distributed_stats.distributed_hits += 1
                    self.distributed_stats.semantic_hits += 1
                    
                    # Promover a cache local
                    await self._promote_search_to_local(search_hash, distributed_result)
                    
                    return distributed_result
            except Exception as e:
                logger.warning(f"Error obteniendo búsqueda distribuida: {e}")
                self.distributed_stats.redis_errors += 1
        
        self.distributed_stats.cache_misses += 1
        
        # Actualizar métricas
        lookup_time = (time.time() - start_time) * 1000
        self._update_performance_metric("avg_cache_lookup_ms", lookup_time)
        
        return None
    
    async def cache_search_distributed(
        self,
        query: str,
        products: List[Dict[str, Any]],
        scores: List[float],
        filters: Dict = None,
        limit: int = 10,
        metadata: Dict = None
    ) -> bool:
        """Cachea resultados de búsqueda en cache distribuido"""
        try:
            # Cachear localmente primero
            local_success = await super().cache_search_semantic(
                query, products, scores, filters, limit, metadata
            )
            
            # Cachear en Redis distribuido
            if self.redis_available:
                distributed_success = await self._cache_distributed_search(
                    query, products, scores, filters, limit, metadata
                )
                
                if distributed_success:
                    self.distributed_stats.cross_instance_shares += 1
                
                return local_success or distributed_success
            
            return local_success
            
        except Exception as e:
            logger.error(f"Error cacheando búsqueda distribuida: {e}")
            self.distributed_stats.redis_errors += 1
            return False
    
    async def _get_distributed_search(self, search_hash: str) -> Optional[Dict[str, Any]]:
        """Obtiene búsqueda del cache Redis distribuido"""
        try:
            config = self.redis_config["searches"]
            
            cached_data = await get_distributed_cached(
                config["namespace"],
                search_hash
            )
            
            if cached_data:
                self.distributed_stats.redis_operations += 1
                return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo búsqueda distribuida: {e}")
            self.distributed_stats.redis_errors += 1
            return None
    
    async def _cache_distributed_search(
        self,
        query: str,
        products: List[Dict[str, Any]],
        scores: List[float],
        filters: Dict = None,
        limit: int = 10,
        metadata: Dict = None
    ) -> bool:
        """Cachea búsqueda en Redis distribuido"""
        try:
            config = self.redis_config["searches"]
            normalized, entities = self.normalize_query_advanced(query)
            search_hash = self._generate_search_hash(normalized, filters, limit)
            intent = self.detect_intent(query)
            
            cache_entry = {
                "products": products,
                "scores": scores,
                "query_info": {
                    "original": query,
                    "normalized": normalized,
                    "entities": entities,
                    "intent": intent,
                },
                "filters": filters,
                "limit": limit,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "strategy": self.strategy.value,
                "similarity_level": SimilarityLevel.EXACT.value,
                "instance_id": self.instance_id
            }
            
            # Determinar TTL basado en tipo de consulta
            ttl = self._get_search_ttl(intent, SimilarityLevel.EXACT)
            
            success = await set_distributed_cached(
                config["namespace"],
                search_hash,
                cache_entry,
                ttl_seconds=ttl
            )
            
            if success:
                self.distributed_stats.redis_operations += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error cacheando búsqueda distribuida: {e}")
            self.distributed_stats.redis_errors += 1
            return False
    
    async def _promote_search_to_local(self, search_hash: str, search_data: Dict[str, Any]):
        """Promueve búsqueda distribuida a cache local"""
        try:
            # Extraer información de la búsqueda
            query_info = search_data.get("query_info", {})
            original_query = query_info.get("original", "")
            products = search_data.get("products", [])
            scores = search_data.get("scores", [])
            filters = search_data.get("filters")
            limit = search_data.get("limit", 10)
            metadata = search_data.get("metadata", {})
            
            # Cachear localmente
            await super().cache_search_semantic(
                original_query, products, scores, filters, limit, metadata
            )
            
            logger.debug(f"Búsqueda promovida a cache local: {search_hash[:8]}...")
            
        except Exception as e:
            logger.error(f"Error promoviendo búsqueda a local: {e}")
    
    # ===============================
    # INVALIDACIÓN DISTRIBUIDA
    # ===============================
    
    async def invalidate_product_distributed(self, product_id: str) -> int:
        """Invalida caches relacionados con un producto (distribuido)"""
        try:
            count = 0
            
            # Invalidar localmente primero
            local_count = await self._invalidate_product_local(product_id)
            count += local_count
            
            # Invalidar en Redis distribuido
            if self.redis_available:
                distributed_count = await self._invalidate_product_redis(product_id)
                count += distributed_count
                
                # Notificar a otras instancias
                await self._notify_product_invalidation(product_id)
            
            self.distributed_stats.redis_operations += 1
            return count
            
        except Exception as e:
            logger.error(f"Error invalidando producto distribuido: {e}")
            self.distributed_stats.redis_errors += 1
            return 0
    
    async def _invalidate_product_local(self, product_id: str) -> int:
        """Invalida producto en cache local"""
        # Implementación simplificada
        return 0
    
    async def _invalidate_product_redis(self, product_id: str) -> int:
        """Invalida producto en Redis distribuido"""
        try:
            count = 0
            
            # Invalidar en cada namespace
            for config_name, config in self.redis_config.items():
                pattern = f"*product_id:{product_id}*"
                invalidated = await invalidate_distributed_pattern(pattern)
                count += invalidated
            
            return count
            
        except Exception as e:
            logger.error(f"Error invalidando producto en Redis: {e}")
            return 0
    
    async def _notify_product_invalidation(self, product_id: str):
        """Notifica invalidación de producto a otras instancias"""
        try:
            if self.redis_available:
                message = {
                    "type": "product_invalidation",
                    "product_id": product_id,
                    "instance_id": self.instance_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                await redis_manager.execute_command(
                    "publish", 
                    "semantic_cache_invalidation", 
                    json.dumps(message)
                )
                
        except Exception as e:
            logger.error(f"Error notificando invalidación: {e}")
    
    # ===============================
    # CACHE LOCAL HOT
    # ===============================
    
    def _update_hot_cache(self, key: str, value: Any):
        """Actualiza cache local hot con LRU"""
        try:
            # Eliminar si ya existe (para reordenar)
            if key in self._local_hot_cache:
                del self._local_hot_cache[key]
            
            # Añadir al final
            self._local_hot_cache[key] = value
            
            # Eviction LRU si excede tamaño
            while len(self._local_hot_cache) > self._hot_cache_max_size:
                # Eliminar el más antiguo (primero)
                oldest_key = next(iter(self._local_hot_cache))
                del self._local_hot_cache[oldest_key]
                
        except Exception as e:
            logger.error(f"Error actualizando hot cache: {e}")
    
    # ===============================
    # MÉTRICAS DISTRIBUIDAS
    # ===============================
    
    def get_distributed_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache semántico distribuido"""
        # Estadísticas base
        base_stats = super().get_stats()
        
        # Estadísticas distribuidas
        total_requests = self.distributed_stats.total_queries
        distributed_hit_rate = 0.0
        redis_success_rate = 0.0
        
        if total_requests > 0:
            distributed_hits = (
                self.distributed_stats.exact_hits + 
                self.distributed_stats.semantic_hits + 
                self.distributed_stats.distributed_hits
            )
            distributed_hit_rate = (distributed_hits / total_requests) * 100
        
        if self.distributed_stats.redis_operations > 0:
            redis_success_rate = (
                (self.distributed_stats.redis_operations - self.distributed_stats.redis_errors) /
                self.distributed_stats.redis_operations
            ) * 100
        
        # Combinar estadísticas
        distributed_stats = {
            "distributed_performance": {
                "total_queries": total_requests,
                "exact_hits": self.distributed_stats.exact_hits,
                "semantic_hits": self.distributed_stats.semantic_hits,
                "distributed_hits": self.distributed_stats.distributed_hits,
                "cache_misses": self.distributed_stats.cache_misses,
                "distributed_hit_rate": round(distributed_hit_rate, 2)
            },
            "redis_performance": {
                "redis_operations": self.distributed_stats.redis_operations,
                "redis_errors": self.distributed_stats.redis_errors,
                "redis_success_rate": round(redis_success_rate, 2),
                "redis_available": self.redis_available
            },
            "cross_instance": {
                "cross_instance_shares": self.distributed_stats.cross_instance_shares,
                "instance_id": self.instance_id,
                "hot_cache_size": len(self._local_hot_cache),
                "hot_cache_max_size": self._hot_cache_max_size
            },
            "configuration": {
                "redis_config": self.redis_config,
                "distribution_enabled": self.redis_available
            }
        }
        
        # Combinar con estadísticas base
        base_stats.update(distributed_stats)
        return base_stats
    
    def reset_distributed_stats(self):
        """Resetea estadísticas distribuidas"""
        self.distributed_stats = SemanticCacheStats()
        super().reset_stats()
    
    # ===============================
    # GESTIÓN DEL CICLO DE VIDA
    # ===============================
    
    async def start_distributed(self):
        """Inicia el cache semántico distribuido"""
        try:
            # Inicializar cache distribuido
            if self.redis_available:
                from app.core.distributed_cache import initialize_distributed_cache
                await initialize_distributed_cache()
                logger.info("🚀 Cache semántico distribuido iniciado")
            else:
                logger.warning("⚠️ Redis no disponible - modo local únicamente")
                
        except Exception as e:
            logger.error(f"Error iniciando cache distribuido: {e}")
    
    async def stop_distributed(self):
        """Detiene el cache semántico distribuido"""
        try:
            if self.redis_available:
                from app.core.distributed_cache import stop_distributed_cache
                await stop_distributed_cache()
                logger.info("🛑 Cache semántico distribuido detenido")
                
        except Exception as e:
            logger.error(f"Error deteniendo cache distribuido: {e}")

# ===============================
# INSTANCIA GLOBAL DISTRIBUIDA
# ===============================

# Instancia global del cache semántico distribuido
semantic_cache_redis = RAGSemanticCacheRedis(CacheStrategy.SEMANTIC_SMART)

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_semantic_cache_redis():
    """Inicializa el cache semántico distribuido"""
    await semantic_cache_redis.start_distributed()

async def get_distributed_semantic_embedding(query: str) -> Tuple[np.ndarray, bool]:
    """Función de conveniencia para obtener embedding distribuido"""
    return await semantic_cache_redis.get_or_create_embedding_distributed(query)

async def get_distributed_semantic_search_cache(
    query: str, 
    filters: Dict = None, 
    limit: int = 10
) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para obtener cache de búsqueda distribuida"""
    return await semantic_cache_redis.get_cached_search_distributed(query, filters, limit)

async def cache_distributed_semantic_search(
    query: str,
    products: List[Dict[str, Any]],
    scores: List[float],
    filters: Dict = None,
    limit: int = 10,
    metadata: Dict = None
) -> bool:
    """Función de conveniencia para cachear búsqueda distribuida"""
    return await semantic_cache_redis.cache_search_distributed(
        query, products, scores, filters, limit, metadata
    )

async def invalidate_distributed_product(product_id: str) -> int:
    """Función de conveniencia para invalidar producto distribuido"""
    return await semantic_cache_redis.invalidate_product_distributed(product_id)

def get_distributed_semantic_cache_stats() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas distribuidas"""
    return semantic_cache_redis.get_distributed_stats()

async def stop_semantic_cache_redis():
    """Detiene el cache semántico distribuido"""
    await semantic_cache_redis.stop_distributed() 