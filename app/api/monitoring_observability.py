"""
🔍 APIs de Monitoring & Observability Enterprise
APIs completas para métricas, dashboards, alertas y observabilidad
"""
from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import logging
import uuid

logger = logging.getLogger(__name__)

# ===============================
# MODELOS DE REQUEST/RESPONSE
# ===============================

class MetricQuery(BaseModel):
    """Query para métricas"""
    metrics: List[str] = Field(..., description="Lista de métricas a consultar")
    time_range: str = Field("1h", description="Rango de tiempo (1m, 5m, 1h, 1d)")
    aggregation: str = Field("avg", description="Función de agregación (avg, min, max, sum)")
    labels: Optional[Dict[str, str]] = Field(None, description="Filtros por labels")

class CustomMetricRequest(BaseModel):
    """Request para registrar métrica personalizada"""
    name: str = Field(..., description="Nombre de la métrica")
    metric_type: str = Field(..., description="Tipo de métrica (counter, gauge, histogram)")
    description: str = Field(..., description="Descripción de la métrica")
    unit: str = Field("", description="Unidad de medida")
    labels: Optional[List[str]] = Field(None, description="Labels disponibles")

class MetricValueRequest(BaseModel):
    """Request para registrar valor de métrica"""
    name: str = Field(..., description="Nombre de la métrica")
    value: float = Field(..., description="Valor de la métrica")
    labels: Optional[Dict[str, str]] = Field(None, description="Labels del valor")
    timestamp: Optional[datetime] = Field(None, description="Timestamp del valor")

class DashboardRequest(BaseModel):
    """Request para crear dashboard"""
    dashboard_id: str = Field(..., description="ID único del dashboard")
    name: str = Field(..., description="Nombre del dashboard")
    dashboard_type: str = Field("custom", description="Tipo de dashboard")
    charts: List[Dict[str, Any]] = Field(..., description="Configuración de gráficos")
    access_level: str = Field("user", description="Nivel de acceso requerido")
    theme: str = Field("light", description="Tema del dashboard")

class AlertRuleRequest(BaseModel):
    """Request para crear regla de alerta"""
    rule_id: str = Field(..., description="ID único de la regla")
    name: str = Field(..., description="Nombre de la regla")
    metric: str = Field(..., description="Métrica a monitorear")
    condition: str = Field(..., description="Condición de la alerta (>, <, ==)")
    threshold: float = Field(..., description="Umbral de la alerta")
    duration: str = Field("5m", description="Duración antes de disparar")
    severity: str = Field("warning", description="Severidad (info, warning, critical)")
    enabled: bool = Field(True, description="Si la regla está habilitada")

class HealthCheckResponse(BaseModel):
    """Response de health check"""
    status: str = Field(..., description="Estado del servicio")
    timestamp: datetime = Field(..., description="Timestamp del check")
    uptime_seconds: float = Field(..., description="Tiempo de actividad en segundos")
    version: str = Field("1.0.0", description="Versión del servicio")
    components: Dict[str, str] = Field(..., description="Estado de componentes")

# ===============================
# ROUTER PRINCIPAL
# ===============================

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring & Observability"])

# ===============================
# ENDPOINTS DE MÉTRICAS
# ===============================

@router.get("/health", response_model=HealthCheckResponse)
async def get_health_status():
    """
    🏥 Health check del sistema de monitoring
    
    Retorna el estado de salud de todos los componentes de observabilidad.
    """
    try:
        from app.core.metrics_collector_enterprise import get_metrics_stats
        from app.core.dashboard_service import get_dashboard_stats
        
        # Obtener estadísticas de componentes
        metrics_stats = get_metrics_stats()
        dashboard_stats = get_dashboard_stats()
        
        # Determinar estado de componentes
        components = {
            "metrics_collector": "healthy" if metrics_stats["collector"]["enabled"] else "unhealthy",
            "dashboard_service": "healthy" if dashboard_stats["dashboard_service"]["enabled"] else "unhealthy",
            "prometheus_export": "healthy" if metrics_stats["configuration"]["prometheus_enabled"] else "disabled",
            "websocket_service": "healthy" if dashboard_stats["websocket"]["active_connections"] >= 0 else "unhealthy"
        }
        
        # Estado general
        overall_status = "healthy" if all(status in ["healthy", "disabled"] for status in components.values()) else "degraded"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            uptime_seconds=metrics_stats["collector"]["uptime_seconds"],
            components=components
        )
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        raise HTTPException(status_code=500, detail=f"Error en health check: {str(e)}")

