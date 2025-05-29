"""
📊 Dashboard Service Enterprise
Servicio de dashboards en tiempo real con WebSocket y visualización avanzada
"""
import asyncio
import json
import time
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN DE DASHBOARDS
# ===============================

DASHBOARD_CONFIG = {
    "real_time": {
        "update_interval": 5,  # segundos
        "websocket_enabled": True,
        "auto_refresh": True,
        "max_connections": 100
    },
    "dashboards": {
        "executive": {
            "metrics": ["revenue", "conversion", "user_satisfaction"],
            "refresh": 30,
            "alerts": True,
            "access_level": "executive"
        },
        "operations": {
            "metrics": ["system_health", "performance", "errors"],
            "refresh": 10,
            "alerts": True,
            "access_level": "operations"
        },
        "development": {
            "metrics": ["api_performance", "cache_hits", "response_times"],
            "refresh": 5,
            "alerts": False,
            "access_level": "developer"
        }
    },
    "visualization": {
        "charts": ["line", "bar", "gauge", "heatmap", "table", "pie"],
        "themes": ["light", "dark", "auto"],
        "responsive": True,
        "animations": True
    }
}

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class ChartType(Enum):
    """Tipos de gráficos"""
    LINE = "line"
    BAR = "bar"
    GAUGE = "gauge"
    PIE = "pie"
    HEATMAP = "heatmap"
    TABLE = "table"
    BIG_NUMBER = "big_number"
    STATUS_GRID = "status_grid"

class DashboardType(Enum):
    """Tipos de dashboard"""
    EXECUTIVE = "executive"
    OPERATIONS = "operations"
    DEVELOPMENT = "development"
    CUSTOM = "custom"

class UpdateFrequency(Enum):
    """Frecuencias de actualización"""
    REAL_TIME = 5
    FAST = 10
    MEDIUM = 30
    SLOW = 60

@dataclass
class ChartConfig:
    """Configuración de gráfico"""
    chart_id: str
    name: str
    chart_type: ChartType
    metrics: List[str]
    time_range: str = "1h"
    refresh_interval: int = 30
    width: int = 6  # Grid width (1-12)
    height: int = 4  # Grid height
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "chart_id": self.chart_id,
            "name": self.name,
            "chart_type": self.chart_type.value,
            "metrics": self.metrics,
            "time_range": self.time_range,
            "refresh_interval": self.refresh_interval,
            "width": self.width,
            "height": self.height,
            "options": self.options
        }

@dataclass
class DashboardConfig:
    """Configuración de dashboard"""
    dashboard_id: str
    name: str
    dashboard_type: DashboardType
    charts: List[ChartConfig]
    layout: Dict[str, Any] = field(default_factory=dict)
    theme: str = "light"
    auto_refresh: bool = True
    access_level: str = "user"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "dashboard_type": self.dashboard_type.value,
            "charts": [chart.to_dict() for chart in self.charts],
            "layout": self.layout,
            "theme": self.theme,
            "auto_refresh": self.auto_refresh,
            "access_level": self.access_level,
            "created_at": self.created_at.isoformat()
        }

@dataclass
class ChartData:
    """Datos de gráfico"""
    chart_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebSocketConnection:
    """Conexión WebSocket"""
    connection_id: str
    dashboard_id: str
    user_id: str = "anonymous"
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    subscriptions: List[str] = field(default_factory=list)

# ===============================
# WEBSOCKET MANAGER
# ===============================

