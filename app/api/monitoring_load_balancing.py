"""
⚖️ APIs de Monitoreo Load Balancing & Auto-scaling
Endpoints para monitorear y gestionar load balancing y auto-scaling
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/monitoring/load-balancing", tags=["Load Balancing Monitoring"])

# ===============================
# LOAD BALANCING MONITORING
# ===============================

@router.get("/health")
async def get_load_balancer_health():
    """
    🔍 Health check del load balancer
    Verifica estado general del load balancer
    """
    try:
        from app.core.load_balancer import load_balancer, get_load_balancer_stats
        
        stats = get_load_balancer_stats()
        
        # Determinar estado de salud
        healthy_instances = stats["load_balancer"]["healthy_instances"]
        total_instances = stats["load_balancer"]["total_instances"]
        
        health_status = "healthy"
        if healthy_instances == 0:
            health_status = "critical"
        elif healthy_instances < total_instances * 0.5:
            health_status = "degraded"
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "load_balancer": {
                "health_status": health_status,
                "algorithm": stats["load_balancer"]["algorithm"],
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "uptime_seconds": stats["load_balancer"]["uptime_seconds"]
            },
            "performance": {
                "success_rate": stats["performance"]["success_rate"],
                "requests_per_second": stats["performance"]["requests_per_second"],
                "total_requests": stats["performance"]["total_requests"]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo health del load balancer: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo health: {str(e)}")

@router.get("/stats")
async def get_load_balancer_stats():
    """
    📊 Estadísticas completas del load balancer
    Obtiene todas las métricas y estadísticas
    """
    try:
        from app.core.load_balancer import get_load_balancer_stats
        
        stats = get_load_balancer_stats()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats del load balancer: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo stats: {str(e)}")

@router.get("/instances")
async def get_instances_status():
    """
    🖥️ Estado de todas las instancias
    Lista todas las instancias registradas con su estado
    """
    try:
        from app.core.load_balancer import get_load_balancer_stats
        
        stats = get_load_balancer_stats()
        instances = stats.get("instances", {})
        
        # Enriquecer información de instancias
        enriched_instances = []
        for instance_id, instance_data in instances.items():
            enriched_instances.append({
                "instance_id": instance_id,
                "status": instance_data["status"],
                "weight": instance_data["weight"],
                "active_connections": instance_data["active_connections"],
                "total_requests": instance_data["total_requests"],
                "success_rate": instance_data["success_rate"],
                "avg_response_time": instance_data["avg_response_time"],
                "load_score": instance_data["load_score"],
                "circuit_breaker_state": instance_data["circuit_breaker_state"],
                "last_health_check": instance_data["last_health_check"]
            })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_instances": len(enriched_instances),
            "healthy_instances": len([i for i in enriched_instances if i["status"] == "healthy"]),
            "instances": enriched_instances
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de instancias: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo instancias: {str(e)}")

@router.get("/algorithms")
async def get_available_algorithms():
    """
    🔧 Algoritmos de load balancing disponibles
    Lista todos los algoritmos soportados
    """
    try:
        from app.core.load_balancer import LoadBalancingAlgorithm
        
        algorithms = []
        for algorithm in LoadBalancingAlgorithm:
            algorithms.append({
                "name": algorithm.value,
                "display_name": algorithm.value.replace("_", " ").title(),
                "description": _get_algorithm_description(algorithm.value)
            })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "algorithms": algorithms
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo algoritmos: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo algoritmos: {str(e)}")

def _get_algorithm_description(algorithm: str) -> str:
    """Obtiene descripción de un algoritmo"""
    descriptions = {
        "round_robin": "Distribuye requests de forma circular entre instancias",
        "weighted_round_robin": "Round robin considerando peso de cada instancia",
        "least_connections": "Envía requests a la instancia con menos conexiones activas",
        "weighted_least_connections": "Least connections considerando peso de instancia",
        "response_time": "Envía requests a la instancia con mejor tiempo de respuesta",
        "ip_hash": "Usa hash del IP cliente para sticky sessions",
        "random": "Selecciona instancia aleatoriamente",
        "weighted_random": "Selección aleatoria considerando pesos"
    }
    return descriptions.get(algorithm, "Algoritmo de load balancing")

# ===============================
# GESTIÓN DE LOAD BALANCER
# ===============================

@router.post("/algorithm/switch")
async def switch_load_balancing_algorithm(
    algorithm: str = Body(..., description="Nuevo algoritmo de load balancing")
):
    """
    🔄 Cambiar algoritmo de load balancing
    Cambia el algoritmo activo del load balancer
    """
    try:
        from app.core.load_balancer import load_balancer, LoadBalancingAlgorithm
        
        # Validar algoritmo
        try:
            new_algorithm = LoadBalancingAlgorithm(algorithm)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Algoritmo '{algorithm}' no válido. Algoritmos disponibles: {[a.value for a in LoadBalancingAlgorithm]}"
            )
        
        # Cambiar algoritmo
        success = await load_balancer.switch_algorithm(new_algorithm)
        
        if success:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "message": f"Algoritmo cambiado a: {algorithm}",
                "previous_algorithm": load_balancer.current_algorithm.value,
                "new_algorithm": algorithm
            }
        else:
            raise HTTPException(status_code=500, detail="Error cambiando algoritmo")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cambiando algoritmo: {e}")
        raise HTTPException(status_code=500, detail=f"Error cambiando algoritmo: {str(e)}")

@router.post("/instances/register")
async def register_instance(
    instance_id: str = Body(...),
    host: str = Body(...),
    port: int = Body(...),
    weight: float = Body(1.0),
    capabilities: List[str] = Body([])
):
    """
    ➕ Registrar nueva instancia
    Registra una nueva instancia en el load balancer
    """
    try:
        from app.core.load_balancer import register_service_instance
        
        success = await register_service_instance(
            instance_id=instance_id,
            host=host,
            port=port,
            weight=weight,
            capabilities=capabilities
        )
        
        if success:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "message": f"Instancia {instance_id} registrada exitosamente",
                "instance": {
                    "instance_id": instance_id,
                    "host": host,
                    "port": port,
                    "weight": weight,
                    "capabilities": capabilities
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Error registrando instancia")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error registrando instancia: {e}")
        raise HTTPException(status_code=500, detail=f"Error registrando instancia: {str(e)}")

@router.delete("/instances/{instance_id}")
async def deregister_instance(instance_id: str):
    """
    ➖ Desregistrar instancia
    Remueve una instancia del load balancer
    """
    try:
        from app.core.load_balancer import load_balancer
        
        success = await load_balancer.deregister_instance(instance_id)
        
        if success:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "message": f"Instancia {instance_id} desregistrada exitosamente"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Instancia {instance_id} no encontrada")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error desregistrando instancia: {e}")
        raise HTTPException(status_code=500, detail=f"Error desregistrando instancia: {str(e)}")

@router.put("/instances/{instance_id}/weight")
async def update_instance_weight(
    instance_id: str,
    weight: float = Body(..., description="Nuevo peso de la instancia")
):
    """
    ⚖️ Actualizar peso de instancia
    Cambia el peso de una instancia para load balancing
    """
    try:
        from app.core.load_balancer import load_balancer
        
        if weight < 0.1 or weight > 10.0:
            raise HTTPException(status_code=400, detail="Peso debe estar entre 0.1 y 10.0")
        
        success = await load_balancer.update_instance_weight(instance_id, weight)
        
        if success:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "message": f"Peso de instancia {instance_id} actualizado a {weight}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Instancia {instance_id} no encontrada")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error actualizando peso: {e}")
        raise HTTPException(status_code=500, detail=f"Error actualizando peso: {str(e)}")

# ===============================
# AUTO-SCALING MONITORING
# ===============================

@router.get("/auto-scaling/health")
async def get_auto_scaler_health():
    """
    📈 Health check del auto-scaler
    Verifica estado del servicio de auto-scaling
    """
    try:
        from app.core.auto_scaler import get_auto_scaler_stats
        
        stats = get_auto_scaler_stats()
        
        # Determinar estado de salud
        enabled = stats["auto_scaler"]["enabled"]
        current_instances = stats["auto_scaler"]["current_instances"]
        min_instances = stats["configuration"]["min_instances"]
        max_instances = stats["configuration"]["max_instances"]
        
        health_status = "healthy"
        if not enabled:
            health_status = "disabled"
        elif current_instances < min_instances:
            health_status = "under_provisioned"
        elif current_instances >= max_instances:
            health_status = "at_capacity"
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "auto_scaler": {
                "health_status": health_status,
                "enabled": enabled,
                "current_instances": current_instances,
                "target_instances": stats["auto_scaler"]["target_instances"],
                "uptime_seconds": stats["auto_scaler"]["uptime_seconds"]
            },
            "configuration": stats["configuration"],
            "recent_activity": stats["recent_activity"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo health del auto-scaler: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo health: {str(e)}")

@router.get("/auto-scaling/stats")
async def get_auto_scaling_stats():
    """
    📊 Estadísticas completas del auto-scaler
    Obtiene todas las métricas de auto-scaling
    """
    try:
        from app.core.auto_scaler import get_auto_scaler_stats
        
        stats = get_auto_scaler_stats()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats del auto-scaler: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo stats: {str(e)}")

@router.get("/auto-scaling/metrics")
async def get_current_scaling_metrics():
    """
    📏 Métricas actuales para auto-scaling
    Obtiene métricas en tiempo real del sistema
    """
    try:
        from app.core.auto_scaler import get_current_metrics
        
        metrics = await get_current_metrics()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "cpu_utilization": metrics.cpu_utilization,
                "memory_utilization": metrics.memory_utilization,
                "request_rate": metrics.request_rate,
                "response_time": metrics.response_time,
                "active_instances": metrics.active_instances,
                "healthy_instances": metrics.healthy_instances,
                "total_requests": metrics.total_requests,
                "error_rate": metrics.error_rate,
                "weighted_score": metrics.get_weighted_score()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")

@router.get("/auto-scaling/history")
async def get_scaling_history(
    limit: int = Query(10, description="Número de eventos a retornar")
):
    """
    📜 Historial de eventos de escalado
    Obtiene historial de eventos de auto-scaling
    """
    try:
        from app.core.auto_scaler import get_auto_scaler_stats
        
        stats = get_auto_scaler_stats()
        history = stats.get("scaling_history", [])
        
        # Limitar resultados
        limited_history = history[-limit:] if limit > 0 else history
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_events": len(history),
            "returned_events": len(limited_history),
            "events": limited_history
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")

# ===============================
# GESTIÓN DE AUTO-SCALING
# ===============================

@router.post("/auto-scaling/enable")
async def enable_auto_scaling():
    """
    ✅ Habilitar auto-scaling
    Activa el servicio de auto-scaling automático
    """
    try:
        from app.core.auto_scaler import enable_auto_scaling
        
        enable_auto_scaling()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message": "Auto-scaling habilitado exitosamente"
        }
        
    except Exception as e:
        logger.error(f"❌ Error habilitando auto-scaling: {e}")
        raise HTTPException(status_code=500, detail=f"Error habilitando auto-scaling: {str(e)}")

@router.post("/auto-scaling/disable")
async def disable_auto_scaling():
    """
    ⏸️ Deshabilitar auto-scaling
    Desactiva el servicio de auto-scaling automático
    """
    try:
        from app.core.auto_scaler import disable_auto_scaling
        
        disable_auto_scaling()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message": "Auto-scaling deshabilitado exitosamente"
        }
        
    except Exception as e:
        logger.error(f"❌ Error deshabilitando auto-scaling: {e}")
        raise HTTPException(status_code=500, detail=f"Error deshabilitando auto-scaling: {str(e)}")

@router.post("/auto-scaling/manual-scale")
async def manual_scale(
    target_instances: int = Body(..., description="Número objetivo de instancias"),
    reason: str = Body("manual", description="Razón del escalado manual")
):
    """
    🎛️ Escalado manual
    Ejecuta escalado manual a un número específico de instancias
    """
    try:
        from app.core.auto_scaler import manual_scale_instances, get_auto_scaler_stats
        
        # Validar rango
        stats = get_auto_scaler_stats()
        min_instances = stats["configuration"]["min_instances"]
        max_instances = stats["configuration"]["max_instances"]
        
        if target_instances < min_instances or target_instances > max_instances:
            raise HTTPException(
                status_code=400,
                detail=f"Target instances debe estar entre {min_instances} y {max_instances}"
            )
        
        success = await manual_scale_instances(target_instances, reason)
        
        if success:
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "message": f"Escalado manual iniciado a {target_instances} instancias",
                "target_instances": target_instances,
                "reason": reason
            }
        else:
            raise HTTPException(status_code=500, detail="Error ejecutando escalado manual")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en escalado manual: {e}")
        raise HTTPException(status_code=500, detail=f"Error en escalado manual: {str(e)}")

# ===============================
# ANÁLISIS Y RECOMENDACIONES
# ===============================

@router.get("/analysis/performance")
async def get_performance_analysis():
    """
    🔍 Análisis de performance
    Analiza performance del load balancing y auto-scaling
    """
    try:
        from app.core.load_balancer import get_load_balancer_stats
        from app.core.auto_scaler import get_auto_scaler_stats, get_current_metrics
        
        lb_stats = get_load_balancer_stats()
        as_stats = get_auto_scaler_stats()
        current_metrics = await get_current_metrics()
        
        # Análisis de load balancing
        lb_analysis = {
            "distribution_efficiency": _calculate_distribution_efficiency(lb_stats),
            "instance_utilization": _calculate_instance_utilization(lb_stats),
            "circuit_breaker_health": _analyze_circuit_breakers(lb_stats)
        }
        
        # Análisis de auto-scaling
        as_analysis = {
            "scaling_efficiency": _calculate_scaling_efficiency(as_stats),
            "resource_optimization": _analyze_resource_optimization(current_metrics),
            "cost_efficiency": _calculate_cost_efficiency(as_stats, current_metrics)
        }
        
        # Recomendaciones
        recommendations = _generate_recommendations(lb_stats, as_stats, current_metrics)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "load_balancing": lb_analysis,
                "auto_scaling": as_analysis
            },
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de performance: {e}")
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")

def _calculate_distribution_efficiency(lb_stats: Dict) -> Dict[str, Any]:
    """Calcula eficiencia de distribución de carga"""
    try:
        instances = lb_stats.get("instances", {})
        if not instances:
            return {"efficiency": 0.0, "variance": 0.0, "status": "no_instances"}
        
        # Calcular varianza en distribución de requests
        request_counts = [inst.get("total_requests", 0) for inst in instances.values()]
        if not request_counts or max(request_counts) == 0:
            return {"efficiency": 100.0, "variance": 0.0, "status": "no_traffic"}
        
        mean_requests = sum(request_counts) / len(request_counts)
        variance = sum((x - mean_requests) ** 2 for x in request_counts) / len(request_counts)
        coefficient_of_variation = (variance ** 0.5) / mean_requests if mean_requests > 0 else 0
        
        # Eficiencia inversa al coeficiente de variación
        efficiency = max(0, 100 - (coefficient_of_variation * 100))
        
        return {
            "efficiency": round(efficiency, 2),
            "variance": round(variance, 2),
            "coefficient_of_variation": round(coefficient_of_variation, 3),
            "status": "good" if efficiency > 80 else "needs_improvement"
        }
        
    except Exception as e:
        logger.error(f"Error calculando eficiencia de distribución: {e}")
        return {"efficiency": 0.0, "variance": 0.0, "status": "error"}

def _calculate_instance_utilization(lb_stats: Dict) -> Dict[str, Any]:
    """Calcula utilización de instancias"""
    try:
        instances = lb_stats.get("instances", {})
        if not instances:
            return {"avg_utilization": 0.0, "status": "no_instances"}
        
        # Calcular utilización promedio basada en load_score
        load_scores = [inst.get("load_score", 0) for inst in instances.values()]
        avg_load = sum(load_scores) / len(load_scores) if load_scores else 0
        
        # Normalizar a porcentaje (asumiendo que load_score > 1 es alta utilización)
        utilization_percent = min(avg_load * 50, 100)  # Escalar aproximadamente
        
        status = "optimal"
        if utilization_percent < 30:
            status = "under_utilized"
        elif utilization_percent > 80:
            status = "over_utilized"
        
        return {
            "avg_utilization": round(utilization_percent, 2),
            "avg_load_score": round(avg_load, 3),
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error calculando utilización de instancias: {e}")
        return {"avg_utilization": 0.0, "status": "error"}

def _analyze_circuit_breakers(lb_stats: Dict) -> Dict[str, Any]:
    """Analiza estado de circuit breakers"""
    try:
        instances = lb_stats.get("instances", {})
        if not instances:
            return {"healthy": 0, "open": 0, "half_open": 0, "status": "no_instances"}
        
        cb_states = {}
        for inst in instances.values():
            state = inst.get("circuit_breaker_state", "unknown")
            cb_states[state] = cb_states.get(state, 0) + 1
        
        total = len(instances)
        healthy_ratio = cb_states.get("closed", 0) / total if total > 0 else 0
        
        status = "healthy"
        if healthy_ratio < 0.5:
            status = "critical"
        elif healthy_ratio < 0.8:
            status = "degraded"
        
        return {
            "healthy": cb_states.get("closed", 0),
            "open": cb_states.get("open", 0),
            "half_open": cb_states.get("half_open", 0),
            "healthy_ratio": round(healthy_ratio, 2),
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error analizando circuit breakers: {e}")
        return {"healthy": 0, "open": 0, "half_open": 0, "status": "error"}

def _calculate_scaling_efficiency(as_stats: Dict) -> Dict[str, Any]:
    """Calcula eficiencia de auto-scaling"""
    try:
        performance = as_stats.get("performance", {})
        total_events = performance.get("scale_up_events", 0) + performance.get("scale_down_events", 0)
        failures = performance.get("scaling_failures", 0)
        
        if total_events == 0:
            return {"efficiency": 100.0, "status": "no_scaling_events"}
        
        success_rate = ((total_events - failures) / total_events) * 100
        
        status = "excellent"
        if success_rate < 80:
            status = "needs_improvement"
        elif success_rate < 95:
            status = "good"
        
        return {
            "efficiency": round(success_rate, 2),
            "total_events": total_events,
            "failures": failures,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error calculando eficiencia de scaling: {e}")
        return {"efficiency": 0.0, "status": "error"}

def _analyze_resource_optimization(metrics) -> Dict[str, Any]:
    """Analiza optimización de recursos"""
    try:
        cpu = metrics.cpu_utilization
        memory = metrics.memory_utilization
        
        # Calcular score de optimización
        target_cpu = 70  # Target ideal
        target_memory = 80
        
        cpu_efficiency = 100 - abs(cpu - target_cpu)
        memory_efficiency = 100 - abs(memory - target_memory)
        
        overall_efficiency = (cpu_efficiency + memory_efficiency) / 2
        
        status = "optimal"
        if overall_efficiency < 60:
            status = "poor"
        elif overall_efficiency < 80:
            status = "good"
        
        return {
            "cpu_utilization": cpu,
            "memory_utilization": memory,
            "cpu_efficiency": round(max(0, cpu_efficiency), 2),
            "memory_efficiency": round(max(0, memory_efficiency), 2),
            "overall_efficiency": round(max(0, overall_efficiency), 2),
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error analizando optimización de recursos: {e}")
        return {"overall_efficiency": 0.0, "status": "error"}

def _calculate_cost_efficiency(as_stats: Dict, metrics) -> Dict[str, Any]:
    """Calcula eficiencia de costos"""
    try:
        current_instances = metrics.active_instances
        min_instances = as_stats["configuration"]["min_instances"]
        max_instances = as_stats["configuration"]["max_instances"]
        
        # Calcular utilización de capacidad
        capacity_utilization = (current_instances - min_instances) / (max_instances - min_instances) if max_instances > min_instances else 0
        
        # Estimar eficiencia de costos basada en utilización de recursos vs instancias
        resource_utilization = (metrics.cpu_utilization + metrics.memory_utilization) / 2
        cost_efficiency = (resource_utilization / 100) * 100  # Simplificado
        
        status = "efficient"
        if cost_efficiency < 50:
            status = "wasteful"
        elif cost_efficiency < 70:
            status = "moderate"
        
        return {
            "current_instances": current_instances,
            "capacity_utilization": round(capacity_utilization * 100, 2),
            "cost_efficiency": round(cost_efficiency, 2),
            "estimated_savings": round(max(0, 100 - cost_efficiency), 2),
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error calculando eficiencia de costos: {e}")
        return {"cost_efficiency": 0.0, "status": "error"}

def _generate_recommendations(lb_stats: Dict, as_stats: Dict, metrics) -> List[Dict[str, Any]]:
    """Genera recomendaciones basadas en análisis"""
    recommendations = []
    
    try:
        # Recomendaciones de load balancing
        instances = lb_stats.get("instances", {})
        if len(instances) < 2:
            recommendations.append({
                "type": "load_balancing",
                "priority": "high",
                "title": "Agregar más instancias",
                "description": "Se recomienda tener al menos 2 instancias para alta disponibilidad",
                "action": "register_instances"
            })
        
        # Recomendaciones de auto-scaling
        if metrics.cpu_utilization > 90:
            recommendations.append({
                "type": "auto_scaling",
                "priority": "high",
                "title": "CPU utilization muy alta",
                "description": f"CPU al {metrics.cpu_utilization}%. Considerar escalado inmediato",
                "action": "scale_up"
            })
        
        if metrics.memory_utilization > 95:
            recommendations.append({
                "type": "auto_scaling",
                "priority": "critical",
                "title": "Memoria casi agotada",
                "description": f"Memoria al {metrics.memory_utilization}%. Escalado urgente requerido",
                "action": "scale_up_urgent"
            })
        
        # Recomendaciones de optimización
        if metrics.cpu_utilization < 20 and metrics.active_instances > as_stats["configuration"]["min_instances"]:
            recommendations.append({
                "type": "optimization",
                "priority": "medium",
                "title": "Recursos subutilizados",
                "description": f"CPU al {metrics.cpu_utilization}%. Considerar reducir instancias",
                "action": "scale_down"
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generando recomendaciones: {e}")
        return []

@router.get("/dashboard")
async def get_dashboard_data():
    """
    📊 Datos para dashboard
    Obtiene datos consolidados para dashboard de monitoreo
    """
    try:
        from app.core.load_balancer import get_load_balancer_stats
        from app.core.auto_scaler import get_auto_scaler_stats, get_current_metrics
        
        lb_stats = get_load_balancer_stats()
        as_stats = get_auto_scaler_stats()
        current_metrics = await get_current_metrics()
        
        # Datos consolidados para dashboard
        dashboard_data = {
            "overview": {
                "total_instances": lb_stats["load_balancer"]["total_instances"],
                "healthy_instances": lb_stats["load_balancer"]["healthy_instances"],
                "current_algorithm": lb_stats["load_balancer"]["algorithm"],
                "auto_scaling_enabled": as_stats["auto_scaler"]["enabled"],
                "requests_per_second": lb_stats["performance"]["requests_per_second"],
                "success_rate": lb_stats["performance"]["success_rate"]
            },
            "metrics": {
                "cpu_utilization": current_metrics.cpu_utilization,
                "memory_utilization": current_metrics.memory_utilization,
                "request_rate": current_metrics.request_rate,
                "response_time": current_metrics.response_time,
                "error_rate": current_metrics.error_rate
            },
            "scaling": {
                "current_instances": as_stats["auto_scaler"]["current_instances"],
                "target_instances": as_stats["auto_scaler"]["target_instances"],
                "min_instances": as_stats["configuration"]["min_instances"],
                "max_instances": as_stats["configuration"]["max_instances"],
                "recent_events": len([e for e in as_stats.get("scaling_history", []) if 
                                    (datetime.now() - datetime.fromisoformat(e["timestamp"])).total_seconds() < 3600])
            },
            "alerts": _generate_alerts(lb_stats, as_stats, current_metrics)
        }
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo datos de dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo dashboard: {str(e)}")

def _generate_alerts(lb_stats: Dict, as_stats: Dict, metrics) -> List[Dict[str, Any]]:
    """Genera alertas para el dashboard"""
    alerts = []
    
    try:
        # Alertas críticas
        if metrics.cpu_utilization > 95:
            alerts.append({
                "level": "critical",
                "message": f"CPU crítico: {metrics.cpu_utilization}%",
                "timestamp": datetime.now().isoformat()
            })
        
        if metrics.memory_utilization > 98:
            alerts.append({
                "level": "critical",
                "message": f"Memoria crítica: {metrics.memory_utilization}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alertas de warning
        if lb_stats["load_balancer"]["healthy_instances"] == 0:
            alerts.append({
                "level": "critical",
                "message": "No hay instancias saludables disponibles",
                "timestamp": datetime.now().isoformat()
            })
        
        if metrics.error_rate > 5:
            alerts.append({
                "level": "warning",
                "message": f"Tasa de error alta: {metrics.error_rate}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error generando alertas: {e}")
        return [] 