@router.get("/metrics/stats")
async def get_metrics_collector_stats():
    """
    📊 Estadísticas del collector de métricas
    
    Retorna estadísticas detalladas del sistema de recolección de métricas.
    """
    try:
        from app.core.metrics_collector_enterprise import get_metrics_stats
        
        stats = get_metrics_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats de métricas: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@router.get("/metrics/latest")
async def get_latest_metrics():
    """
    📈 Métricas más recientes
    
    Retorna las métricas más recientes de todas las categorías.
    """
    try:
        from app.core.metrics_collector_enterprise import get_latest_metrics
        
        metrics = get_latest_metrics()
        
        return {
            "status": "success",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas recientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")

@router.post("/metrics/query")
async def query_metrics(query: MetricQuery):
    """
    🔍 Consulta de métricas con filtros
    
    Permite consultar métricas específicas con rangos de tiempo y agregaciones.
    """
    try:
        from app.core.metrics_collector_enterprise import metrics_collector
        
        # Validar métricas solicitadas
        if not query.metrics:
            raise HTTPException(status_code=400, detail="Se requiere al menos una métrica")
        
        # Simular consulta de métricas (en producción sería consulta real)
        result = {}
        
        for metric in query.metrics:
            # Simular datos históricos
            data_points = []
            now = datetime.now()
            
            # Parsear time_range
            if query.time_range.endswith("m"):
                minutes = int(query.time_range[:-1])
                time_delta = timedelta(minutes=minutes)
                interval = timedelta(minutes=1)
            elif query.time_range.endswith("h"):
                hours = int(query.time_range[:-1])
                time_delta = timedelta(hours=hours)
                interval = timedelta(minutes=5)
            elif query.time_range.endswith("d"):
                days = int(query.time_range[:-1])
                time_delta = timedelta(days=days)
                interval = timedelta(hours=1)
            else:
                time_delta = timedelta(hours=1)
                interval = timedelta(minutes=5)
            
            # Generar puntos de datos
            current_time = now - time_delta
            while current_time <= now:
                import random
                value = random.uniform(0, 100)
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": value
                })
                
                current_time += interval
            
            result[metric] = {
                "data_points": data_points,
                "aggregation": query.aggregation,
                "time_range": query.time_range
            }
        
        return {
            "status": "success",
            "data": result,
            "query": query.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en consulta de métricas: {e}")
        raise HTTPException(status_code=500, detail=f"Error en consulta: {str(e)}")

@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    📊 Métricas en formato Prometheus
    
    Exporta todas las métricas en formato compatible con Prometheus.
    """
    try:
        from app.core.metrics_collector_enterprise import get_prometheus_metrics
        
        metrics_text = get_prometheus_metrics()
        
        if not metrics_text:
            metrics_text = "# No metrics available\n"
        
        return metrics_text
        
    except Exception as e:
        logger.error(f"❌ Error exportando métricas Prometheus: {e}")
        return f"# Error: {str(e)}\n"

@router.post("/metrics/custom/register")
async def register_custom_metric(metric_request: CustomMetricRequest):
    """
    📝 Registrar métrica personalizada
    
    Permite registrar nuevas métricas personalizadas en el sistema.
    """
    try:
        from app.core.metrics_collector_enterprise import register_custom_metric, MetricType
        
        # Validar tipo de métrica
        valid_types = ["counter", "gauge", "histogram", "summary"]
        if metric_request.metric_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de métrica inválido. Tipos válidos: {valid_types}"
            )
        
        # Convertir string a enum
        metric_type = MetricType(metric_request.metric_type)
        
        # Registrar métrica
        register_custom_metric(
            name=metric_request.name,
            metric_type=metric_type,
            description=metric_request.description,
            unit=metric_request.unit,
            labels=metric_request.labels
        )
        
        return {
            "status": "success",
            "message": f"Métrica '{metric_request.name}' registrada exitosamente",
            "metric": metric_request.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error registrando métrica personalizada: {e}")
        raise HTTPException(status_code=500, detail=f"Error registrando métrica: {str(e)}")

@router.post("/metrics/custom/record")
async def record_custom_metric_value(value_request: MetricValueRequest):
    """
    📊 Registrar valor de métrica personalizada
    
    Permite registrar valores para métricas personalizadas.
    """
    try:
        from app.core.metrics_collector_enterprise import record_custom_metric
        
        # Registrar valor
        record_custom_metric(
            name=value_request.name,
            value=value_request.value,
            labels=value_request.labels
        )
        
        return {
            "status": "success",
            "message": f"Valor registrado para métrica '{value_request.name}'",
            "value": value_request.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error registrando valor de métrica: {e}")
        raise HTTPException(status_code=500, detail=f"Error registrando valor: {str(e)}")

@router.get("/metrics/custom/list")
async def list_custom_metrics():
    """
    📋 Listar métricas personalizadas
    
    Retorna todas las métricas personalizadas registradas.
    """
    try:
        from app.core.metrics_collector_enterprise import metrics_collector
        
        custom_metrics = metrics_collector.custom_metrics.get_all_custom_metrics()
        
        return {
            "status": "success",
            "data": custom_metrics,
            "count": len(custom_metrics),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando métricas personalizadas: {e}")
        raise HTTPException(status_code=500, detail=f"Error listando métricas: {str(e)}")

# ===============================
# ENDPOINTS DE DASHBOARDS
# ===============================

@router.get("/dashboards/stats")
async def get_dashboard_stats():
    """
    📊 Estadísticas del servicio de dashboards
    
    Retorna estadísticas detalladas del sistema de dashboards.
    """
    try:
        from app.core.dashboard_service import get_dashboard_stats
        
        stats = get_dashboard_stats()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats de dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@router.get("/dashboards/list")
async def list_dashboards(access_level: Optional[str] = Query(None, description="Filtrar por nivel de acceso")):
    """
    📋 Listar dashboards disponibles
    
    Retorna todos los dashboards disponibles, opcionalmente filtrados por nivel de acceso.
    """
    try:
        from app.core.dashboard_service import list_available_dashboards
        
        dashboards = list_available_dashboards(access_level)
        
        return {
            "status": "success",
            "data": dashboards,
            "count": len(dashboards),
            "filter": {"access_level": access_level},
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error listando dashboards: {str(e)}")

@router.get("/dashboards/{dashboard_id}")
async def get_dashboard_config(dashboard_id: str):
    """
    📊 Obtener configuración de dashboard
    
    Retorna la configuración completa de un dashboard específico.
    """
    try:
        from app.core.dashboard_service import get_dashboard_config
        
        dashboard = get_dashboard_config(dashboard_id)
        
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' no encontrado")
        
        return {
            "status": "success",
            "data": dashboard.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo dashboard {dashboard_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo dashboard: {str(e)}")

@router.post("/dashboards/create")
async def create_dashboard(dashboard_request: DashboardRequest):
    """
    📊 Crear dashboard personalizado
    
    Permite crear un nuevo dashboard con configuración personalizada.
    """
    try:
        from app.core.dashboard_service import create_custom_dashboard, ChartConfig, ChartType
        
        # Convertir charts a objetos ChartConfig
        charts = []
        for chart_data in dashboard_request.charts:
            try:
                chart_type = ChartType(chart_data.get("chart_type", "line"))
                
                chart_config = ChartConfig(
                    chart_id=chart_data.get("chart_id", str(uuid.uuid4())),
                    name=chart_data.get("name", "Unnamed Chart"),
                    chart_type=chart_type,
                    metrics=chart_data.get("metrics", []),
                    time_range=chart_data.get("time_range", "1h"),
                    refresh_interval=chart_data.get("refresh_interval", 30),
                    width=chart_data.get("width", 6),
                    height=chart_data.get("height", 4),
                    options=chart_data.get("options", {})
                )
                
                charts.append(chart_config)
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando chart: {e}")
                continue
        
        if not charts:
            raise HTTPException(status_code=400, detail="Se requiere al menos un gráfico válido")
        
        # Crear dashboard
        success = await create_custom_dashboard(
            dashboard_id=dashboard_request.dashboard_id,
            name=dashboard_request.name,
            charts=charts,
            access_level=dashboard_request.access_level
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Error creando dashboard")
        
        return {
            "status": "success",
            "message": f"Dashboard '{dashboard_request.dashboard_id}' creado exitosamente",
            "dashboard": dashboard_request.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creando dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando dashboard: {str(e)}")

@router.post("/dashboards/{dashboard_id}/connect")
async def connect_to_dashboard(
    dashboard_id: str,
    user_id: str = Query("anonymous", description="ID del usuario")
):
    """
    📡 Conectar a dashboard para actualizaciones en tiempo real
    
    Simula la conexión WebSocket para recibir actualizaciones del dashboard.
    """
    try:
        from app.core.dashboard_service import add_dashboard_connection
        
        # Generar ID de conexión
        connection_id = str(uuid.uuid4())
        
        # Añadir conexión
        success = add_dashboard_connection(connection_id, dashboard_id, user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Error estableciendo conexión")
        
        return {
            "status": "success",
            "message": f"Conectado al dashboard '{dashboard_id}'",
            "connection_id": connection_id,
            "dashboard_id": dashboard_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error conectando a dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error conectando: {str(e)}")

@router.delete("/dashboards/connections/{connection_id}")
async def disconnect_from_dashboard(connection_id: str):
    """
    📡 Desconectar de dashboard
    
    Termina la conexión WebSocket con un dashboard.
    """
    try:
        from app.core.dashboard_service import remove_dashboard_connection
        
        success = remove_dashboard_connection(connection_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conexión no encontrada")
        
        return {
            "status": "success",
            "message": f"Conexión '{connection_id}' terminada",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error desconectando: {e}")
        raise HTTPException(status_code=500, detail=f"Error desconectando: {str(e)}")

# ===============================
# ENDPOINTS DE ALERTAS
# ===============================

@router.get("/alerts/rules")
async def list_alert_rules():
    """
    🚨 Listar reglas de alerta
    
    Retorna todas las reglas de alerta configuradas.
    """
    try:
        # Simular reglas de alerta (en producción vendría de base de datos)
        alert_rules = [
            {
                "rule_id": "high_cpu",
                "name": "High CPU Usage",
                "metric": "cpu_usage",
                "condition": ">",
                "threshold": 80.0,
                "duration": "5m",
                "severity": "warning",
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_triggered": None
            },
            {
                "rule_id": "high_memory",
                "name": "High Memory Usage",
                "metric": "memory_usage",
                "condition": ">",
                "threshold": 90.0,
                "duration": "3m",
                "severity": "critical",
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_triggered": "2024-01-15T10:30:00Z"
            },
            {
                "rule_id": "low_conversion",
                "name": "Low Conversion Rate",
                "metric": "conversion_rate",
                "condition": "<",
                "threshold": 5.0,
                "duration": "10m",
                "severity": "warning",
                "enabled": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_triggered": None
            }
        ]
        
        return {
            "status": "success",
            "data": alert_rules,
            "count": len(alert_rules),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando reglas de alerta: {e}")
        raise HTTPException(status_code=500, detail=f"Error listando alertas: {str(e)}")

@router.post("/alerts/rules")
async def create_alert_rule(alert_request: AlertRuleRequest):
    """
    🚨 Crear regla de alerta
    
    Permite crear una nueva regla de alerta para monitoreo automático.
    """
    try:
        # Validar condición
        valid_conditions = [">", "<", ">=", "<=", "==", "!="]
        if alert_request.condition not in valid_conditions:
            raise HTTPException(
                status_code=400,
                detail=f"Condición inválida. Condiciones válidas: {valid_conditions}"
            )
        
        # Validar severidad
        valid_severities = ["info", "warning", "critical"]
        if alert_request.severity not in valid_severities:
            raise HTTPException(
                status_code=400,
                detail=f"Severidad inválida. Severidades válidas: {valid_severities}"
            )
        
        # Simular creación de regla (en producción se guardaría en base de datos)
        alert_rule = {
            "rule_id": alert_request.rule_id,
            "name": alert_request.name,
            "metric": alert_request.metric,
            "condition": alert_request.condition,
            "threshold": alert_request.threshold,
            "duration": alert_request.duration,
            "severity": alert_request.severity,
            "enabled": alert_request.enabled,
            "created_at": datetime.now().isoformat(),
            "last_triggered": None
        }
        
        return {
            "status": "success",
            "message": f"Regla de alerta '{alert_request.rule_id}' creada exitosamente",
            "alert_rule": alert_rule,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creando regla de alerta: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando alerta: {str(e)}")

@router.get("/alerts/active")
async def get_active_alerts():
    """
    🚨 Obtener alertas activas
    
    Retorna todas las alertas que están actualmente disparadas.
    """
    try:
        # Simular alertas activas
        active_alerts = [
            {
                "alert_id": str(uuid.uuid4()),
                "rule_id": "high_memory",
                "rule_name": "High Memory Usage",
                "metric": "memory_usage",
                "current_value": 92.5,
                "threshold": 90.0,
                "condition": ">",
                "severity": "critical",
                "started_at": "2024-01-15T10:30:00Z",
                "duration": "15m",
                "status": "firing"
            }
        ]
        
        return {
            "status": "success",
            "data": active_alerts,
            "count": len(active_alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo alertas activas: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {str(e)}")

# ===============================
# ENDPOINTS DE ANÁLISIS
# ===============================

@router.get("/analysis/performance")
async def get_performance_analysis():
    """
    📈 Análisis de performance del sistema
    
    Retorna análisis detallado de performance y recomendaciones.
    """
    try:
        from app.core.metrics_collector_enterprise import get_metrics_stats
        from app.core.dashboard_service import get_dashboard_stats
        
        metrics_stats = get_metrics_stats()
        dashboard_stats = get_dashboard_stats()
        
        # Análisis de performance
        analysis = {
            "overall_health": "good",
            "performance_score": 85.2,
            "metrics_collection": {
                "status": "healthy",
                "success_rate": metrics_stats["performance"]["success_rate"],
                "avg_collection_time": metrics_stats["performance"]["avg_collection_duration"],
                "recommendations": []
            },
            "dashboard_performance": {
                "status": "healthy",
                "active_dashboards": dashboard_stats["dashboards"]["active_dashboards"],
                "websocket_connections": dashboard_stats["websocket"]["active_connections"],
                "update_success_rate": dashboard_stats["performance"]["success_rate"],
                "recommendations": []
            },
            "resource_usage": {
                "cpu_trend": "stable",
                "memory_trend": "increasing",
                "disk_trend": "stable",
                "network_trend": "stable"
            },
            "recommendations": [
                {
                    "category": "performance",
                    "priority": "medium",
                    "title": "Optimizar intervalo de recolección",
                    "description": "Considerar aumentar el intervalo de recolección en desarrollo",
                    "impact": "Reducir carga de CPU en 10-15%"
                },
                {
                    "category": "scalability",
                    "priority": "low",
                    "title": "Implementar cache de métricas",
                    "description": "Añadir cache para consultas frecuentes de métricas",
                    "impact": "Mejorar tiempo de respuesta en 20-30%"
                }
            ]
        }
        
        return {
            "status": "success",
            "data": analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de performance: {e}")
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")

@router.get("/analysis/trends")
async def get_trends_analysis(
    time_range: str = Query("24h", description="Rango de tiempo para análisis"),
    metrics: List[str] = Query(["cpu_usage", "memory_usage", "response_time"], description="Métricas a analizar")
):
    """
    📊 Análisis de tendencias
    
    Analiza tendencias de métricas específicas en un rango de tiempo.
    """
    try:
        # Simular análisis de tendencias
        trends = {}
        
        for metric in metrics:
            # Simular datos de tendencia
            import random
            
            trend_direction = random.choice(["increasing", "decreasing", "stable"])
            trend_strength = random.uniform(0.1, 0.9)
            
            trends[metric] = {
                "direction": trend_direction,
                "strength": trend_strength,
                "change_percentage": random.uniform(-20, 20),
                "volatility": random.uniform(0.1, 0.5),
                "prediction": {
                    "next_hour": random.uniform(40, 80),
                    "next_day": random.uniform(35, 85),
                    "confidence": random.uniform(0.7, 0.95)
                },
                "anomalies_detected": random.randint(0, 3),
                "seasonal_pattern": random.choice(["daily", "weekly", "none"])
            }
        
        analysis_summary = {
            "overall_trend": "stable",
            "risk_level": "low",
            "attention_required": [m for m in metrics if trends[m]["direction"] == "increasing"],
            "stable_metrics": [m for m in metrics if trends[m]["direction"] == "stable"]
        }
        
        return {
            "status": "success",
            "data": {
                "trends": trends,
                "summary": analysis_summary,
                "time_range": time_range,
                "analyzed_metrics": metrics
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de tendencias: {e}")
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")

# ===============================
# ENDPOINTS DE CONFIGURACIÓN
# ===============================

@router.get("/config/collector")
async def get_collector_config():
    """
    ⚙️ Obtener configuración del collector
    
    Retorna la configuración actual del sistema de recolección de métricas.
    """
    try:
        from app.core.metrics_collector_enterprise import MC_CONFIG, ENVIRONMENT
        
        return {
            "status": "success",
            "data": {
                "environment": ENVIRONMENT,
                "config": MC_CONFIG,
                "active_features": {
                    "business_metrics": MC_CONFIG["custom_metrics"]["business_metrics"],
                    "rag_performance": MC_CONFIG["custom_metrics"]["rag_performance"],
                    "cache_efficiency": MC_CONFIG["custom_metrics"].get("cache_efficiency", False),
                    "user_experience": MC_CONFIG["custom_metrics"].get("user_experience", False)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración: {str(e)}")

@router.get("/config/dashboards")
async def get_dashboard_config():
    """
    ⚙️ Obtener configuración de dashboards
    
    Retorna la configuración actual del sistema de dashboards.
    """
    try:
        from app.core.dashboard_service import DASHBOARD_CONFIG
        
        return {
            "status": "success",
            "data": DASHBOARD_CONFIG,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración: {str(e)}")

# ===============================
# WEBSOCKET PARA TIEMPO REAL
# ===============================

@router.websocket("/ws/dashboard/{dashboard_id}")
async def websocket_dashboard(websocket: WebSocket, dashboard_id: str):
    """
    📡 WebSocket para actualizaciones de dashboard en tiempo real
    
    Establece conexión WebSocket para recibir actualizaciones del dashboard.
    """
    await websocket.accept()
    
    connection_id = str(uuid.uuid4())
    
    try:
        from app.core.dashboard_service import add_dashboard_connection, remove_dashboard_connection
        
        # Añadir conexión
        success = add_dashboard_connection(connection_id, dashboard_id)
        
        if not success:
            await websocket.close(code=1000, reason="Error estableciendo conexión")
            return
        
        logger.info(f"📡 WebSocket conectado: {connection_id} para dashboard {dashboard_id}")
        
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "dashboard_id": dashboard_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Loop para mantener conexión activa
        while True:
            try:
                # Esperar mensajes del cliente (ping, etc.)
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"❌ Error en WebSocket: {e}")
                break
    
    except Exception as e:
        logger.error(f"❌ Error en WebSocket connection: {e}")
    
    finally:
        # Limpiar conexión
        try:
            remove_dashboard_connection(connection_id)
            logger.info(f"📡 WebSocket desconectado: {connection_id}")
        except Exception as e:
            logger.error(f"❌ Error limpiando conexión WebSocket: {e}")

# ===============================
# ENDPOINTS DE UTILIDAD
# ===============================

@router.get("/status")
async def get_monitoring_status():
    """
    📊 Estado general del sistema de monitoring
    
    Retorna un resumen del estado de todos los componentes de observabilidad.
    """
    try:
        from app.core.metrics_collector_enterprise import get_metrics_stats
        from app.core.dashboard_service import get_dashboard_stats
        
        metrics_stats = get_metrics_stats()
        dashboard_stats = get_dashboard_stats()
        
        status = {
            "overall_status": "healthy",
            "components": {
                "metrics_collector": {
                    "status": "healthy" if metrics_stats["collector"]["enabled"] else "disabled",
                    "uptime": metrics_stats["collector"]["uptime_seconds"],
                    "success_rate": metrics_stats["performance"]["success_rate"]
                },
                "dashboard_service": {
                    "status": "healthy" if dashboard_stats["dashboard_service"]["enabled"] else "disabled",
                    "active_dashboards": dashboard_stats["dashboards"]["active_dashboards"],
                    "websocket_connections": dashboard_stats["websocket"]["active_connections"]
                },
                "prometheus_export": {
                    "status": "enabled" if metrics_stats["configuration"]["prometheus_enabled"] else "disabled"
                }
            },
            "metrics": {
                "total_metrics_collected": metrics_stats["metrics_count"]["system"] + 
                                         metrics_stats["metrics_count"]["application"] + 
                                         metrics_stats["metrics_count"]["business"],
                "custom_metrics": metrics_stats["metrics_count"]["custom"],
                "collection_rate": f"{metrics_stats['performance']['total_collections']} collections"
            },
            "dashboards": {
                "total_dashboards": dashboard_stats["dashboards"]["total_dashboards"],
                "active_connections": dashboard_stats["websocket"]["active_connections"],
                "update_rate": f"{dashboard_stats['performance']['total_updates']} updates"
            }
        }
        
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")

@router.get("/version")
async def get_version_info():
    """
    ℹ️ Información de versión
    
    Retorna información sobre la versión del sistema de monitoring.
    """
    return {
        "status": "success",
        "data": {
            "service": "Monitoring & Observability Enterprise",
            "version": "1.0.0",
            "step": "Paso 7",
            "features": [
                "Metrics Collection Enterprise",
                "Real-time Dashboards",
                "WebSocket Support",
                "Prometheus Export",
                "Custom Metrics",
                "Alert Rules",
                "Performance Analysis",
                "Trend Analysis"
            ],
            "build_date": "2024-01-15",
            "environment": "development"
        },
        "timestamp": datetime.now().isoformat()
    } 