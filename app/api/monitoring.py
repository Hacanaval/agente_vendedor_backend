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