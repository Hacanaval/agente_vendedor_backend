"""
RAG Cache Service Enterprise
Cache semántico inteligente para el sistema RAG con detección de consultas similares
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, field

# Imports del sistema
from app.core.cache_manager import cache_manager, get_cached, set_cached
from app.services.embeddings_service import embeddings_service

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN RAG CACHE
# ===============================

# TTL específico para componentes RAG
RAG_CACHE_TTL = {
    "query_embeddings": 86400,      # 24h - embeddings de consultas
    "product_embeddings": 172800,   # 48h - embeddings de productos
    "search_results": 3600,         # 1h - resultados de búsqueda
    "llm_responses": 1800,          # 30min - respuestas LLM
    "similarity_scores": 7200,      # 2h - scores de similaridad
    "normalized_queries": 43200,    # 12h - consultas normalizadas
}

# Umbrales de similaridad
SIMILARITY_THRESHOLDS = {
    "exact_match": 1.0,             # Match exacto
    "high_similarity": 0.95,        # Muy similar
    "medium_similarity": 0.85,      # Moderadamente similar
    "low_similarity": 0.75,         # Poco similar
}

# Patrones de normalización de consultas
QUERY_NORMALIZATION_PATTERNS = [
    # Eliminar caracteres especiales
    (r'[^\w\s]', ''),
    # Múltiples espacios a uno solo
    (r'\s+', ' '),
    # Convertir a minúsculas (se hace por separado)
    # Eliminar palabras vacías comunes
    (r'\b(el|la|los|las|un|una|de|del|en|con|para|por|que|es|son|tiene|tienes|necesito|quiero|busco)\b', ''),
]

# Sinónimos para normalización semántica
SEMANTIC_SYNONYMS = {
    "extintor": ["extinguidor", "aparato contra incendios", "equipo extinción"],
    "protección auditiva": ["tapones oídos", "protectores oído", "auriculares protección"],
    "soldadura": ["welding", "soldar", "equipo soldadura"],
    "seguridad": ["protección", "safety", "equipos seguridad"],
    "industrial": ["empresa", "fábrica", "industria"],
}

# ===============================
# ESTRUCTURAS DE DATOS
# ===============================

@dataclass
class CachedQuery:
    """Consulta cacheada con metadatos"""
    original_query: str
    normalized_query: str
    embedding: Optional[np.ndarray] = None
    embedding_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

@dataclass
class CachedSearchResult:
    """Resultado de búsqueda cacheado"""
    query_hash: str
    products: List[Dict[str, Any]]
    scores: List[float]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = RAG_CACHE_TTL["search_results"]

@dataclass
class CachedLLMResponse:
    """Respuesta LLM cacheada"""
    prompt_hash: str
    response: str
    context_products: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = RAG_CACHE_TTL["llm_responses"]

# ===============================
# SERVICIO PRINCIPAL
# ===============================

class RAGCacheService:
    """
    Servicio de cache semántico para RAG con detección inteligente de consultas similares
    """
    
    def __init__(self):
        self.cache_manager = cache_manager
        self.embeddings_service = embeddings_service
        
        # Estadísticas del cache RAG
        self.stats = {
            "query_cache_hits": 0,
            "query_cache_misses": 0,
            "embedding_cache_hits": 0,
            "embedding_cache_misses": 0,
            "search_cache_hits": 0,
            "search_cache_misses": 0,
            "llm_cache_hits": 0,
            "llm_cache_misses": 0,
            "similarity_matches": 0,
            "total_queries": 0,
        }
        
        logger.info("🧠 RAG Cache Service inicializado")
    
    # ===============================
    # NORMALIZACIÓN DE CONSULTAS
    # ===============================
    
    def normalize_query(self, query: str) -> str:
        """Normaliza una consulta para mejorar el cache hit rate"""
        if not query:
            return ""
        
        normalized = query.lower().strip()
        
        # Aplicar patrones de normalización
        for pattern, replacement in QUERY_NORMALIZATION_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized)
        
        # Aplicar sinónimos semánticos
        for canonical, synonyms in SEMANTIC_SYNONYMS.items():
            for synonym in synonyms:
                if synonym in normalized:
                    normalized = normalized.replace(synonym, canonical)
        
        # Limpiar espacios extra
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def generate_query_hash(self, query: str, context: Dict = None) -> str:
        """Genera un hash único para una consulta y su contexto"""
        normalized = self.normalize_query(query)
        
        # Incluir contexto relevante en el hash
        context_str = ""
        if context:
            # Solo incluir campos relevantes para el cache
            relevant_context = {
                k: v for k, v in context.items() 
                if k in ["user_id", "chat_id", "filters", "limit"]
            }
            context_str = json.dumps(relevant_context, sort_keys=True)
        
        combined = f"{normalized}|{context_str}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    # ===============================
    # CACHE DE EMBEDDINGS
    # ===============================
    
    async def get_cached_embedding(self, query: str) -> Optional[np.ndarray]:
        """Obtiene el embedding de una consulta del cache"""
        query_hash = self.generate_query_hash(query)
        
        try:
            cached_data = await get_cached("query_embeddings", query_hash)
            if cached_data:
                self.stats["embedding_cache_hits"] += 1
                # Convertir de lista a numpy array
                return np.array(cached_data["embedding"])
            
            self.stats["embedding_cache_misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo embedding cacheado: {e}")
            return None
    
    async def cache_embedding(self, query: str, embedding: np.ndarray) -> bool:
        """Cachea el embedding de una consulta"""
        query_hash = self.generate_query_hash(query)
        
        try:
            cache_data = {
                "query": query,
                "normalized_query": self.normalize_query(query),
                "embedding": embedding.tolist(),  # Convertir a lista para JSON
                "created_at": datetime.now().isoformat(),
            }
            
            return await set_cached(
                "query_embeddings", 
                query_hash, 
                cache_data,
                ttl_seconds=RAG_CACHE_TTL["query_embeddings"]
            )
            
        except Exception as e:
            logger.error(f"Error cacheando embedding: {e}")
            return False
    
    # ===============================
    # CACHE DE BÚSQUEDAS SEMÁNTICAS
    # ===============================
    
    async def get_cached_search_results(
        self, 
        query: str, 
        filters: Dict = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Obtiene resultados de búsqueda cacheados"""
        context = {"filters": filters, "limit": limit}
        search_hash = self.generate_query_hash(query, context)
        
        try:
            cached_results = await get_cached("search_results", search_hash)
            if cached_results:
                self.stats["search_cache_hits"] += 1
                return cached_results
            
            # Buscar por similaridad semántica
            similar_result = await self._find_similar_cached_search(query, context)
            if similar_result:
                self.stats["similarity_matches"] += 1
                self.stats["search_cache_hits"] += 1
                return similar_result
            
            self.stats["search_cache_misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo búsqueda cacheada: {e}")
            return None
    
    async def cache_search_results(
        self,
        query: str,
        products: List[Dict[str, Any]],
        scores: List[float],
        filters: Dict = None,
        limit: int = 10,
        metadata: Dict = None
    ) -> bool:
        """Cachea resultados de búsqueda semántica"""
        context = {"filters": filters, "limit": limit}
        search_hash = self.generate_query_hash(query, context)
        
        try:
            cache_data = {
                "query": query,
                "normalized_query": self.normalize_query(query),
                "products": products,
                "scores": scores,
                "filters": filters,
                "limit": limit,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
            }
            
            return await set_cached(
                "search_results",
                search_hash,
                cache_data,
                ttl_seconds=RAG_CACHE_TTL["search_results"]
            )
            
        except Exception as e:
            logger.error(f"Error cacheando búsqueda: {e}")
            return False
    
    async def _find_similar_cached_search(
        self, 
        query: str, 
        context: Dict
    ) -> Optional[Dict[str, Any]]:
        """Busca resultados de búsqueda similares en el cache"""
        try:
            # Obtener embedding de la consulta actual
            current_embedding = await self.get_cached_embedding(query)
            if current_embedding is None:
                return None
            
            # Esta es una implementación simplificada
            # En producción, mantendrías un índice de embeddings cacheados
            normalized_query = self.normalize_query(query)
            
            # Buscar consultas normalizadas similares
            # Por ahora, usamos matching de texto normalizado
            # TODO: Implementar búsqueda por embedding similarity
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando búsquedas similares: {e}")
            return None
    
    # ===============================
    # CACHE DE RESPUESTAS LLM
    # ===============================
    
    async def get_cached_llm_response(
        self,
        prompt: str,
        context_products: List[Dict[str, Any]] = None,
        model: str = "gemini"
    ) -> Optional[str]:
        """Obtiene respuesta LLM cacheada"""
        prompt_hash = self._generate_llm_hash(prompt, context_products, model)
        
        try:
            cached_response = await get_cached("llm_responses", prompt_hash)
            if cached_response:
                self.stats["llm_cache_hits"] += 1
                return cached_response["response"]
            
            # Buscar respuestas similares
            similar_response = await self._find_similar_llm_response(prompt, context_products)
            if similar_response:
                self.stats["similarity_matches"] += 1
                self.stats["llm_cache_hits"] += 1
                return similar_response
            
            self.stats["llm_cache_misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo respuesta LLM cacheada: {e}")
            return None
    
    async def cache_llm_response(
        self,
        prompt: str,
        response: str,
        context_products: List[Dict[str, Any]] = None,
        model: str = "gemini",
        metadata: Dict = None
    ) -> bool:
        """Cachea respuesta LLM"""
        prompt_hash = self._generate_llm_hash(prompt, context_products, model)
        
        try:
            cache_data = {
                "prompt": prompt,
                "response": response,
                "context_products": context_products or [],
                "model": model,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
            }
            
            return await set_cached(
                "llm_responses",
                prompt_hash,
                cache_data,
                ttl_seconds=RAG_CACHE_TTL["llm_responses"]
            )
            
        except Exception as e:
            logger.error(f"Error cacheando respuesta LLM: {e}")
            return False
    
    def _generate_llm_hash(
        self,
        prompt: str,
        context_products: List[Dict[str, Any]] = None,
        model: str = "gemini"
    ) -> str:
        """Genera hash para prompt LLM considerando contexto"""
        # Normalizar prompt
        normalized_prompt = self.normalize_query(prompt)
        
        # Hash de productos de contexto (solo IDs para consistencia)
        context_hash = ""
        if context_products:
            product_ids = sorted([str(p.get("id", "")) for p in context_products])
            context_hash = hashlib.sha256("|".join(product_ids).encode()).hexdigest()[:8]
        
        combined = f"{model}|{normalized_prompt}|{context_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    async def _find_similar_llm_response(
        self,
        prompt: str,
        context_products: List[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Busca respuestas LLM similares en el cache"""
        try:
            # Implementación simplificada
            # En producción, usarías embedding similarity
            normalized_prompt = self.normalize_query(prompt)
            
            # Por ahora, solo matching exacto de prompt normalizado
            # TODO: Implementar similarity search
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando respuestas LLM similares: {e}")
            return None
    
    # ===============================
    # INVALIDACIÓN INTELIGENTE
    # ===============================
    
    async def invalidate_product_caches(self, product_id: str) -> int:
        """Invalida caches relacionados con un producto específico"""
        try:
            count = 0
            
            # Invalidar búsquedas que incluyan este producto
            count += await cache_manager.invalidate_pattern(f"product_{product_id}")
            
            # Invalidar embeddings de productos
            count += await cache_manager.invalidate_pattern("product_embeddings")
            
            # Invalidar búsquedas recientes (podrían incluir el producto)
            count += await cache_manager.clear_namespace("search_results")
            
            logger.info(f"Invalidadas {count} entradas de cache para producto {product_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error invalidando caches de producto: {e}")
            return 0
    
    async def invalidate_all_rag_caches(self) -> int:
        """Invalida todos los caches RAG (usar con cuidado)"""
        try:
            count = 0
            
            # Limpiar todos los namespaces RAG
            for namespace in ["query_embeddings", "search_results", "llm_responses"]:
                count += await cache_manager.clear_namespace(namespace)
            
            logger.info(f"Invalidadas {count} entradas de cache RAG")
            return count
            
        except Exception as e:
            logger.error(f"Error invalidando todos los caches RAG: {e}")
            return 0
    
    # ===============================
    # MÉTRICAS Y ESTADÍSTICAS
    # ===============================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache RAG"""
        total_requests = sum([
            self.stats["query_cache_hits"] + self.stats["query_cache_misses"],
            self.stats["embedding_cache_hits"] + self.stats["embedding_cache_misses"],
            self.stats["search_cache_hits"] + self.stats["search_cache_misses"],
            self.stats["llm_cache_hits"] + self.stats["llm_cache_misses"],
        ])
        
        total_hits = sum([
            self.stats["query_cache_hits"],
            self.stats["embedding_cache_hits"],
            self.stats["search_cache_hits"],
            self.stats["llm_cache_hits"],
        ])
        
        hit_rate = (total_hits / max(total_requests, 1)) * 100
        
        return {
            "overall": {
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "total_hits": total_hits,
                "similarity_matches": self.stats["similarity_matches"],
            },
            "by_component": {
                "embeddings": {
                    "hits": self.stats["embedding_cache_hits"],
                    "misses": self.stats["embedding_cache_misses"],
                    "hit_rate": (self.stats["embedding_cache_hits"] / 
                               max(self.stats["embedding_cache_hits"] + self.stats["embedding_cache_misses"], 1)) * 100
                },
                "search_results": {
                    "hits": self.stats["search_cache_hits"],
                    "misses": self.stats["search_cache_misses"],
                    "hit_rate": (self.stats["search_cache_hits"] / 
                               max(self.stats["search_cache_hits"] + self.stats["search_cache_misses"], 1)) * 100
                },
                "llm_responses": {
                    "hits": self.stats["llm_cache_hits"],
                    "misses": self.stats["llm_cache_misses"],
                    "hit_rate": (self.stats["llm_cache_hits"] / 
                               max(self.stats["llm_cache_hits"] + self.stats["llm_cache_misses"], 1)) * 100
                }
            },
            "configuration": {
                "ttl_config": RAG_CACHE_TTL,
                "similarity_thresholds": SIMILARITY_THRESHOLDS,
            }
        }
    
    def reset_stats(self):
        """Resetea las estadísticas del cache"""
        for key in self.stats:
            self.stats[key] = 0

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del servicio
rag_cache_service = RAGCacheService()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def get_cached_rag_embedding(query: str) -> Optional[np.ndarray]:
    """Función de conveniencia para obtener embedding cacheado"""
    return await rag_cache_service.get_cached_embedding(query)

async def cache_rag_embedding(query: str, embedding: np.ndarray) -> bool:
    """Función de conveniencia para cachear embedding"""
    return await rag_cache_service.cache_embedding(query, embedding)

async def get_cached_rag_search(
    query: str, 
    filters: Dict = None, 
    limit: int = 10
) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para obtener búsqueda cacheada"""
    return await rag_cache_service.get_cached_search_results(query, filters, limit)

async def cache_rag_search(
    query: str,
    products: List[Dict[str, Any]],
    scores: List[float],
    filters: Dict = None,
    limit: int = 10,
    metadata: Dict = None
) -> bool:
    """Función de conveniencia para cachear búsqueda"""
    return await rag_cache_service.cache_search_results(
        query, products, scores, filters, limit, metadata
    )

async def get_cached_rag_llm(
    prompt: str,
    context_products: List[Dict[str, Any]] = None,
    model: str = "gemini"
) -> Optional[str]:
    """Función de conveniencia para obtener respuesta LLM cacheada"""
    return await rag_cache_service.get_cached_llm_response(prompt, context_products, model)

async def cache_rag_llm(
    prompt: str,
    response: str,
    context_products: List[Dict[str, Any]] = None,
    model: str = "gemini",
    metadata: Dict = None
) -> bool:
    """Función de conveniencia para cachear respuesta LLM"""
    return await rag_cache_service.cache_llm_response(
        prompt, response, context_products, model, metadata
    ) 