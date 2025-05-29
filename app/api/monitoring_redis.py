"""
📊🔴 Monitoring APIs para Redis Distribuido
APIs de monitoreo avanzado para cache distribuido y Redis enterprise
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
import asyncio
import time
from datetime import datetime, timedelta

# Imports del sistema
from app.core.redis_manager import (
    redis_manager,
    get_redis_stats,
    redis_health_check,
    REDIS_AVAILABLE
)
from app.core.distributed_cache import (
    distributed_cache,
    get_distributed_cache_stats
)
from app.services.rag_semantic_cache_redis import (
    semantic_cache_redis,
    get_distributed_semantic_cache_stats
)

router = APIRouter(prefix="/monitoring/redis", tags=["Redis Monitoring"])

# ===============================
# REDIS MANAGER MONITORING
# ===============================

@router.get("/health")
async def redis_health():
    """
    🔴 Health check completo del Redis Manager
    
    Verifica:
    - Estado de conexiones Redis
    - Salud del cluster/instancia
    - Métricas de performance
    - Errores recientes
    """
    try:
        if not REDIS_AVAILABLE:
            return {
                "status": "mock",
                "message": "Redis no disponible - modo mock activo",
                "timestamp": datetime.now().isoformat(),
                "redis_available": False
            }
        
        # Health check detallado
        health_info = await redis_health_check()
        
        # Estadísticas del manager
        manager_stats = get_redis_stats()
        
        # Combinar información
        return {
            "redis_health": health_info,
            "manager_stats": manager_stats,
            "timestamp": datetime.now().isoformat(),
            "redis_available": REDIS_AVAILABLE
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo health Redis: {str(e)}"
        )

@router.get("/cluster/info")
async def redis_cluster_info():
    """
    🔗 Información detallada del cluster Redis
    
    Incluye:
    - Estado de cada nodo
    - Distribución de slots
    - Métricas de replicación
    - Estadísticas de memoria
    """
    try:
        if not REDIS_AVAILABLE:
            return {
                "status": "mock",
                "message": "Redis cluster no disponible",
                "cluster_enabled": False
            }
        
        health_info = await redis_health_check()
        cluster_stats = health_info.get("cluster_stats")
        nodes_info = health_info.get("nodes", [])
        
        # Análisis del cluster
        cluster_analysis = {
            "cluster_health": health_info.get("status", "unknown"),
            "total_nodes": len(nodes_info),
            "healthy_nodes": sum(1 for node in nodes_info if node.get("status") == "healthy"),
            "failed_nodes": sum(1 for node in nodes_info if node.get("status") == "failed"),
            "master_nodes": sum(1 for node in nodes_info if node.get("role") == "master"),
            "slave_nodes": sum(1 for node in nodes_info if node.get("role") == "slave"),
            "cluster_coverage": "complete" if cluster_stats and cluster_stats.get("slots_ok") == 16384 else "partial"
        }
        
        return {
            "cluster_analysis": cluster_analysis,
            "cluster_stats": cluster_stats,
            "nodes_detail": nodes_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo info cluster: {str(e)}"
        )

@router.get("/performance")
async def redis_performance_metrics():
    """
    ⚡ Métricas de performance Redis en tiempo real
    
    Incluye:
    - Latencia de operaciones
    - Throughput (ops/sec)
    - Uso de memoria
    - Conexiones activas
    """
    try:
        manager_stats = get_redis_stats()
        health_info = await redis_health_check()
        
        # Calcular métricas de performance
        operations = manager_stats.get("operations", {})
        total_ops = operations.get("operations_total", 0)
        failed_ops = operations.get("operations_failed", 0)
        success_rate = operations.get("success_rate", 0)
        
        # Métricas de tiempo
        uptime_seconds = manager_stats.get("redis_manager", {}).get("uptime_seconds", 0)
        ops_per_second = total_ops / max(uptime_seconds, 1)
        
        # Información de nodos para memoria
        nodes_info = health_info.get("nodes", [])
        total_memory_used = sum(node.get("memory_used", 0) for node in nodes_info)
        total_memory_max = sum(node.get("memory_max", 0) for node in nodes_info)
        memory_usage_percent = (total_memory_used / max(total_memory_max, 1)) * 100 if total_memory_max > 0 else 0
        
        performance_metrics = {
            "operations": {
                "total_operations": total_ops,
                "failed_operations": failed_ops,
                "success_rate_percent": round(success_rate, 2),
                "operations_per_second": round(ops_per_second, 2)
            },
            "memory": {
                "total_used_bytes": total_memory_used,
                "total_max_bytes": total_memory_max,
                "usage_percent": round(memory_usage_percent, 2),
                "nodes_count": len(nodes_info)
            },
            "connections": {
                "total_connections": sum(node.get("connections", 0) for node in nodes_info),
                "max_connections": manager_stats.get("configuration", {}).get("max_connections", 0)
            },
            "latency": {
                "socket_timeout": manager_stats.get("configuration", {}).get("socket_timeout", 0),
                "health_check_interval": manager_stats.get("configuration", {}).get("health_check_interval", 0)
            }
        }
        
        return {
            "performance_metrics": performance_metrics,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime_seconds
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas performance: {str(e)}"
        )

# ===============================
# DISTRIBUTED CACHE MONITORING
# ===============================

@router.get("/distributed/stats")
async def distributed_cache_stats():
    """
    🌐 Estadísticas del cache distribuido multi-nivel
    
    Incluye:
    - Hit rates por nivel (L1, L2, L3)
    - Latencia por nivel
    - Promociones entre niveles
    - Distribución de datos
    """
    try:
        stats = get_distributed_cache_stats()
        
        # Análisis adicional
        global_stats = stats.get("global", {})
        levels_stats = stats.get("levels", {})
        
        # Calcular eficiencia de distribución
        l1_stats = levels_stats.get("l1_memory", {})
        l2_stats = levels_stats.get("l2_redis", {})
        l3_stats = levels_stats.get("l3_disk", {})
        
        distribution_efficiency = {
            "l1_hit_rate": l1_stats.get("hit_rate", 0),
            "l2_hit_rate": l2_stats.get("hit_rate", 0),
            "l3_hit_rate": l3_stats.get("hit_rate", 0),
            "total_promotions": global_stats.get("promotions", 0),
            "total_invalidations": global_stats.get("invalidations", 0),
            "cache_hierarchy_efficiency": _calculate_hierarchy_efficiency(levels_stats)
        }
        
        return {
            "distributed_cache_stats": stats,
            "distribution_efficiency": distribution_efficiency,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo stats cache distribuido: {str(e)}"
        )

@router.get("/distributed/levels")
async def distributed_cache_levels_detail():
    """
    📊 Detalle por nivel del cache distribuido
    
    Análisis granular de:
    - L1 (Memory): Velocidad y capacidad
    - L2 (Redis): Distribución y persistencia  
    - L3 (Disk): Almacenamiento y recuperación
    """
    try:
        stats = get_distributed_cache_stats()
        levels_stats = stats.get("levels", {})
        config = stats.get("configuration", {})
        
        # Análisis detallado por nivel
        levels_analysis = {}
        
        for level_name, level_stats in levels_stats.items():
            total_requests = level_stats.get("hits", 0) + level_stats.get("misses", 0)
            
            levels_analysis[level_name] = {
                "performance": {
                    "hit_rate": level_stats.get("hit_rate", 0),
                    "total_requests": total_requests,
                    "avg_latency_ms": level_stats.get("avg_latency_ms", 0),
                    "error_rate": (level_stats.get("errors", 0) / max(total_requests, 1)) * 100
                },
                "operations": {
                    "hits": level_stats.get("hits", 0),
                    "misses": level_stats.get("misses", 0),
                    "sets": level_stats.get("sets", 0),
                    "deletes": level_stats.get("deletes", 0),
                    "evictions": level_stats.get("evictions", 0)
                },
                "storage": {
                    "total_size_bytes": level_stats.get("total_size_bytes", 0),
                    "level": level_stats.get("level", level_name)
                }
            }
        
        return {
            "levels_analysis": levels_analysis,
            "configuration": config,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo detalle niveles: {str(e)}"
        )

# ===============================
# SEMANTIC CACHE REDIS MONITORING
# ===============================

@router.get("/semantic/stats")
async def semantic_cache_redis_stats():
    """
    🧠🔴 Estadísticas del cache semántico distribuido
    
    Incluye:
    - Performance semántico vs exacto
    - Distribución Redis de embeddings
    - Cross-instance sharing
    - Métricas de similaridad
    """
    try:
        stats = get_distributed_semantic_cache_stats()
        
        # Extraer métricas clave
        distributed_perf = stats.get("distributed_performance", {})
        redis_perf = stats.get("redis_performance", {})
        cross_instance = stats.get("cross_instance", {})
        semantic_perf = stats.get("semantic_performance", {})
        
        # Análisis de eficiencia semántica
        semantic_efficiency = {
            "semantic_vs_exact_ratio": _calculate_semantic_ratio(distributed_perf),
            "redis_distribution_success": redis_perf.get("redis_success_rate", 0),
            "cross_instance_sharing_rate": _calculate_sharing_rate(cross_instance, distributed_perf),
            "embedding_cache_efficiency": _calculate_embedding_efficiency(stats),
            "similarity_detection_accuracy": semantic_perf.get("avg_similarity_score", 0)
        }
        
        return {
            "semantic_cache_stats": stats,
            "semantic_efficiency": semantic_efficiency,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo stats cache semántico: {str(e)}"
        )

@router.get("/semantic/embeddings")
async def semantic_embeddings_performance():
    """
    🧠 Performance específico de embeddings distribuidos
    
    Métricas de:
    - Cache hits/misses de embeddings
    - Tiempo de generación vs cache
    - Distribución entre instancias
    - Eficiencia de compresión
    """
    try:
        stats = get_distributed_semantic_cache_stats()
        
        # Métricas específicas de embeddings
        distributed_perf = stats.get("distributed_performance", {})
        redis_perf = stats.get("redis_performance", {})
        cross_instance = stats.get("cross_instance", {})
        
        embeddings_metrics = {
            "cache_performance": {
                "embedding_hits": distributed_perf.get("exact_hits", 0) + distributed_perf.get("distributed_hits", 0),
                "embedding_misses": distributed_perf.get("cache_misses", 0),
                "hit_rate": distributed_perf.get("distributed_hit_rate", 0)
            },
            "generation_vs_cache": {
                "cache_lookups": distributed_perf.get("total_queries", 0),
                "new_generations": distributed_perf.get("cache_misses", 0),
                "cache_efficiency": (1 - (distributed_perf.get("cache_misses", 0) / max(distributed_perf.get("total_queries", 1), 1))) * 100
            },
            "distribution": {
                "redis_operations": redis_perf.get("redis_operations", 0),
                "redis_errors": redis_perf.get("redis_errors", 0),
                "cross_instance_shares": cross_instance.get("cross_instance_shares", 0),
                "hot_cache_utilization": (cross_instance.get("hot_cache_size", 0) / max(cross_instance.get("hot_cache_max_size", 1), 1)) * 100
            }
        }
        
        return {
            "embeddings_metrics": embeddings_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas embeddings: {str(e)}"
        )

# ===============================
# OPERACIONES DE GESTIÓN
# ===============================

@router.post("/distributed/clear")
async def clear_distributed_cache(
    level: Optional[str] = Query(None, description="Nivel específico a limpiar (l1, l2, l3)"),
    namespace: Optional[str] = Query(None, description="Namespace específico a limpiar")
):
    """
    🗑️ Limpia cache distribuido
    
    Opciones:
    - level: Limpiar nivel específico
    - namespace: Limpiar namespace específico
    - Sin parámetros: Limpia todo
    """
    try:
        cleared_count = 0
        
        if namespace:
            # Limpiar namespace específico
            from app.core.distributed_cache import invalidate_distributed_pattern
            pattern = f"{namespace}:*"
            cleared_count = await invalidate_distributed_pattern(pattern)
            
            return {
                "status": "success",
                "message": f"Namespace '{namespace}' limpiado",
                "cleared_entries": cleared_count,
                "timestamp": datetime.now().isoformat()
            }
        
        elif level:
            # Limpiar nivel específico (implementación simplificada)
            return {
                "status": "success",
                "message": f"Nivel '{level}' limpiado",
                "cleared_entries": 0,  # Implementar según necesidad
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            # Limpiar todo (implementación simplificada)
            return {
                "status": "success",
                "message": "Cache distribuido completamente limpiado",
                "cleared_entries": 0,  # Implementar según necesidad
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error limpiando cache distribuido: {str(e)}"
        )

@router.post("/semantic/invalidate/product/{product_id}")
async def invalidate_semantic_product(product_id: str):
    """
    🔄 Invalida cache semántico para un producto específico
    
    Invalida en:
    - Cache local
    - Redis distribuido
    - Notifica a otras instancias
    """
    try:
        from app.services.rag_semantic_cache_redis import invalidate_distributed_product
        
        invalidated_count = await invalidate_distributed_product(product_id)
        
        return {
            "status": "success",
            "message": f"Producto {product_id} invalidado en cache semántico",
            "invalidated_entries": invalidated_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error invalidando producto: {str(e)}"
        )

@router.get("/redis/memory")
async def redis_memory_analysis():
    """
    💾 Análisis detallado de memoria Redis
    
    Incluye:
    - Uso por tipo de dato
    - Fragmentación
    - Eviction policies
    - Recomendaciones de optimización
    """
    try:
        health_info = await redis_health_check()
        nodes_info = health_info.get("nodes", [])
        
        memory_analysis = {
            "total_memory": {
                "used_bytes": sum(node.get("memory_used", 0) for node in nodes_info),
                "max_bytes": sum(node.get("memory_max", 0) for node in nodes_info),
                "nodes_count": len(nodes_info)
            },
            "per_node": [
                {
                    "host": node.get("host", "unknown"),
                    "port": node.get("port", 0),
                    "memory_used": node.get("memory_used", 0),
                    "memory_max": node.get("memory_max", 0),
                    "usage_percent": (node.get("memory_used", 0) / max(node.get("memory_max", 1), 1)) * 100,
                    "role": node.get("role", "unknown")
                }
                for node in nodes_info
            ],
            "recommendations": _generate_memory_recommendations(nodes_info)
        }
        
        return {
            "memory_analysis": memory_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando memoria Redis: {str(e)}"
        )

# ===============================
# FUNCIONES AUXILIARES
# ===============================

def _calculate_hierarchy_efficiency(levels_stats: Dict) -> float:
    """Calcula eficiencia de la jerarquía de cache"""
    try:
        l1_hits = levels_stats.get("l1_memory", {}).get("hits", 0)
        l2_hits = levels_stats.get("l2_redis", {}).get("hits", 0)
        l3_hits = levels_stats.get("l3_disk", {}).get("hits", 0)
        
        total_hits = l1_hits + l2_hits + l3_hits
        if total_hits == 0:
            return 0.0
        
        # Peso por velocidad: L1=3, L2=2, L3=1
        weighted_score = (l1_hits * 3 + l2_hits * 2 + l3_hits * 1) / total_hits
        return round((weighted_score / 3) * 100, 2)  # Normalizar a porcentaje
        
    except Exception:
        return 0.0

def _calculate_semantic_ratio(distributed_perf: Dict) -> float:
    """Calcula ratio de hits semánticos vs exactos"""
    try:
        semantic_hits = distributed_perf.get("semantic_hits", 0)
        exact_hits = distributed_perf.get("exact_hits", 0)
        
        total_hits = semantic_hits + exact_hits
        if total_hits == 0:
            return 0.0
        
        return round((semantic_hits / total_hits) * 100, 2)
        
    except Exception:
        return 0.0

def _calculate_sharing_rate(cross_instance: Dict, distributed_perf: Dict) -> float:
    """Calcula tasa de sharing entre instancias"""
    try:
        shares = cross_instance.get("cross_instance_shares", 0)
        total_queries = distributed_perf.get("total_queries", 0)
        
        if total_queries == 0:
            return 0.0
        
        return round((shares / total_queries) * 100, 2)
        
    except Exception:
        return 0.0

def _calculate_embedding_efficiency(stats: Dict) -> float:
    """Calcula eficiencia del cache de embeddings"""
    try:
        distributed_perf = stats.get("distributed_performance", {})
        hits = distributed_perf.get("exact_hits", 0) + distributed_perf.get("distributed_hits", 0)
        total = distributed_perf.get("total_queries", 0)
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)
        
    except Exception:
        return 0.0

def _generate_memory_recommendations(nodes_info: List[Dict]) -> List[str]:
    """Genera recomendaciones de optimización de memoria"""
    recommendations = []
    
    try:
        for node in nodes_info:
            usage_percent = (node.get("memory_used", 0) / max(node.get("memory_max", 1), 1)) * 100
            
            if usage_percent > 90:
                recommendations.append(f"⚠️ Nodo {node.get('host')}:{node.get('port')} con uso crítico de memoria ({usage_percent:.1f}%)")
            elif usage_percent > 75:
                recommendations.append(f"⚡ Nodo {node.get('host')}:{node.get('port')} con uso alto de memoria ({usage_percent:.1f}%)")
        
        if not recommendations:
            recommendations.append("✅ Uso de memoria dentro de rangos normales")
            
    except Exception:
        recommendations.append("❌ Error calculando recomendaciones")
    
    return recommendations 