class WebSocketManager:
    """Gestor de conexiones WebSocket"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.dashboard_subscribers: Dict[str, List[str]] = defaultdict(list)
        self.max_connections = DASHBOARD_CONFIG["real_time"]["max_connections"]
        
        # Estadísticas
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "start_time": datetime.now()
        }
    
    def add_connection(
        self, 
        connection_id: str, 
        dashboard_id: str, 
        user_id: str = "anonymous"
    ) -> bool:
        """Añade una nueva conexión"""
        try:
            if len(self.connections) >= self.max_connections:
                logger.warning(f"Máximo de conexiones alcanzado: {self.max_connections}")
                return False
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                dashboard_id=dashboard_id,
                user_id=user_id
            )
            
            self.connections[connection_id] = connection
            self.dashboard_subscribers[dashboard_id].append(connection_id)
            
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.connections)
            
            logger.info(f"📡 Nueva conexión WebSocket: {connection_id} para dashboard {dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error añadiendo conexión: {e}")
            return False
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remueve una conexión"""
        try:
            if connection_id not in self.connections:
                return False
            
            connection = self.connections[connection_id]
            dashboard_id = connection.dashboard_id
            
            # Remover de suscripciones
            if connection_id in self.dashboard_subscribers[dashboard_id]:
                self.dashboard_subscribers[dashboard_id].remove(connection_id)
            
            # Remover conexión
            del self.connections[connection_id]
            
            self.stats["active_connections"] = len(self.connections)
            
            logger.info(f"📡 Conexión WebSocket removida: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removiendo conexión: {e}")
            return False
    
    def get_dashboard_connections(self, dashboard_id: str) -> List[str]:
        """Obtiene conexiones para un dashboard"""
        return self.dashboard_subscribers.get(dashboard_id, [])
    
    def update_ping(self, connection_id: str):
        """Actualiza último ping de conexión"""
        if connection_id in self.connections:
            self.connections[connection_id].last_ping = datetime.now()
    
    def cleanup_stale_connections(self, timeout_minutes: int = 5):
        """Limpia conexiones inactivas"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        stale_connections = []
        
        for connection_id, connection in self.connections.items():
            if connection.last_ping < cutoff_time:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            self.remove_connection(connection_id)
        
        if stale_connections:
            logger.info(f"🧹 Limpiadas {len(stale_connections)} conexiones inactivas")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de WebSocket"""
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            "websocket": {
                "active_connections": self.stats["active_connections"],
                "total_connections": self.stats["total_connections"],
                "max_connections": self.max_connections,
                "uptime_seconds": uptime.total_seconds()
            },
            "messaging": {
                "messages_sent": self.stats["messages_sent"],
                "messages_failed": self.stats["messages_failed"],
                "success_rate": (
                    (self.stats["messages_sent"] / max(self.stats["messages_sent"] + self.stats["messages_failed"], 1)) * 100
                )
            },
            "dashboards": {
                "active_dashboards": len([d for d in self.dashboard_subscribers.values() if d]),
                "total_subscriptions": sum(len(subs) for subs in self.dashboard_subscribers.values())
            }
        }

# ===============================
# CHART GENERATOR
# ===============================

