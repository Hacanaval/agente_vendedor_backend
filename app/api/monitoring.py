"""
API de Monitoreo Enterprise
Métricas detalladas para observabilidad en producción
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import psutil
import platform

from app.core.database import get_db, check_database_health, get_connection_stats
from app.core.websocket_manager import ws_manager
from app.core.rate_limiting import rate_limiter, export_rate_limits_config
from app.core.cache_manager import cache_manager
from app.services.embeddings_service import get_embeddings_stats
from app.models.responses import StatusEnum

router = APIRouter(prefix="/monitoring", tags=["Monitoreo Enterprise"])
logger = logging.getLogger(__name__)

# ===============================
# MÉTRICAS GENERALES DEL SISTEMA
# ===============================

@router.get("/overview")
async def get_system_overview():
    """Resumen general del estado del sistema"""
    try:
        # Obtener todas las métricas principales
        db_health = await check_database_health()
        ws_stats = ws_manager.get_connection_stats()
        rl_stats = rate_limiter.get_stats()
        embeddings_stats = get_embeddings_stats()
        
        # Métricas del sistema operativo
        try:
            system_stats = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "boot_time": psutil.boot_time(),
                "platform": platform.platform()
            }
        except Exception as e:
            system_stats = {"error": str(e)}
        
        # Calcular salud general
        health_score = 100
        issues = []
        
        # Verificar problemas críticos
        if db_health.get("status") != "healthy":
            health_score -= 30
            issues.append("Base de datos no saludable")
        
        if ws_stats["current_connections"] > ws_stats["limits"]["max_global"] * 0.9:
            health_score -= 20
            issues.append("Conexiones WebSocket cerca del límite")
        
        if rl_stats["block_rate"] > 15:
            health_score -= 15
            issues.append("Alto rate de bloqueo de requests")
        
        if system_stats.get("cpu_percent", 0) > 80:
            health_score -= 10
            issues.append("CPU alta")
        
        if system_stats.get("memory_percent", 0) > 85:
            health_score -= 10
            issues.append("Memoria alta")
        
        # Estado general
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "database_healthy": db_health.get("status") == "healthy",
                "active_websockets": ws_stats["current_connections"],
                "rate_limit_blocks": rl_stats["requests_blocked"],
                "embeddings_ready": embeddings_stats.get("initialized", False)
            },
            "issues": issues,
            "system_resources": system_stats
        }
        
    except Exception as e:
        logger.error(f"Error en overview del sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE BASE DE DATOS
# ===============================

@router.get("/database")
async def get_database_metrics():
    """Métricas detalladas de la base de datos"""
    try:
        health = await check_database_health()
        connection_stats = await get_connection_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "connection_pool": connection_stats,
            "performance": {
                "pool_utilization": (
                    connection_stats.get("connections_checked_out", 0) / 
                    max(connection_stats.get("pool_size_configured", 1), 1) * 100
                ),
                "overflow_usage": (
                    connection_stats.get("connections_overflow", 0) / 
                    max(connection_stats.get("max_overflow_configured", 1), 1) * 100
                )
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de BD: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE WEBSOCKETS
# ===============================

@router.get("/websockets")
async def get_websocket_metrics():
    """Métricas detalladas de WebSockets"""
    try:
        stats = ws_manager.get_connection_stats()
        
        # Calcular métricas adicionales
        utilization = (
            stats["current_connections"] / 
            max(stats["limits"]["max_global"], 1) * 100
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "utilization": {
                "global_percent": utilization,
                "status": "high" if utilization > 80 else "medium" if utilization > 50 else "low"
            },
            "recommendations": []
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de WebSockets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/websockets/active")
async def get_active_connections():
    """Lista de conexiones WebSocket activas (sin datos sensibles)"""
    try:
        connections_info = []
        
        for conn_id, conn in ws_manager.connections.items():
            connections_info.append({
                "connection_id": conn_id[:8] + "...",  # ID parcial por privacidad
                "chat_id": conn.chat_id,
                "state": conn.state.value,
                "connected_at": conn.connected_at.isoformat(),
                "duration_seconds": conn.connection_duration.total_seconds(),
                "message_count": conn.message_count,
                "bytes_sent": conn.bytes_sent,
                "bytes_received": conn.bytes_received,
                "last_ping": conn.last_ping.isoformat() if conn.last_ping else None
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_connections": len(connections_info),
            "connections": connections_info
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo conexiones activas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE RATE LIMITING
# ===============================

@router.get("/rate-limiting")
async def get_rate_limiting_metrics():
    """Métricas detalladas de rate limiting"""
    try:
        stats = rate_limiter.get_stats()
        config = export_rate_limits_config()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "configuration": config,
            "analysis": {
                "block_rate_status": (
                    "high" if stats["block_rate"] > 10 else 
                    "medium" if stats["block_rate"] > 5 else "low"
                ),
                "most_restrictive_limits": [
                    name for name, limit in config.items() 
                    if limit["requests"] < 50 and limit["enabled"]
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de rate limiting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rate-limiting/reset/{limit_name}")
async def reset_rate_limit(
    limit_name: str,
    identifier: str = Query(..., description="Identificador a resetear")
):
    """Resetea un límite específico para un identificador"""
    try:
        await rate_limiter.reset_limit(identifier, limit_name)
        return {
            "status": "success",
            "message": f"Límite {limit_name} reseteado para {identifier}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reseteando rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE EMBEDDINGS
# ===============================

@router.get("/embeddings")
async def get_embeddings_metrics():
    """Métricas del sistema de embeddings semánticos"""
    try:
        stats = get_embeddings_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "recommendations": [
                "Inicializar índice" if not stats.get("initialized") else None,
                "Reconstruir índice si hay muchos productos nuevos" if stats.get("total_products", 0) > 1000 else None
            ]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE CACHE ENTERPRISE
# ===============================

@router.get("/cache")
async def get_cache_metrics():
    """Métricas detalladas del sistema de cache enterprise"""
    try:
        stats = cache_manager.get_stats()
        
        # Análisis de performance
        global_hit_rate = stats["global"]["hit_rate"]
        memory_hit_rate = stats["levels"]["memory"]["hit_rate"]
        disk_hit_rate = stats["levels"]["disk"]["hit_rate"]
        
        performance_status = "excellent" if global_hit_rate > 80 else \
                           "good" if global_hit_rate > 60 else \
                           "poor" if global_hit_rate > 30 else "critical"
        
        recommendations = []
        if global_hit_rate < 50:
            recommendations.append("Considerar aumentar TTL para contenido estable")
        if memory_hit_rate < 70:
            recommendations.append("Aumentar tamaño del cache en memoria")
        if stats["levels"]["memory"]["evictions"] > 100:
            recommendations.append("Cache en memoria saturado - considerar optimización")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "performance": {
                "status": performance_status,
                "global_hit_rate": global_hit_rate,
                "memory_hit_rate": memory_hit_rate,
                "disk_hit_rate": disk_hit_rate
            },
            "recommendations": [r for r in recommendations if r]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/levels")
async def get_cache_levels_detail():
    """Detalle de cada nivel de cache"""
    try:
        stats = cache_manager.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "levels": {
                "L1_memory": {
                    **stats["levels"]["memory"],
                    "description": "Cache en memoria - Ultra rápido (1-5ms)",
                    "priority": "highest"
                },
                "L2_disk": {
                    **stats["levels"]["disk"],
                    "description": "Cache en disco - Rápido (10-50ms)",
                    "priority": "high"
                }
            },
            "cache_flow": {
                "description": "L1 (memoria) -> L2 (disco) -> Source (BD/API)",
                "promotion": "Los datos se promueven de L2 a L1 en acceso",
                "eviction": "LRU en memoria, TTL en ambos niveles"
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo detalle de niveles de cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_cache(
    namespace: Optional[str] = Query(None, description="Namespace específico a limpiar")
):
    """Limpia el cache (todo o por namespace)"""
    try:
        if namespace:
            cleared = await cache_manager.clear_namespace(namespace)
            message = f"Cache del namespace '{namespace}' limpiado"
        else:
            memory_cleared = await cache_manager.memory_cache.clear()
            disk_cleared = await cache_manager.disk_cache.clear()
            cleared = memory_cleared + disk_cleared
            message = "Todo el cache limpiado"
        
        return {
            "status": "success",
            "message": message,
            "entries_cleared": cleared,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error limpiando cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/invalidate")
async def invalidate_cache_pattern(
    pattern: str = Query(..., description="Patrón para invalidar entradas")
):
    """Invalida entradas de cache que coincidan con un patrón"""
    try:
        invalidated = await cache_manager.invalidate_pattern(pattern)
        
        return {
            "status": "success",
            "message": f"Entradas invalidadas con patrón: {pattern}",
            "entries_invalidated": invalidated,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error invalidando cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/efficiency")
async def get_cache_efficiency():
    """Análisis de eficiencia del cache"""
    try:
        stats = cache_manager.get_stats()
        
        # Calcular métricas de eficiencia
        global_stats = stats["global"]
        memory_stats = stats["levels"]["memory"]
        disk_stats = stats["levels"]["disk"]
        
        total_requests = global_stats["total_requests"]
        if total_requests == 0:
            return {
                "status": "no_data",
                "message": "No hay suficientes datos para análisis"
            }
        
        # Eficiencia por nivel
        memory_efficiency = (memory_stats["hits"] / max(total_requests, 1)) * 100
        disk_efficiency = (disk_stats["hits"] / max(total_requests, 1)) * 100
        
        # Análisis de costos (estimado)
        memory_cost_saved = memory_stats["hits"] * 0.001  # 1ms ahorrado por hit
        disk_cost_saved = disk_stats["hits"] * 0.05      # 50ms ahorrado por hit
        
        # Recomendaciones de optimización
        optimizations = []
        
        if memory_efficiency < 30:
            optimizations.append({
                "type": "memory_size",
                "priority": "high",
                "description": "Aumentar tamaño del cache en memoria",
                "impact": "Reducir latencia promedio"
            })
        
        if disk_efficiency < 20:
            optimizations.append({
                "type": "ttl_tuning",
                "priority": "medium", 
                "description": "Ajustar TTL para mejor retención",
                "impact": "Mejorar hit rate en disco"
            })
        
        if memory_stats["evictions"] > memory_stats["hits"] * 0.1:
            optimizations.append({
                "type": "eviction_rate",
                "priority": "high",
                "description": "Cache en memoria saturado",
                "impact": "Datos útiles siendo eliminados prematuramente"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "efficiency": {
                "global_hit_rate": global_stats["hit_rate"],
                "memory_efficiency": memory_efficiency,
                "disk_efficiency": disk_efficiency,
                "total_requests": total_requests,
                "cost_savings": {
                    "memory_ms_saved": memory_cost_saved,
                    "disk_ms_saved": disk_cost_saved,
                    "total_ms_saved": memory_cost_saved + disk_cost_saved
                }
            },
            "optimizations": optimizations,
            "health": {
                "status": "excellent" if global_stats["hit_rate"] > 80 else
                         "good" if global_stats["hit_rate"] > 60 else
                         "needs_attention",
                "memory_pressure": "high" if memory_stats["evictions"] > 50 else "normal",
                "disk_usage": f"{disk_stats['total_size_mb']:.1f}MB / {disk_stats['max_size_mb']}MB"
            }
        }
        
    except Exception as e:
        logger.error(f"Error analizando eficiencia de cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE CACHE RAG ENTERPRISE
# ===============================

@router.get("/rag-cache")
async def get_rag_cache_metrics():
    """Métricas específicas del cache RAG semántico"""
    try:
        from app.services.rag_cache_service import rag_cache_service
        
        stats = rag_cache_service.get_cache_stats()
        
        # Análisis de performance RAG
        overall_hit_rate = stats["overall"]["hit_rate"]
        embedding_hit_rate = stats["by_component"]["embeddings"]["hit_rate"]
        search_hit_rate = stats["by_component"]["search_results"]["hit_rate"]
        llm_hit_rate = stats["by_component"]["llm_responses"]["hit_rate"]
        
        performance_status = "excellent" if overall_hit_rate > 80 else \
                           "good" if overall_hit_rate > 60 else \
                           "poor" if overall_hit_rate > 30 else "critical"
        
        # Recomendaciones específicas para RAG
        recommendations = []
        if embedding_hit_rate < 70:
            recommendations.append("Aumentar TTL de embeddings para consultas similares")
        if search_hit_rate < 60:
            recommendations.append("Mejorar normalización de consultas para mejor cache hit")
        if llm_hit_rate < 50:
            recommendations.append("Implementar templates de respuestas para consultas frecuentes")
        if stats["overall"]["similarity_matches"] < stats["overall"]["total_hits"] * 0.1:
            recommendations.append("Mejorar detección de consultas similares")
        
        # Estimación de ahorro de costos
        total_hits = stats["overall"]["total_hits"]
        embedding_savings = stats["by_component"]["embeddings"]["hits"] * 0.1  # 100ms ahorrados
        search_savings = stats["by_component"]["search_results"]["hits"] * 0.5   # 500ms ahorrados
        llm_savings = stats["by_component"]["llm_responses"]["hits"] * 2.0       # 2s ahorrados
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "performance": {
                "status": performance_status,
                "overall_hit_rate": overall_hit_rate,
                "component_hit_rates": {
                    "embeddings": embedding_hit_rate,
                    "search_results": search_hit_rate,
                    "llm_responses": llm_hit_rate
                }
            },
            "cost_savings": {
                "total_time_saved_seconds": embedding_savings + search_savings + llm_savings,
                "embedding_time_saved": embedding_savings,
                "search_time_saved": search_savings,
                "llm_time_saved": llm_savings,
                "estimated_cost_reduction_percent": min(80, overall_hit_rate * 0.8)
            },
            "recommendations": [r for r in recommendations if r]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de cache RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rag-cache/components")
async def get_rag_cache_components():
    """Detalle de cada componente del cache RAG"""
    try:
        from app.services.rag_cache_service import rag_cache_service
        
        stats = rag_cache_service.get_cache_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "components": {
                "embeddings": {
                    **stats["by_component"]["embeddings"],
                    "description": "Cache de embeddings de consultas",
                    "ttl_hours": stats["configuration"]["ttl_config"]["query_embeddings"] / 3600,
                    "impact": "Evita recálculo de embeddings (100ms+ ahorrados)",
                    "priority": "critical"
                },
                "search_results": {
                    **stats["by_component"]["search_results"],
                    "description": "Cache de resultados de búsqueda FAISS",
                    "ttl_hours": stats["configuration"]["ttl_config"]["search_results"] / 3600,
                    "impact": "Evita búsqueda FAISS completa (500ms+ ahorrados)",
                    "priority": "high"
                },
                "llm_responses": {
                    **stats["by_component"]["llm_responses"],
                    "description": "Cache de respuestas LLM generadas",
                    "ttl_hours": stats["configuration"]["ttl_config"]["llm_responses"] / 3600,
                    "impact": "Evita llamadas LLM costosas (2s+ ahorrados)",
                    "priority": "high"
                }
            },
            "cache_flow": {
                "description": "Flujo de cache RAG optimizado",
                "steps": [
                    "1. Verificar cache de búsqueda completa",
                    "2. Si miss → verificar cache de embedding",
                    "3. Si miss → generar embedding y cachear",
                    "4. Ejecutar búsqueda FAISS",
                    "5. Verificar cache de respuesta LLM",
                    "6. Si miss → generar respuesta y cachear",
                    "7. Cachear resultado completo"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo componentes de cache RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag-cache/clear")
async def clear_rag_cache(
    component: Optional[str] = Query(None, description="Componente específico a limpiar")
):
    """Limpia el cache RAG (todo o por componente)"""
    try:
        from app.services.rag_cache_service import rag_cache_service
        
        if component:
            if component not in ["embeddings", "search_results", "llm_responses"]:
                raise HTTPException(
                    status_code=400, 
                    detail="Componente debe ser: embeddings, search_results, o llm_responses"
                )
            
            # Limpiar componente específico
            namespace_map = {
                "embeddings": "query_embeddings",
                "search_results": "search_results", 
                "llm_responses": "llm_responses"
            }
            
            cleared = await cache_manager.clear_namespace(namespace_map[component])
            message = f"Cache del componente '{component}' limpiado"
        else:
            # Limpiar todo el cache RAG
            cleared = await rag_cache_service.invalidate_all_rag_caches()
            message = "Todo el cache RAG limpiado"
        
        return {
            "status": "success",
            "message": message,
            "entries_cleared": cleared,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error limpiando cache RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag-cache/invalidate-product")
async def invalidate_product_rag_cache(
    product_id: str = Query(..., description="ID del producto a invalidar")
):
    """Invalida caches RAG relacionados con un producto específico"""
    try:
        from app.services.rag_cache_service import rag_cache_service
        
        invalidated = await rag_cache_service.invalidate_product_caches(product_id)
        
        return {
            "status": "success",
            "message": f"Caches invalidados para producto {product_id}",
            "entries_invalidated": invalidated,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error invalidando cache de producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rag-cache/performance")
async def get_rag_cache_performance():
    """Análisis de performance del cache RAG"""
    try:
        from app.services.rag_cache_service import rag_cache_service
        
        stats = rag_cache_service.get_cache_stats()
        
        # Calcular métricas de performance
        total_requests = stats["overall"]["total_requests"]
        if total_requests == 0:
            return {
                "status": "no_data",
                "message": "No hay suficientes datos para análisis de performance RAG"
            }
        
        # Análisis de latencia estimada
        hit_rate = stats["overall"]["hit_rate"]
        
        # Estimaciones de latencia (ms)
        cache_hit_latency = 50      # 50ms para hit de cache
        cache_miss_latency = 1500   # 1.5s para miss completo (embedding + FAISS + LLM)
        
        avg_latency = (hit_rate/100 * cache_hit_latency) + ((100-hit_rate)/100 * cache_miss_latency)
        latency_improvement = ((cache_miss_latency - avg_latency) / cache_miss_latency) * 100
        
        # Análisis de throughput
        max_throughput_no_cache = 1    # 1 request/segundo sin cache
        max_throughput_with_cache = max_throughput_no_cache * (1500 / avg_latency)
        
        # Recomendaciones de optimización
        optimizations = []
        
        if hit_rate < 50:
            optimizations.append({
                "type": "hit_rate_improvement",
                "priority": "critical",
                "description": "Mejorar normalización de consultas",
                "impact": "Aumentar hit rate del cache"
            })
        
        if stats["by_component"]["embeddings"]["hit_rate"] < 70:
            optimizations.append({
                "type": "embedding_cache",
                "priority": "high",
                "description": "Aumentar TTL de embeddings",
                "impact": "Reducir recálculo de embeddings"
            })
        
        if stats["overall"]["similarity_matches"] < 10:
            optimizations.append({
                "type": "similarity_detection",
                "priority": "medium",
                "description": "Mejorar detección de consultas similares",
                "impact": "Aumentar hits por similaridad semántica"
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "hit_rate": hit_rate,
                "avg_latency_ms": round(avg_latency, 1),
                "latency_improvement_percent": round(latency_improvement, 1),
                "throughput_multiplier": round(max_throughput_with_cache, 1),
                "requests_per_second": round(max_throughput_with_cache, 1)
            },
            "latency_breakdown": {
                "cache_hit": f"{cache_hit_latency}ms",
                "cache_miss": f"{cache_miss_latency}ms",
                "average": f"{avg_latency:.1f}ms"
            },
            "cost_analysis": {
                "embedding_cost_reduction": f"{stats['by_component']['embeddings']['hit_rate']:.1f}%",
                "llm_cost_reduction": f"{stats['by_component']['llm_responses']['hit_rate']:.1f}%",
                "overall_cost_reduction": f"{min(80, hit_rate * 0.8):.1f}%"
            },
            "optimizations": optimizations,
            "health": {
                "status": "excellent" if hit_rate > 80 else
                         "good" if hit_rate > 60 else
                         "needs_attention",
                "cache_efficiency": "high" if hit_rate > 70 else "medium" if hit_rate > 40 else "low",
                "similarity_detection": "active" if stats["overall"]["similarity_matches"] > 0 else "inactive"
            }
        }
        
    except Exception as e:
        logger.error(f"Error analizando performance de cache RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# MÉTRICAS DE PERFORMANCE
# ===============================

@router.get("/performance")
async def get_performance_metrics():
    """Métricas de performance del sistema"""
    try:
        # Métricas de CPU y memoria
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Procesos más pesados
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 1.0:  # Solo procesos con >1% CPU
                        top_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Ordenar por CPU
            top_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            top_processes = top_processes[:5]  # Top 5
            
            system_metrics = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "status": "high" if cpu_percent > 80 else "medium" if cpu_percent > 50 else "low"
                },
                "memory": {
                    "percent": memory.percent,
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "status": "high" if memory.percent > 85 else "medium" if memory.percent > 70 else "low"
                },
                "disk": {
                    "percent": disk.percent,
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "status": "high" if disk.percent > 90 else "medium" if disk.percent > 80 else "low"
                },
                "top_processes": top_processes
            }
            
        except Exception as e:
            system_metrics = {"error": str(e)}
        
        # Métricas de la aplicación
        ws_stats = ws_manager.get_connection_stats()
        rl_stats = rate_limiter.get_stats()
        
        app_metrics = {
            "websockets": {
                "active_connections": ws_stats["current_connections"],
                "peak_connections": ws_stats["peak_connections"],
                "total_bytes_sent": ws_stats["total_bytes_sent"],
                "total_bytes_received": ws_stats["total_bytes_received"]
            },
            "rate_limiting": {
                "requests_checked": rl_stats["requests_checked"],
                "requests_blocked": rl_stats["requests_blocked"],
                "block_rate": rl_stats["block_rate"]
            }
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": system_metrics,
            "application": app_metrics,
            "alerts": _generate_performance_alerts(system_metrics, app_metrics)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _generate_performance_alerts(system_metrics: Dict, app_metrics: Dict) -> List[str]:
    """Genera alertas basadas en métricas de performance"""
    alerts = []
    
    try:
        # Alertas de sistema
        if system_metrics.get("cpu", {}).get("percent", 0) > 80:
            alerts.append("CPU usage is high (>80%)")
        
        if system_metrics.get("memory", {}).get("percent", 0) > 85:
            alerts.append("Memory usage is high (>85%)")
        
        if system_metrics.get("disk", {}).get("percent", 0) > 90:
            alerts.append("Disk usage is critical (>90%)")
        
        # Alertas de aplicación
        ws_connections = app_metrics.get("websockets", {}).get("active_connections", 0)
        if ws_connections > 400:  # 80% del límite de 500
            alerts.append("WebSocket connections approaching limit")
        
        block_rate = app_metrics.get("rate_limiting", {}).get("block_rate", 0)
        if block_rate > 15:
            alerts.append("High rate limiting block rate (>15%)")
    
    except Exception:
        pass
    
    return alerts

# ===============================
# MÉTRICAS EN TIEMPO REAL
# ===============================

@router.get("/realtime")
async def get_realtime_metrics():
    """Métricas en tiempo real para dashboards"""
    try:
        timestamp = datetime.now()
        
        # Métricas instantáneas
        metrics = {
            "timestamp": timestamp.isoformat(),
            "connections": ws_manager.get_connection_stats()["current_connections"],
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "requests_per_minute": _calculate_requests_per_minute(),
            "active_chats": len(ws_manager.connections_by_chat),
            "rate_limit_blocks": rate_limiter.get_stats()["requests_blocked"]
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas en tiempo real: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_requests_per_minute() -> int:
    """Calcula requests por minuto aproximado"""
    # Implementación simplificada basada en stats de rate limiter
    stats = rate_limiter.get_stats()
    # Esto es una aproximación - en producción usarías métricas más precisas
    return min(stats.get("requests_checked", 0), 1000)

# ===============================
# CONTROL DEL SISTEMA
# ===============================

@router.post("/system/gc")
async def trigger_garbage_collection():
    """Fuerza garbage collection (solo para debugging)"""
    try:
        import gc
        before = len(gc.get_objects())
        collected = gc.collect()
        after = len(gc.get_objects())
        
        return {
            "status": "success",
            "objects_before": before,
            "objects_after": after,
            "objects_collected": collected,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en garbage collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_system_alerts():
    """Obtiene todas las alertas del sistema"""
    try:
        alerts = []
        
        # Verificar métricas y generar alertas
        db_health = await check_database_health()
        if db_health.get("status") != "healthy":
            alerts.append({
                "level": "critical",
                "component": "database",
                "message": "Base de datos no está saludable",
                "timestamp": datetime.now().isoformat()
            })
        
        ws_stats = ws_manager.get_connection_stats()
        if ws_stats["current_connections"] > ws_stats["limits"]["max_global"] * 0.8:
            alerts.append({
                "level": "warning",
                "component": "websockets",
                "message": f"Conexiones WebSocket altas: {ws_stats['current_connections']}/{ws_stats['limits']['max_global']}",
                "timestamp": datetime.now().isoformat()
            })
        
        rl_stats = rate_limiter.get_stats()
        if rl_stats["block_rate"] > 10:
            alerts.append({
                "level": "warning",
                "component": "rate_limiting",
                "message": f"Alto rate de bloqueo: {rl_stats['block_rate']:.1f}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🧠 MONITOREO CACHE SEMÁNTICO
@router.get("/cache/semantic", response_model=Dict[str, Any])
async def get_semantic_cache_stats():
    """
    Obtiene estadísticas detalladas del cache semántico
    
    Incluye:
    - Performance de cache (hit rates, latencia)
    - Análisis semántico (similaridad, intenciones)
    - Métricas de embeddings
    - Configuración actual
    """
    try:
        # Importar dinámicamente para evitar errores si no está disponible
        try:
            from app.services.rag_semantic_cache import get_semantic_cache_stats
            semantic_stats = get_semantic_cache_stats()
            semantic_available = True
        except ImportError:
            semantic_stats = {"error": "Cache semántico no disponible"}
            semantic_available = False
        
        # Estadísticas del cache básico para comparación
        try:
            from app.services.rag_cache_service import rag_cache_service
            basic_stats = rag_cache_service.get_cache_stats()
        except Exception:
            basic_stats = {"error": "Cache básico no disponible"}
        
        # Estadísticas del cache manager
        try:
            from app.core.cache_manager import cache_manager
            manager_stats = cache_manager.get_stats()
        except Exception:
            manager_stats = {"error": "Cache manager no disponible"}
        
        return {
            "semantic_cache": {
                "available": semantic_available,
                "stats": semantic_stats
            },
            "basic_cache": basic_stats,
            "cache_manager": manager_stats,
            "comparison": _generate_cache_comparison(semantic_stats, basic_stats) if semantic_available else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de cache semántico: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/cache/semantic/performance", response_model=Dict[str, Any])
async def get_semantic_performance_metrics():
    """
    Métricas de performance específicas del cache semántico
    """
    try:
        from app.services.rag_semantic_cache import semantic_cache_service
        
        stats = semantic_cache_service.get_stats()
        
        # Calcular métricas derivadas
        total_queries = stats["cache_performance"]["total_queries"]
        exact_hits = stats["cache_performance"]["exact_hits"]
        semantic_hits = stats["cache_performance"]["semantic_hits"]
        cache_misses = stats["cache_performance"]["cache_misses"]
        
        # Métricas de eficiencia
        efficiency_metrics = {
            "overall_hit_rate": round(((exact_hits + semantic_hits) / max(total_queries, 1)) * 100, 2),
            "exact_hit_rate": round((exact_hits / max(total_queries, 1)) * 100, 2),
            "semantic_hit_rate": round((semantic_hits / max(total_queries, 1)) * 100, 2),
            "miss_rate": round((cache_misses / max(total_queries, 1)) * 100, 2),
            "semantic_intelligence_ratio": round((semantic_hits / max(exact_hits + semantic_hits, 1)) * 100, 2)
        }
        
        # Análisis de performance
        performance_analysis = {
            "avg_lookup_time": stats["performance_metrics"]["avg_cache_lookup_ms"],
            "avg_embedding_time": stats["performance_metrics"]["avg_embedding_generation_ms"],
            "avg_similarity_time": stats["performance_metrics"]["avg_similarity_calculation_ms"],
            "total_time_saved_estimate": _calculate_time_saved(stats),
            "cost_savings_estimate": _calculate_cost_savings(stats)
        }
        
        return {
            "efficiency_metrics": efficiency_metrics,
            "performance_analysis": performance_analysis,
            "raw_stats": stats,
            "recommendations": _generate_performance_recommendations(stats),
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Cache semántico no disponible")
    except Exception as e:
        logger.error(f"Error obteniendo métricas de performance: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/cache/semantic/strategy", response_model=Dict[str, Any])
async def change_semantic_cache_strategy(strategy: str):
    """
    Cambia la estrategia del cache semántico
    
    Estrategias disponibles:
    - exact_only: Solo cache exacto
    - semantic_smart: Cache semántico inteligente (recomendado)
    - aggressive: Cache agresivo (más hits, menos precisión)
    - conservative: Cache conservador (más precisión, menos hits)
    """
    try:
        from app.services.rag_semantic_cache import semantic_cache_service, CacheStrategy
        
        # Validar estrategia
        valid_strategies = [s.value for s in CacheStrategy]
        if strategy not in valid_strategies:
            raise HTTPException(
                status_code=400, 
                detail=f"Estrategia inválida. Opciones: {valid_strategies}"
            )
        
        # Cambiar estrategia
        old_strategy = semantic_cache_service.strategy.value
        semantic_cache_service.strategy = CacheStrategy(strategy)
        semantic_cache_service.similarity_thresholds = semantic_cache_service.SIMILARITY_THRESHOLDS[CacheStrategy(strategy)]
        
        # Resetear estadísticas para nueva medición
        semantic_cache_service.reset_stats()
        
        return {
            "message": f"Estrategia cambiada de '{old_strategy}' a '{strategy}'",
            "old_strategy": old_strategy,
            "new_strategy": strategy,
            "new_thresholds": {
                level.value: threshold 
                for level, threshold in semantic_cache_service.similarity_thresholds.items()
            },
            "stats_reset": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Cache semántico no disponible")
    except Exception as e:
        logger.error(f"Error cambiando estrategia: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.delete("/cache/semantic/clear", response_model=Dict[str, Any])
async def clear_semantic_cache():
    """
    Limpia el cache semántico (embeddings y búsquedas)
    """
    try:
        from app.core.cache_manager import cache_manager
        
        # Limpiar namespaces del cache semántico
        semantic_namespaces = [
            "semantic_embeddings",
            "semantic_searches",
            "similarity_matrix",
            "intent_classification"
        ]
        
        cleared_count = 0
        for namespace in semantic_namespaces:
            try:
                count = await cache_manager.clear_namespace(namespace)
                cleared_count += count
            except Exception as e:
                logger.warning(f"Error limpiando namespace {namespace}: {e}")
        
        # Resetear estadísticas
        try:
            from app.services.rag_semantic_cache import semantic_cache_service
            semantic_cache_service.reset_stats()
            semantic_cache_service._embedding_cache.clear()
            semantic_cache_service._similarity_cache.clear()
            stats_reset = True
        except ImportError:
            stats_reset = False
        
        return {
            "message": "Cache semántico limpiado exitosamente",
            "cleared_entries": cleared_count,
            "cleared_namespaces": semantic_namespaces,
            "stats_reset": stats_reset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error limpiando cache semántico: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Funciones auxiliares para análisis

def _generate_cache_comparison(semantic_stats: Dict, basic_stats: Dict) -> Dict[str, Any]:
    """Genera comparación entre cache semántico y básico"""
    try:
        semantic_hit_rate = semantic_stats.get("cache_performance", {}).get("hit_rate_percentage", 0)
        basic_hit_rate = basic_stats.get("cache_performance", {}).get("hit_rate_percentage", 0)
        
        return {
            "hit_rate_improvement": round(semantic_hit_rate - basic_hit_rate, 2),
            "semantic_advantage": semantic_hit_rate > basic_hit_rate,
            "semantic_hit_rate": semantic_hit_rate,
            "basic_hit_rate": basic_hit_rate,
            "intelligence_features": {
                "similarity_detection": semantic_stats.get("semantic_analysis", {}).get("similarity_calculations", 0) > 0,
                "intent_detection": semantic_stats.get("semantic_analysis", {}).get("intent_detections", 0) > 0,
                "advanced_normalization": True
            }
        }
    except Exception:
        return {"error": "No se pudo generar comparación"}

def _calculate_time_saved(stats: Dict) -> float:
    """Calcula tiempo estimado ahorrado por el cache"""
    try:
        hits = stats["cache_performance"]["exact_hits"] + stats["cache_performance"]["semantic_hits"]
        avg_lookup_time = stats["performance_metrics"]["avg_cache_lookup_ms"]
        avg_generation_time = stats["performance_metrics"]["avg_embedding_generation_ms"]
        
        # Tiempo ahorrado = hits * (tiempo_generación - tiempo_lookup)
        time_saved_per_hit = max(avg_generation_time - avg_lookup_time, 0)
        total_time_saved = hits * time_saved_per_hit
        
        return round(total_time_saved, 2)
    except Exception:
        return 0.0

def _calculate_cost_savings(stats: Dict) -> Dict[str, float]:
    """Calcula ahorros estimados de costos"""
    try:
        hits = stats["cache_performance"]["exact_hits"] + stats["cache_performance"]["semantic_hits"]
        
        # Estimaciones de costos (valores aproximados)
        cost_per_embedding = 0.0001  # USD por embedding
        cost_per_llm_call = 0.002    # USD por llamada LLM
        
        embedding_savings = hits * cost_per_embedding
        llm_savings = hits * cost_per_llm_call * 0.8  # 80% de hits evitan LLM
        
        return {
            "embedding_cost_savings_usd": round(embedding_savings, 4),
            "llm_cost_savings_usd": round(llm_savings, 4),
            "total_savings_usd": round(embedding_savings + llm_savings, 4)
        }
    except Exception:
        return {"error": "No se pudo calcular ahorros"}

def _generate_performance_recommendations(stats: Dict) -> List[str]:
    """Genera recomendaciones basadas en las estadísticas"""
    recommendations = []
    
    try:
        hit_rate = stats["cache_performance"]["hit_rate_percentage"]
        semantic_hit_rate = stats["cache_performance"]["semantic_hit_rate"]
        avg_similarity = stats["semantic_analysis"]["avg_similarity_score"]
        
        if hit_rate < 70:
            recommendations.append("Hit rate bajo (<70%). Considerar estrategia más agresiva.")
        
        if semantic_hit_rate < 20:
            recommendations.append("Pocos hits semánticos. Verificar normalización de consultas.")
        
        if avg_similarity < 0.8:
            recommendations.append("Similaridad promedio baja. Revisar umbrales de similaridad.")
        
        if stats["performance_metrics"]["avg_embedding_generation_ms"] > 500:
            recommendations.append("Generación de embeddings lenta. Considerar optimización del modelo.")
        
        if len(recommendations) == 0:
            recommendations.append("Performance óptima. Sistema funcionando correctamente.")
            
    except Exception:
        recommendations.append("Error generando recomendaciones.")
    
    return recommendations 