class ChartGenerator:
    """Generador de gráficos dinámicos"""
    
    def __init__(self):
        self.chart_cache = {}
        self.cache_ttl = 30  # segundos
    
    async def generate_chart(self, chart_config: ChartConfig) -> Dict[str, Any]:
        """Genera datos de gráfico según configuración"""
        try:
            # Verificar cache
            cache_key = f"{chart_config.chart_id}_{chart_config.time_range}"
            if cache_key in self.chart_cache:
                cached_data, timestamp = self.chart_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Generar datos según tipo de gráfico
            chart_data = await self._generate_chart_data(chart_config)
            
            # Cachear resultado
            self.chart_cache[cache_key] = (chart_data, datetime.now())
            
            return chart_data
            
        except Exception as e:
            logger.error(f"❌ Error generando gráfico {chart_config.chart_id}: {e}")
            return {"error": str(e)}
    
    async def _generate_chart_data(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera datos específicos según tipo de gráfico"""
        if config.chart_type == ChartType.LINE:
            return await self._generate_line_chart(config)
        elif config.chart_type == ChartType.BAR:
            return await self._generate_bar_chart(config)
        elif config.chart_type == ChartType.GAUGE:
            return await self._generate_gauge_chart(config)
        elif config.chart_type == ChartType.PIE:
            return await self._generate_pie_chart(config)
        elif config.chart_type == ChartType.BIG_NUMBER:
            return await self._generate_big_number(config)
        elif config.chart_type == ChartType.TABLE:
            return await self._generate_table(config)
        elif config.chart_type == ChartType.STATUS_GRID:
            return await self._generate_status_grid(config)
        else:
            return {"error": f"Tipo de gráfico no soportado: {config.chart_type}"}
    
    async def _generate_line_chart(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera gráfico de líneas"""
        try:
            # Obtener datos de métricas
            metrics_data = await self._get_metrics_data(config.metrics, config.time_range)
            
            # Formatear para gráfico de líneas
            series = []
            for metric_name, data_points in metrics_data.items():
                series.append({
                    "name": metric_name,
                    "data": [{"x": point["timestamp"], "y": point["value"]} for point in data_points]
                })
            
            return {
                "type": "line",
                "series": series,
                "options": {
                    "chart": {"type": "line", "height": 350},
                    "xaxis": {"type": "datetime"},
                    "yaxis": {"title": {"text": "Value"}},
                    "title": {"text": config.name},
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando line chart: {e}")
            return {"error": str(e)}
    
    async def _generate_bar_chart(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera gráfico de barras"""
        try:
            # Obtener datos agregados
            metrics_data = await self._get_aggregated_metrics(config.metrics, config.time_range)
            
            categories = list(metrics_data.keys())
            values = list(metrics_data.values())
            
            return {
                "type": "bar",
                "series": [{
                    "name": config.name,
                    "data": values
                }],
                "options": {
                    "chart": {"type": "bar", "height": 350},
                    "xaxis": {"categories": categories},
                    "title": {"text": config.name},
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando bar chart: {e}")
            return {"error": str(e)}
    
    async def _generate_gauge_chart(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera gráfico gauge"""
        try:
            # Obtener valor actual de la métrica
            current_value = await self._get_current_metric_value(config.metrics[0])
            
            # Configuración del gauge
            max_value = config.options.get("max", 100)
            target_value = config.options.get("target", max_value * 0.8)
            
            return {
                "type": "gauge",
                "value": current_value,
                "options": {
                    "chart": {"type": "radialBar", "height": 350},
                    "plotOptions": {
                        "radialBar": {
                            "startAngle": -90,
                            "endAngle": 90,
                            "hollow": {"size": "60%"},
                            "dataLabels": {
                                "value": {"fontSize": "24px"},
                                "total": {"show": True, "label": config.name}
                            }
                        }
                    },
                    "labels": [config.name],
                    "max": max_value,
                    "target": target_value,
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando gauge chart: {e}")
            return {"error": str(e)}
    
    async def _generate_pie_chart(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera gráfico de pie"""
        try:
            # Obtener datos para pie chart
            metrics_data = await self._get_aggregated_metrics(config.metrics, config.time_range)
            
            labels = list(metrics_data.keys())
            values = list(metrics_data.values())
            
            return {
                "type": "pie",
                "series": values,
                "options": {
                    "chart": {"type": "pie", "height": 350},
                    "labels": labels,
                    "title": {"text": config.name},
                    "legend": {"position": "bottom"},
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando pie chart: {e}")
            return {"error": str(e)}
    
    async def _generate_big_number(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera big number display"""
        try:
            current_value = await self._get_current_metric_value(config.metrics[0])
            previous_value = await self._get_previous_metric_value(config.metrics[0], "1h")
            
            # Calcular cambio
            change = 0.0
            if previous_value and previous_value != 0:
                change = ((current_value - previous_value) / previous_value) * 100
            
            return {
                "type": "big_number",
                "value": current_value,
                "change": change,
                "options": {
                    "title": config.name,
                    "format": config.options.get("format", "number"),
                    "unit": config.options.get("unit", ""),
                    "decimals": config.options.get("decimals", 2),
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando big number: {e}")
            return {"error": str(e)}
    
    async def _generate_table(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera tabla de datos"""
        try:
            # Obtener datos tabulares
            table_data = await self._get_table_data(config.metrics)
            
            return {
                "type": "table",
                "data": table_data,
                "options": {
                    "title": config.name,
                    "columns": config.options.get("columns", []),
                    "sortable": config.options.get("sortable", True),
                    "searchable": config.options.get("searchable", True),
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando table: {e}")
            return {"error": str(e)}
    
    async def _generate_status_grid(self, config: ChartConfig) -> Dict[str, Any]:
        """Genera grid de estado de servicios"""
        try:
            # Obtener estado de servicios
            services_status = await self._get_services_status(config.metrics)
            
            return {
                "type": "status_grid",
                "services": services_status,
                "options": {
                    "title": config.name,
                    "grid_columns": config.options.get("grid_columns", 4),
                    **config.options
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando status grid: {e}")
            return {"error": str(e)}
    
    # ===============================
    # HELPERS PARA DATOS
    # ===============================
    
    async def _get_metrics_data(self, metrics: List[str], time_range: str) -> Dict[str, List[Dict]]:
        """Obtiene datos de métricas para el rango de tiempo"""
        try:
            from app.core.metrics_collector_enterprise import metrics_collector
            
            # Convertir time_range a timedelta
            time_delta = self._parse_time_range(time_range)
            
            result = {}
            for metric in metrics:
                # Simular datos de métricas (en producción vendría del collector)
                data_points = []
                now = datetime.now()
                
                # Generar puntos de datos cada 5 minutos
                for i in range(int(time_delta.total_seconds() // 300)):
                    timestamp = now - timedelta(seconds=i * 300)
                    value = self._simulate_metric_value(metric, timestamp)
                    
                    data_points.append({
                        "timestamp": timestamp.isoformat(),
                        "value": value
                    })
                
                result[metric] = list(reversed(data_points))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de métricas: {e}")
            return {}
    
    async def _get_aggregated_metrics(self, metrics: List[str], time_range: str) -> Dict[str, float]:
        """Obtiene métricas agregadas"""
        try:
            result = {}
            for metric in metrics:
                # Simular valor agregado
                result[metric] = self._simulate_metric_value(metric, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas agregadas: {e}")
            return {}
    
    async def _get_current_metric_value(self, metric: str) -> float:
        """Obtiene valor actual de métrica"""
        try:
            return self._simulate_metric_value(metric, datetime.now())
        except Exception as e:
            logger.error(f"❌ Error obteniendo valor actual: {e}")
            return 0.0
    
    async def _get_previous_metric_value(self, metric: str, time_ago: str) -> float:
        """Obtiene valor anterior de métrica"""
        try:
            time_delta = self._parse_time_range(time_ago)
            timestamp = datetime.now() - time_delta
            return self._simulate_metric_value(metric, timestamp)
        except Exception as e:
            logger.error(f"❌ Error obteniendo valor anterior: {e}")
            return 0.0
    
    async def _get_table_data(self, metrics: List[str]) -> List[Dict[str, Any]]:
        """Obtiene datos para tabla"""
        try:
            # Simular datos de tabla
            table_data = []
            for i, metric in enumerate(metrics):
                table_data.append({
                    "id": i + 1,
                    "metric": metric,
                    "value": self._simulate_metric_value(metric, datetime.now()),
                    "status": "healthy" if i % 3 != 0 else "warning",
                    "last_updated": datetime.now().isoformat()
                })
            
            return table_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de tabla: {e}")
            return []
    
    async def _get_services_status(self, services: List[str]) -> List[Dict[str, Any]]:
        """Obtiene estado de servicios"""
        try:
            services_status = []
            for service in services:
                # Simular estado de servicio
                status = "healthy"
                if service == "database":
                    status = "warning"
                elif service == "cache":
                    status = "critical"
                
                services_status.append({
                    "name": service,
                    "status": status,
                    "uptime": "99.9%",
                    "response_time": f"{self._simulate_metric_value(f'{service}_response_time', datetime.now()):.0f}ms",
                    "last_check": datetime.now().isoformat()
                })
            
            return services_status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado de servicios: {e}")
            return []
    
    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parsea string de rango de tiempo a timedelta"""
        if time_range.endswith("m"):
            return timedelta(minutes=int(time_range[:-1]))
        elif time_range.endswith("h"):
            return timedelta(hours=int(time_range[:-1]))
        elif time_range.endswith("d"):
            return timedelta(days=int(time_range[:-1]))
        else:
            return timedelta(hours=1)  # Default
    
    def _simulate_metric_value(self, metric: str, timestamp: datetime) -> float:
        """Simula valor de métrica"""
        import random
        import math
        
        # Simular valores realistas según el tipo de métrica
        base_values = {
            "cpu_usage": 45.0,
            "memory_usage": 65.0,
            "response_time": 250.0,
            "requests_per_second": 150.0,
            "error_rate": 2.5,
            "revenue": 15000.0,
            "conversion": 12.5,
            "user_satisfaction": 8.2
        }
        
        # Obtener valor base
        base_value = base_values.get(metric, 50.0)
        
        # Añadir variación temporal (ciclo diario)
        hour = timestamp.hour
        daily_factor = 0.8 + 0.4 * math.sin((hour - 6) * math.pi / 12)
        
        # Añadir ruido aleatorio
        noise = random.uniform(-0.1, 0.1)
        
        return max(0, base_value * daily_factor * (1 + noise))

# ===============================
# DATA AGGREGATOR
# ===============================

class DataAggregator:
    """Agregador de datos para dashboards"""
    
    def __init__(self):
        self.aggregation_cache = {}
        self.cache_ttl = 60  # segundos
    
    async def aggregate_data(
        self, 
        metrics: List[str], 
        time_range: str, 
        aggregation_func: str = "avg"
    ) -> Dict[str, float]:
        """Agrega datos según función especificada"""
        try:
            cache_key = f"{'-'.join(metrics)}_{time_range}_{aggregation_func}"
            
            # Verificar cache
            if cache_key in self.aggregation_cache:
                cached_data, timestamp = self.aggregation_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                    return cached_data
            
            # Obtener datos raw
            from app.core.metrics_collector_enterprise import metrics_collector
            
            result = {}
            for metric in metrics:
                # Simular agregación de datos
                values = [random.uniform(0, 100) for _ in range(10)]
                
                if aggregation_func == "avg":
                    result[metric] = statistics.mean(values)
                elif aggregation_func == "min":
                    result[metric] = min(values)
                elif aggregation_func == "max":
                    result[metric] = max(values)
                elif aggregation_func == "sum":
                    result[metric] = sum(values)
                else:
                    result[metric] = statistics.mean(values)
            
            # Cachear resultado
            self.aggregation_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error agregando datos: {e}")
            return {}

# ===============================
# DASHBOARD SERVICE
# ===============================

class DashboardService:
    """
    Servicio de dashboards enterprise con:
    - Dashboards en tiempo real
    - WebSocket para actualizaciones live
    - Múltiples tipos de gráficos
    - Configuración flexible
    - Cache inteligente
    """
    
    def __init__(self):
        self.websocket_manager = WebSocketManager()
        self.chart_generator = ChartGenerator()
        self.data_aggregator = DataAggregator()
        
        # Dashboards registrados
        self.dashboards: Dict[str, DashboardConfig] = {}
        
        # Estado del servicio
        self.enabled = True
        self.update_interval = DASHBOARD_CONFIG["real_time"]["update_interval"]
        
        # Estadísticas
        self.stats = {
            "total_dashboards": 0,
            "active_dashboards": 0,
            "total_updates": 0,
            "failed_updates": 0,
            "start_time": datetime.now()
        }
        
        # Tasks de background
        self._update_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Crear dashboards predefinidos
        self._create_default_dashboards()
        
        logger.info("📊 Dashboard Service Enterprise inicializado")
    
    def _create_default_dashboards(self):
        """Crea dashboards predefinidos"""
        # Executive Dashboard
        executive_charts = [
            ChartConfig(
                chart_id="revenue_today",
                name="Revenue Today",
                chart_type=ChartType.BIG_NUMBER,
                metrics=["revenue"],
                options={"format": "currency", "unit": "$"}
            ),
            ChartConfig(
                chart_id="conversion_rate",
                name="Conversion Rate",
                chart_type=ChartType.GAUGE,
                metrics=["conversion"],
                options={"max": 20, "target": 15}
            ),
            ChartConfig(
                chart_id="user_satisfaction",
                name="User Satisfaction",
                chart_type=ChartType.GAUGE,
                metrics=["user_satisfaction"],
                options={"max": 10, "target": 8.5}
            ),
            ChartConfig(
                chart_id="revenue_trend",
                name="Revenue Trend",
                chart_type=ChartType.LINE,
                metrics=["revenue"],
                time_range="24h",
                width=12,
                height=6
            )
        ]
        
        executive_dashboard = DashboardConfig(
            dashboard_id="executive",
            name="Executive Dashboard",
            dashboard_type=DashboardType.EXECUTIVE,
            charts=executive_charts,
            access_level="executive"
        )
        
        self.dashboards["executive"] = executive_dashboard
        
        # Operations Dashboard
        operations_charts = [
            ChartConfig(
                chart_id="system_overview",
                name="System Overview",
                chart_type=ChartType.STATUS_GRID,
                metrics=["api", "cache", "database", "load_balancer"],
                width=12,
                height=4
            ),
            ChartConfig(
                chart_id="response_times",
                name="Response Times",
                chart_type=ChartType.LINE,
                metrics=["response_time"],
                time_range="1h",
                width=6,
                height=4
            ),
            ChartConfig(
                chart_id="error_rates",
                name="Error Rates",
                chart_type=ChartType.LINE,
                metrics=["error_rate"],
                time_range="1h",
                width=6,
                height=4
            ),
            ChartConfig(
                chart_id="throughput",
                name="Throughput",
                chart_type=ChartType.BAR,
                metrics=["requests_per_second"],
                width=6,
                height=4
            ),
            ChartConfig(
                chart_id="resource_usage",
                name="Resource Usage",
                chart_type=ChartType.PIE,
                metrics=["cpu_usage", "memory_usage"],
                width=6,
                height=4
            )
        ]
        
        operations_dashboard = DashboardConfig(
            dashboard_id="operations",
            name="Operations Dashboard",
            dashboard_type=DashboardType.OPERATIONS,
            charts=operations_charts,
            access_level="operations"
        )
        
        self.dashboards["operations"] = operations_dashboard
        
        # Development Dashboard
        development_charts = [
            ChartConfig(
                chart_id="api_performance",
                name="API Performance",
                chart_type=ChartType.LINE,
                metrics=["response_time", "requests_per_second"],
                time_range="1h",
                width=12,
                height=6
            ),
            ChartConfig(
                chart_id="cache_metrics",
                name="Cache Metrics",
                chart_type=ChartType.TABLE,
                metrics=["cache_hits", "cache_misses", "cache_ratio"],
                width=6,
                height=4
            ),
            ChartConfig(
                chart_id="error_breakdown",
                name="Error Breakdown",
                chart_type=ChartType.PIE,
                metrics=["4xx_errors", "5xx_errors", "timeouts"],
                width=6,
                height=4
            )
        ]
        
        development_dashboard = DashboardConfig(
            dashboard_id="development",
            name="Development Dashboard",
            dashboard_type=DashboardType.DEVELOPMENT,
            charts=development_charts,
            access_level="developer"
        )
        
        self.dashboards["development"] = development_dashboard
        
        self.stats["total_dashboards"] = len(self.dashboards)
        logger.info(f"📊 Creados {len(self.dashboards)} dashboards predefinidos")
    
    async def start(self):
        """Inicia el dashboard service"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar tasks de background
        self._update_task = asyncio.create_task(self._update_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("🚀 Dashboard Service iniciado")
    
    async def stop(self):
        """Detiene el dashboard service"""
        self._running = False
        
        # Cancelar tasks
        for task in [self._update_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("🛑 Dashboard Service detenido")
    
    async def _update_loop(self):
        """Loop de actualización de dashboards"""
        while self._running:
            try:
                if self.enabled:
                    await self._update_all_dashboards()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ Error en loop de actualización: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Loop de limpieza"""
        while self._running:
            try:
                # Limpiar conexiones inactivas
                self.websocket_manager.cleanup_stale_connections()
                
                # Limpiar cache
                await self._cleanup_cache()
                
                await asyncio.sleep(300)  # Cada 5 minutos
                
            except Exception as e:
                logger.error(f"❌ Error en loop de limpieza: {e}")
                await asyncio.sleep(300)
    
    async def _update_all_dashboards(self):
        """Actualiza todos los dashboards activos"""
        active_dashboards = [
            dashboard_id for dashboard_id in self.dashboards.keys()
            if self.websocket_manager.get_dashboard_connections(dashboard_id)
        ]
        
        for dashboard_id in active_dashboards:
            try:
                await self.update_dashboard_data(dashboard_id)
            except Exception as e:
                logger.error(f"❌ Error actualizando dashboard {dashboard_id}: {e}")
                self.stats["failed_updates"] += 1
    
    async def _cleanup_cache(self):
        """Limpia cache expirado"""
        try:
            # Limpiar cache de chart generator
            current_time = datetime.now()
            expired_keys = []
            
            for key, (data, timestamp) in self.chart_generator.chart_cache.items():
                if (current_time - timestamp).total_seconds() > self.chart_generator.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.chart_generator.chart_cache[key]
            
            if expired_keys:
                logger.debug(f"🧹 Limpiadas {len(expired_keys)} entradas de cache")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando cache: {e}")
    
    # ===============================
    # GESTIÓN DE DASHBOARDS
    # ===============================
    
    async def create_dashboard(self, config: DashboardConfig) -> bool:
        """Crea un nuevo dashboard"""
        try:
            self.dashboards[config.dashboard_id] = config
            self.stats["total_dashboards"] = len(self.dashboards)
            
            logger.info(f"📊 Dashboard creado: {config.dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando dashboard: {e}")
            return False
    
    def get_dashboard(self, dashboard_id: str) -> Optional[DashboardConfig]:
        """Obtiene configuración de dashboard"""
        return self.dashboards.get(dashboard_id)
    
    def list_dashboards(self, access_level: str = None) -> List[Dict[str, Any]]:
        """Lista dashboards disponibles"""
        dashboards = []
        
        for dashboard in self.dashboards.values():
            if access_level and dashboard.access_level != access_level:
                continue
            
            dashboard_info = dashboard.to_dict()
            dashboard_info["active_connections"] = len(
                self.websocket_manager.get_dashboard_connections(dashboard.dashboard_id)
            )
            
            dashboards.append(dashboard_info)
        
        return dashboards
    
    async def update_dashboard_data(self, dashboard_id: str):
        """Actualiza datos del dashboard en tiempo real"""
        try:
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return
            
            # Generar datos para todos los gráficos
            dashboard_data = {
                "dashboard_id": dashboard_id,
                "timestamp": datetime.now().isoformat(),
                "charts": {}
            }
            
            for chart in dashboard.charts:
                chart_data = await self.chart_generator.generate_chart(chart)
                dashboard_data["charts"][chart.chart_id] = chart_data
            
            # Enviar actualizaciones via WebSocket
            await self.broadcast_updates(dashboard_id, dashboard_data)
            
            self.stats["total_updates"] += 1
            
        except Exception as e:
            logger.error(f"❌ Error actualizando datos de dashboard {dashboard_id}: {e}")
            self.stats["failed_updates"] += 1
    
    async def broadcast_updates(self, dashboard_id: str, data: Dict[str, Any]):
        """Envía actualizaciones via WebSocket"""
        try:
            connections = self.websocket_manager.get_dashboard_connections(dashboard_id)
            
            if not connections:
                return
            
            message = {
                "type": "dashboard_update",
                "data": data
            }
            
            # Simular envío de mensaje (en producción sería WebSocket real)
            for connection_id in connections:
                try:
                    # await websocket.send(json.dumps(message))
                    self.websocket_manager.stats["messages_sent"] += 1
                    logger.debug(f"📡 Mensaje enviado a {connection_id}")
                except Exception as e:
                    logger.error(f"❌ Error enviando mensaje a {connection_id}: {e}")
                    self.websocket_manager.stats["messages_failed"] += 1
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting updates: {e}")
    
    # ===============================
    # GESTIÓN DE CONEXIONES
    # ===============================
    
    def add_websocket_connection(
        self, 
        connection_id: str, 
        dashboard_id: str, 
        user_id: str = "anonymous"
    ) -> bool:
        """Añade conexión WebSocket"""
        return self.websocket_manager.add_connection(connection_id, dashboard_id, user_id)
    
    def remove_websocket_connection(self, connection_id: str) -> bool:
        """Remueve conexión WebSocket"""
        return self.websocket_manager.remove_connection(connection_id)
    
    def ping_connection(self, connection_id: str):
        """Actualiza ping de conexión"""
        self.websocket_manager.update_ping(connection_id)
    
    # ===============================
    # ESTADÍSTICAS
    # ===============================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del dashboard service"""
        uptime = datetime.now() - self.stats["start_time"]
        
        # Estadísticas de dashboards
        active_dashboards = len([
            d for d in self.dashboards.keys()
            if self.websocket_manager.get_dashboard_connections(d)
        ])
        
        # Estadísticas de WebSocket
        ws_stats = self.websocket_manager.get_stats()
        
        return {
            "dashboard_service": {
                "enabled": self.enabled,
                "uptime_seconds": uptime.total_seconds(),
                "update_interval": self.update_interval
            },
            "dashboards": {
                "total_dashboards": self.stats["total_dashboards"],
                "active_dashboards": active_dashboards,
                "dashboard_types": {
                    dashboard_type.value: len([
                        d for d in self.dashboards.values()
                        if d.dashboard_type == dashboard_type
                    ])
                    for dashboard_type in DashboardType
                }
            },
            "performance": {
                "total_updates": self.stats["total_updates"],
                "failed_updates": self.stats["failed_updates"],
                "success_rate": (
                    (self.stats["total_updates"] / max(self.stats["total_updates"] + self.stats["failed_updates"], 1)) * 100
                ),
                "updates_per_minute": self.stats["total_updates"] / max(uptime.total_seconds() / 60, 1)
            },
            "websocket": ws_stats["websocket"],
            "messaging": ws_stats["messaging"]
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del dashboard service
dashboard_service = DashboardService()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_dashboard_service():
    """Inicializa el dashboard service"""
    await dashboard_service.start()

async def create_custom_dashboard(
    dashboard_id: str,
    name: str,
    charts: List[ChartConfig],
    access_level: str = "user"
) -> bool:
    """Crea un dashboard personalizado"""
    config = DashboardConfig(
        dashboard_id=dashboard_id,
        name=name,
        dashboard_type=DashboardType.CUSTOM,
        charts=charts,
        access_level=access_level
    )
    return await dashboard_service.create_dashboard(config)

def get_dashboard_config(dashboard_id: str) -> Optional[DashboardConfig]:
    """Obtiene configuración de dashboard"""
    return dashboard_service.get_dashboard(dashboard_id)

def list_available_dashboards(access_level: str = None) -> List[Dict[str, Any]]:
    """Lista dashboards disponibles"""
    return dashboard_service.list_dashboards(access_level)

def add_dashboard_connection(
    connection_id: str, 
    dashboard_id: str, 
    user_id: str = "anonymous"
) -> bool:
    """Añade conexión a dashboard"""
    return dashboard_service.add_websocket_connection(connection_id, dashboard_id, user_id)

def remove_dashboard_connection(connection_id: str) -> bool:
    """Remueve conexión de dashboard"""
    return dashboard_service.remove_websocket_connection(connection_id)

def get_dashboard_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del dashboard service"""
    return dashboard_service.get_stats()

async def stop_dashboard_service():
    """Detiene el dashboard service"""
    await dashboard_service.stop() 