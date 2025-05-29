"""
📊 Metrics Collector Enterprise
Sistema avanzado de recolección de métricas para observabilidad completa
"""
import asyncio
import time
import logging
import psutil
import os
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import uuid
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN DE MÉTRICAS
# ===============================

# Configuración por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

METRICS_CONFIG = {
    "production": {
        "collection": {
            "interval": 15,
            "retention": {
                "raw": 3600,      # 1 hora en segundos
                "aggregated": 604800,  # 7 días
                "summary": 2592000     # 30 días
            },
            "storage": "prometheus",
            "export_format": "prometheus"
        },
        "custom_metrics": {
            "business_metrics": True,
            "rag_performance": True,
            "cache_efficiency": True,
            "user_experience": True
        },
        "aggregation": {
            "levels": ["1m", "5m", "15m", "1h", "1d"],
            "functions": ["avg", "min", "max", "p50", "p95", "p99"]
        }
    },
    "staging": {
        "collection": {
            "interval": 30,
            "retention": {
                "raw": 1800,      # 30 minutos
                "aggregated": 259200,  # 3 días
                "summary": 604800      # 7 días
            },
            "storage": "prometheus",
            "export_format": "prometheus"
        },
        "custom_metrics": {
            "business_metrics": True,
            "rag_performance": True,
            "cache_efficiency": False,
            "user_experience": False
        },
        "aggregation": {
            "levels": ["1m", "5m", "15m", "1h"],
            "functions": ["avg", "min", "max", "p95"]
        }
    },
    "development": {
        "collection": {
            "interval": 60,
            "retention": {
                "raw": 900,       # 15 minutos
                "aggregated": 86400,   # 1 día
                "summary": 259200      # 3 días
            },
            "storage": "memory",
            "export_format": "json"
        },
        "custom_metrics": {
            "business_metrics": False,
            "rag_performance": True,
            "cache_efficiency": False,
            "user_experience": False
        },
        "aggregation": {
            "levels": ["1m", "5m", "15m"],
            "functions": ["avg", "max"]
        }
    }
}

# Configuración actual
MC_CONFIG = METRICS_CONFIG.get(ENVIRONMENT, METRICS_CONFIG["development"])

# Métricas empresariales
BUSINESS_METRICS = {
    "sales_conversion": {
        "type": "counter",
        "description": "Tasa de conversión de ventas",
        "labels": ["product_category", "user_segment"],
        "unit": "percentage"
    },
    "recommendation_accuracy": {
        "type": "histogram",
        "description": "Precisión de recomendaciones",
        "buckets": [0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
        "unit": "ratio"
    },
    "user_satisfaction": {
        "type": "gauge",
        "description": "Score de satisfacción del usuario",
        "range": [1, 10],
        "unit": "score"
    },
    "revenue_per_user": {
        "type": "histogram",
        "description": "Ingresos por usuario",
        "buckets": [10, 50, 100, 500, 1000, 5000],
        "unit": "currency"
    }
}

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class MetricType(Enum):
    """Tipos de métricas"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class MetricCategory(Enum):
    """Categorías de métricas"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    CUSTOM = "custom"

@dataclass
class MetricPoint:
    """Punto de datos de métrica"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    category: MetricCategory = MetricCategory.SYSTEM
    unit: str = ""
    description: str = ""

@dataclass
class SystemMetrics:
    """Métricas del sistema"""
    cpu_usage_total: float = 0.0
    cpu_usage_per_core: List[float] = field(default_factory=list)
    memory_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_available_bytes: int = 0
    disk_usage_percent: float = 0.0
    disk_io_read_bytes: int = 0
    disk_io_write_bytes: int = 0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    load_average: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ApplicationMetrics:
    """Métricas de la aplicación"""
    request_count: int = 0
    request_duration_avg: float = 0.0
    request_duration_p95: float = 0.0
    request_duration_p99: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    active_connections: int = 0
    cache_hit_ratio: float = 0.0
    cache_miss_ratio: float = 0.0
    queue_depth: int = 0
    throughput_rps: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class BusinessMetrics:
    """Métricas de negocio"""
    sales_conversion_rate: float = 0.0
    revenue_total: float = 0.0
    revenue_per_user: float = 0.0
    user_satisfaction_score: float = 0.0
    recommendation_accuracy: float = 0.0
    cart_abandonment_rate: float = 0.0
    product_views: int = 0
    session_duration_avg: float = 0.0
    feature_usage: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RAGPerformanceMetrics:
    """Métricas específicas de RAG"""
    search_accuracy: float = 0.0
    search_latency_avg: float = 0.0
    search_latency_p95: float = 0.0
    recommendation_relevance: float = 0.0
    knowledge_base_coverage: float = 0.0
    query_complexity_avg: float = 0.0
    embedding_generation_time: float = 0.0
    vector_search_time: float = 0.0
    context_retrieval_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

# ===============================
# PROMETHEUS CLIENT
# ===============================

class PrometheusClient:
    """Cliente para exportar métricas a Prometheus"""
    
    def __init__(self):
        self.metrics_registry = {}
        self.enabled = MC_CONFIG["collection"]["storage"] == "prometheus"
    
    def register_metric(self, name: str, metric_type: MetricType, description: str, labels: List[str] = None):
        """Registra una métrica en el registry"""
        if not self.enabled:
            return
        
        self.metrics_registry[name] = {
            "type": metric_type.value,
            "description": description,
            "labels": labels or [],
            "samples": []
        }
    
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Registra un valor de métrica"""
        if not self.enabled or name not in self.metrics_registry:
            return
        
        sample = {
            "value": value,
            "timestamp": time.time(),
            "labels": labels or {}
        }
        
        self.metrics_registry[name]["samples"].append(sample)
        
        # Limpiar samples antiguos
        cutoff_time = time.time() - MC_CONFIG["collection"]["retention"]["raw"]
        self.metrics_registry[name]["samples"] = [
            s for s in self.metrics_registry[name]["samples"]
            if s["timestamp"] > cutoff_time
        ]
    
    def export_metrics(self) -> str:
        """Exporta métricas en formato Prometheus"""
        if not self.enabled:
            return ""
        
        output = []
        
        for name, metric in self.metrics_registry.items():
            # Header
            output.append(f"# HELP {name} {metric['description']}")
            output.append(f"# TYPE {name} {metric['type']}")
            
            # Samples
            for sample in metric["samples"]:
                labels_str = ""
                if sample["labels"]:
                    labels_list = [f'{k}="{v}"' for k, v in sample["labels"].items()]
                    labels_str = "{" + ",".join(labels_list) + "}"
                
                output.append(f"{name}{labels_str} {sample['value']} {int(sample['timestamp'] * 1000)}")
        
        return "\n".join(output)

# ===============================
# CUSTOM METRICS REGISTRY
# ===============================

class CustomMetricsRegistry:
    """Registry para métricas personalizadas"""
    
    def __init__(self):
        self.custom_metrics = {}
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))
    
    def register_custom_metric(
        self, 
        name: str, 
        metric_type: MetricType, 
        description: str,
        unit: str = "",
        labels: List[str] = None
    ):
        """Registra una métrica personalizada"""
        self.custom_metrics[name] = {
            "type": metric_type,
            "description": description,
            "unit": unit,
            "labels": labels or [],
            "created_at": datetime.now()
        }
        
        logger.info(f"📊 Métrica personalizada registrada: {name}")
    
    def record_custom_metric(
        self, 
        name: str, 
        value: float, 
        labels: Dict[str, str] = None,
        timestamp: datetime = None
    ):
        """Registra valor de métrica personalizada"""
        if name not in self.custom_metrics:
            logger.warning(f"Métrica {name} no registrada")
            return
        
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=timestamp or datetime.now(),
            labels=labels or {},
            metric_type=self.custom_metrics[name]["type"],
            category=MetricCategory.CUSTOM,
            unit=self.custom_metrics[name]["unit"],
            description=self.custom_metrics[name]["description"]
        )
        
        self.metric_history[name].append(point)
    
    def get_custom_metric_history(self, name: str, time_range: timedelta = None) -> List[MetricPoint]:
        """Obtiene historial de métrica personalizada"""
        if name not in self.metric_history:
            return []
        
        points = list(self.metric_history[name])
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            points = [p for p in points if p.timestamp >= cutoff_time]
        
        return points
    
    def get_all_custom_metrics(self) -> Dict[str, Any]:
        """Obtiene todas las métricas personalizadas"""
        result = {}
        
        for name, config in self.custom_metrics.items():
            recent_points = self.get_custom_metric_history(name, timedelta(hours=1))
            
            result[name] = {
                "config": config,
                "recent_count": len(recent_points),
                "latest_value": recent_points[-1].value if recent_points else None,
                "latest_timestamp": recent_points[-1].timestamp.isoformat() if recent_points else None
            }
        
        return result

# ===============================
# BUSINESS METRICS COLLECTOR
# ===============================

class BusinessMetricsCollector:
    """Recolector de métricas de negocio"""
    
    def __init__(self):
        self.enabled = MC_CONFIG["custom_metrics"]["business_metrics"]
        self.metrics_cache = {}
        self.last_collection = None
    
    async def collect_sales_metrics(self) -> Dict[str, float]:
        """Recolecta métricas de ventas"""
        if not self.enabled:
            return {}
        
        try:
            # Simular recolección de métricas de ventas
            # En producción, esto vendría de la base de datos
            
            # Obtener datos de ventas del último período
            sales_data = await self._get_sales_data()
            
            return {
                "sales_conversion_rate": sales_data.get("conversion_rate", 0.12),
                "revenue_total": sales_data.get("revenue_total", 15000.0),
                "revenue_per_user": sales_data.get("revenue_per_user", 75.0),
                "cart_abandonment_rate": sales_data.get("cart_abandonment", 0.68)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de ventas: {e}")
            return {}
    
    async def collect_user_experience_metrics(self) -> Dict[str, float]:
        """Recolecta métricas de experiencia de usuario"""
        if not self.enabled:
            return {}
        
        try:
            # Simular recolección de métricas de UX
            ux_data = await self._get_ux_data()
            
            return {
                "user_satisfaction_score": ux_data.get("satisfaction", 8.2),
                "session_duration_avg": ux_data.get("session_duration", 420.0),  # segundos
                "page_load_time_avg": ux_data.get("page_load_time", 1.2),  # segundos
                "feature_usage_total": ux_data.get("feature_usage", 1250)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de UX: {e}")
            return {}
    
    async def collect_rag_performance_metrics(self) -> Dict[str, float]:
        """Recolecta métricas de performance de RAG"""
        try:
            # Obtener métricas de los sistemas RAG
            from app.core.cache_enterprise import get_cache_stats
            
            cache_stats = get_cache_stats()
            
            # Simular métricas específicas de RAG
            return {
                "search_accuracy": 0.87,
                "search_latency_avg": 145.0,  # ms
                "search_latency_p95": 280.0,  # ms
                "recommendation_relevance": 0.82,
                "knowledge_base_coverage": 0.94,
                "query_complexity_avg": 3.2,
                "embedding_generation_time": 45.0,  # ms
                "vector_search_time": 25.0,  # ms
                "context_retrieval_time": 75.0,  # ms
                "cache_hit_ratio": cache_stats.get("hit_ratio", 0.85)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de RAG: {e}")
            return {}
    
    async def _get_sales_data(self) -> Dict[str, float]:
        """Simula obtención de datos de ventas"""
        # En producción, esto consultaría la base de datos
        import random
        
        base_conversion = 0.12
        base_revenue = 15000.0
        
        # Simular variación realista
        return {
            "conversion_rate": base_conversion + random.uniform(-0.02, 0.03),
            "revenue_total": base_revenue + random.uniform(-2000, 3000),
            "revenue_per_user": random.uniform(50, 120),
            "cart_abandonment": 0.68 + random.uniform(-0.1, 0.1)
        }
    
    async def _get_ux_data(self) -> Dict[str, float]:
        """Simula obtención de datos de UX"""
        import random
        
        return {
            "satisfaction": 8.2 + random.uniform(-0.5, 0.8),
            "session_duration": 420 + random.uniform(-60, 120),
            "page_load_time": 1.2 + random.uniform(-0.3, 0.8),
            "feature_usage": random.randint(1000, 1500)
        }

# ===============================
# METRICS COLLECTOR ENTERPRISE
# ===============================

class MetricsCollectorEnterprise:
    """
    Recolector de métricas enterprise con:
    - Múltiples tipos de métricas (sistema, aplicación, negocio)
    - Exportación a Prometheus
    - Métricas personalizadas
    - Agregación temporal
    - Retención configurable
    """
    
    def __init__(self):
        self.config = MC_CONFIG.copy()
        self.prometheus_client = PrometheusClient()
        self.custom_metrics = CustomMetricsRegistry()
        self.business_metrics = BusinessMetricsCollector()
        
        # Estado del collector
        self.enabled = True
        self.collection_interval = self.config["collection"]["interval"]
        
        # Historial de métricas
        self.metrics_history = {
            "system": deque(maxlen=1000),
            "application": deque(maxlen=1000),
            "business": deque(maxlen=1000),
            "rag": deque(maxlen=1000)
        }
        
        # Estadísticas
        self.stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "last_collection": None,
            "collection_duration_avg": 0.0,
            "start_time": datetime.now()
        }
        
        # Tasks de background
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Inicializar métricas de Prometheus
        self._initialize_prometheus_metrics()
        
        logger.info(f"📊 Metrics Collector Enterprise inicializado para entorno: {ENVIRONMENT}")
    
    def _initialize_prometheus_metrics(self):
        """Inicializa métricas en Prometheus"""
        if not self.prometheus_client.enabled:
            return
        
        # Métricas de sistema
        self.prometheus_client.register_metric(
            "system_cpu_usage_percent", 
            MetricType.GAUGE, 
            "CPU usage percentage"
        )
        self.prometheus_client.register_metric(
            "system_memory_usage_percent", 
            MetricType.GAUGE, 
            "Memory usage percentage"
        )
        self.prometheus_client.register_metric(
            "system_disk_usage_percent", 
            MetricType.GAUGE, 
            "Disk usage percentage"
        )
        
        # Métricas de aplicación
        self.prometheus_client.register_metric(
            "app_request_duration_seconds", 
            MetricType.HISTOGRAM, 
            "Request duration in seconds"
        )
        self.prometheus_client.register_metric(
            "app_requests_total", 
            MetricType.COUNTER, 
            "Total number of requests"
        )
        self.prometheus_client.register_metric(
            "app_errors_total", 
            MetricType.COUNTER, 
            "Total number of errors"
        )
        
        # Métricas de negocio (si están habilitadas)
        if self.config["custom_metrics"]["business_metrics"]:
            self.prometheus_client.register_metric(
                "business_conversion_rate", 
                MetricType.GAUGE, 
                "Sales conversion rate"
            )
            self.prometheus_client.register_metric(
                "business_revenue_total", 
                MetricType.GAUGE, 
                "Total revenue"
            )
    
    async def start(self):
        """Inicia el collector de métricas"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar loop de recolección
        self._collection_task = asyncio.create_task(self._collection_loop())
        
        logger.info("🚀 Metrics Collector Enterprise iniciado")
    
    async def stop(self):
        """Detiene el collector de métricas"""
        self._running = False
        
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Metrics Collector Enterprise detenido")
    
    async def _collection_loop(self):
        """Loop principal de recolección de métricas"""
        while self._running:
            try:
                if self.enabled:
                    await self._collect_all_metrics()
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"❌ Error en loop de recolección: {e}")
                self.stats["failed_collections"] += 1
                await asyncio.sleep(60)  # Esperar más tiempo si hay error
    
    async def _collect_all_metrics(self):
        """Recolecta todas las métricas"""
        start_time = time.time()
        
        try:
            self.stats["total_collections"] += 1
            
            # Recolectar métricas en paralelo
            system_task = asyncio.create_task(self.collect_system_metrics())
            app_task = asyncio.create_task(self.collect_application_metrics())
            business_task = asyncio.create_task(self.collect_business_metrics())
            rag_task = asyncio.create_task(self.collect_rag_metrics())
            
            # Esperar a que terminen todas
            system_metrics, app_metrics, business_metrics, rag_metrics = await asyncio.gather(
                system_task, app_task, business_task, rag_task,
                return_exceptions=True
            )
            
            # Almacenar en historial
            if isinstance(system_metrics, SystemMetrics):
                self.metrics_history["system"].append(system_metrics)
                await self._export_system_metrics(system_metrics)
            
            if isinstance(app_metrics, ApplicationMetrics):
                self.metrics_history["application"].append(app_metrics)
                await self._export_application_metrics(app_metrics)
            
            if isinstance(business_metrics, BusinessMetrics):
                self.metrics_history["business"].append(business_metrics)
                await self._export_business_metrics(business_metrics)
            
            if isinstance(rag_metrics, RAGPerformanceMetrics):
                self.metrics_history["rag"].append(rag_metrics)
                await self._export_rag_metrics(rag_metrics)
            
            # Actualizar estadísticas
            duration = time.time() - start_time
            self.stats["successful_collections"] += 1
            self.stats["last_collection"] = datetime.now()
            
            # Actualizar promedio de duración
            if self.stats["collection_duration_avg"] == 0:
                self.stats["collection_duration_avg"] = duration
            else:
                self.stats["collection_duration_avg"] = (
                    self.stats["collection_duration_avg"] * 0.9 + duration * 0.1
                )
            
            logger.debug(f"Recolección completada en {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Error en recolección de métricas: {e}")
            self.stats["failed_collections"] += 1
    
    # ===============================
    # RECOLECCIÓN DE MÉTRICAS
    # ===============================
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Recolecta métricas del sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network
            network_io = psutil.net_io_counters()
            
            # Process
            process_count = len(psutil.pids())
            
            # Load average (Unix only)
            load_avg = []
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                load_avg = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                cpu_usage_total=cpu_percent,
                cpu_usage_per_core=cpu_per_core,
                memory_usage_percent=memory.percent,
                memory_usage_bytes=memory.used,
                memory_available_bytes=memory.available,
                disk_usage_percent=disk.percent,
                disk_io_read_bytes=disk_io.read_bytes if disk_io else 0,
                disk_io_write_bytes=disk_io.write_bytes if disk_io else 0,
                network_bytes_sent=network_io.bytes_sent if network_io else 0,
                network_bytes_recv=network_io.bytes_recv if network_io else 0,
                process_count=process_count,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas del sistema: {e}")
            return SystemMetrics()
    
    async def collect_application_metrics(self) -> ApplicationMetrics:
        """Recolecta métricas de la aplicación"""
        try:
            # Obtener métricas del load balancer
            from app.core.load_balancer import get_load_balancer_stats
            
            lb_stats = get_load_balancer_stats()
            performance = lb_stats.get("performance", {})
            
            # Calcular métricas derivadas
            total_requests = performance.get("total_requests", 0)
            successful_requests = performance.get("successful_requests", 0)
            failed_requests = performance.get("failed_requests", 0)
            
            error_rate = 0.0
            if total_requests > 0:
                error_rate = (failed_requests / total_requests) * 100
            
            # Simular métricas adicionales
            return ApplicationMetrics(
                request_count=total_requests,
                request_duration_avg=250.0,  # ms
                request_duration_p95=450.0,  # ms
                request_duration_p99=800.0,  # ms
                error_count=failed_requests,
                error_rate=error_rate,
                active_connections=lb_stats.get("load_balancer", {}).get("healthy_instances", 0),
                cache_hit_ratio=85.0,  # %
                cache_miss_ratio=15.0,  # %
                queue_depth=0,
                throughput_rps=performance.get("requests_per_second", 0.0)
            )
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de aplicación: {e}")
            return ApplicationMetrics()
    
    async def collect_business_metrics(self) -> BusinessMetrics:
        """Recolecta métricas de negocio"""
        try:
            if not self.config["custom_metrics"]["business_metrics"]:
                return BusinessMetrics()
            
            # Recolectar métricas de ventas y UX
            sales_metrics = await self.business_metrics.collect_sales_metrics()
            ux_metrics = await self.business_metrics.collect_user_experience_metrics()
            
            return BusinessMetrics(
                sales_conversion_rate=sales_metrics.get("sales_conversion_rate", 0.0),
                revenue_total=sales_metrics.get("revenue_total", 0.0),
                revenue_per_user=sales_metrics.get("revenue_per_user", 0.0),
                user_satisfaction_score=ux_metrics.get("user_satisfaction_score", 0.0),
                recommendation_accuracy=0.87,  # Simulated
                cart_abandonment_rate=sales_metrics.get("cart_abandonment_rate", 0.0),
                product_views=1250,  # Simulated
                session_duration_avg=ux_metrics.get("session_duration_avg", 0.0),
                feature_usage={"search": 450, "recommendations": 320, "cart": 180}
            )
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de negocio: {e}")
            return BusinessMetrics()
    
    async def collect_rag_metrics(self) -> RAGPerformanceMetrics:
        """Recolecta métricas específicas de RAG"""
        try:
            if not self.config["custom_metrics"]["rag_performance"]:
                return RAGPerformanceMetrics()
            
            # Obtener métricas de RAG
            rag_metrics = await self.business_metrics.collect_rag_performance_metrics()
            
            return RAGPerformanceMetrics(
                search_accuracy=rag_metrics.get("search_accuracy", 0.0),
                search_latency_avg=rag_metrics.get("search_latency_avg", 0.0),
                search_latency_p95=rag_metrics.get("search_latency_p95", 0.0),
                recommendation_relevance=rag_metrics.get("recommendation_relevance", 0.0),
                knowledge_base_coverage=rag_metrics.get("knowledge_base_coverage", 0.0),
                query_complexity_avg=rag_metrics.get("query_complexity_avg", 0.0),
                embedding_generation_time=rag_metrics.get("embedding_generation_time", 0.0),
                vector_search_time=rag_metrics.get("vector_search_time", 0.0),
                context_retrieval_time=rag_metrics.get("context_retrieval_time", 0.0)
            )
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de RAG: {e}")
            return RAGPerformanceMetrics()
    
    # ===============================
    # EXPORTACIÓN DE MÉTRICAS
    # ===============================
    
    async def _export_system_metrics(self, metrics: SystemMetrics):
        """Exporta métricas del sistema"""
        if self.prometheus_client.enabled:
            self.prometheus_client.record_metric("system_cpu_usage_percent", metrics.cpu_usage_total)
            self.prometheus_client.record_metric("system_memory_usage_percent", metrics.memory_usage_percent)
            self.prometheus_client.record_metric("system_disk_usage_percent", metrics.disk_usage_percent)
    
    async def _export_application_metrics(self, metrics: ApplicationMetrics):
        """Exporta métricas de aplicación"""
        if self.prometheus_client.enabled:
            self.prometheus_client.record_metric("app_request_duration_seconds", metrics.request_duration_avg / 1000)
            self.prometheus_client.record_metric("app_requests_total", metrics.request_count)
            self.prometheus_client.record_metric("app_errors_total", metrics.error_count)
    
    async def _export_business_metrics(self, metrics: BusinessMetrics):
        """Exporta métricas de negocio"""
        if self.prometheus_client.enabled and self.config["custom_metrics"]["business_metrics"]:
            self.prometheus_client.record_metric("business_conversion_rate", metrics.sales_conversion_rate)
            self.prometheus_client.record_metric("business_revenue_total", metrics.revenue_total)
    
    async def _export_rag_metrics(self, metrics: RAGPerformanceMetrics):
        """Exporta métricas de RAG"""
        # Las métricas de RAG se pueden exportar como métricas personalizadas
        if self.config["custom_metrics"]["rag_performance"]:
            self.custom_metrics.record_custom_metric("rag_search_accuracy", metrics.search_accuracy)
            self.custom_metrics.record_custom_metric("rag_search_latency_avg", metrics.search_latency_avg)
            self.custom_metrics.record_custom_metric("rag_recommendation_relevance", metrics.recommendation_relevance)
    
    # ===============================
    # MÉTRICAS PERSONALIZADAS
    # ===============================
    
    def register_custom_metric(
        self, 
        name: str, 
        metric_type: MetricType, 
        description: str,
        unit: str = "",
        labels: List[str] = None
    ):
        """Registra una métrica personalizada"""
        self.custom_metrics.register_custom_metric(name, metric_type, description, unit, labels)
        
        # También registrar en Prometheus si está habilitado
        if self.prometheus_client.enabled:
            self.prometheus_client.register_metric(name, metric_type, description, labels)
    
    def record_custom_metric(
        self, 
        name: str, 
        value: float, 
        labels: Dict[str, str] = None
    ):
        """Registra valor de métrica personalizada"""
        self.custom_metrics.record_custom_metric(name, value, labels)
        
        # También registrar en Prometheus si está habilitado
        if self.prometheus_client.enabled:
            self.prometheus_client.record_metric(name, value, labels)
    
    # ===============================
    # CONSULTAS Y ESTADÍSTICAS
    # ===============================
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Obtiene las métricas más recientes"""
        result = {}
        
        for category, history in self.metrics_history.items():
            if history:
                latest = history[-1]
                result[category] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "data": latest.__dict__
                }
        
        return result
    
    def get_metrics_history(
        self, 
        category: str, 
        time_range: timedelta = None
    ) -> List[Dict[str, Any]]:
        """Obtiene historial de métricas por categoría"""
        if category not in self.metrics_history:
            return []
        
        history = list(self.metrics_history[category])
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            history = [m for m in history if m.timestamp >= cutoff_time]
        
        return [{"timestamp": m.timestamp.isoformat(), "data": m.__dict__} for m in history]
    
    def get_prometheus_metrics(self) -> str:
        """Obtiene métricas en formato Prometheus"""
        return self.prometheus_client.export_metrics()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del collector"""
        uptime = datetime.now() - self.stats["start_time"]
        
        success_rate = 0.0
        if self.stats["total_collections"] > 0:
            success_rate = (self.stats["successful_collections"] / self.stats["total_collections"]) * 100
        
        return {
            "collector": {
                "enabled": self.enabled,
                "collection_interval": self.collection_interval,
                "uptime_seconds": uptime.total_seconds()
            },
            "performance": {
                "total_collections": self.stats["total_collections"],
                "successful_collections": self.stats["successful_collections"],
                "failed_collections": self.stats["failed_collections"],
                "success_rate": round(success_rate, 2),
                "avg_collection_duration": round(self.stats["collection_duration_avg"], 3),
                "last_collection": self.stats["last_collection"].isoformat() if self.stats["last_collection"] else None
            },
            "metrics_count": {
                "system": len(self.metrics_history["system"]),
                "application": len(self.metrics_history["application"]),
                "business": len(self.metrics_history["business"]),
                "rag": len(self.metrics_history["rag"]),
                "custom": len(self.custom_metrics.custom_metrics)
            },
            "configuration": {
                "environment": ENVIRONMENT,
                "prometheus_enabled": self.prometheus_client.enabled,
                "business_metrics_enabled": self.config["custom_metrics"]["business_metrics"],
                "rag_metrics_enabled": self.config["custom_metrics"]["rag_performance"]
            }
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del metrics collector
metrics_collector = MetricsCollectorEnterprise()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_metrics_collector():
    """Inicializa el metrics collector"""
    await metrics_collector.start()

def register_custom_metric(
    name: str, 
    metric_type: MetricType, 
    description: str,
    unit: str = "",
    labels: List[str] = None
):
    """Registra una métrica personalizada"""
    metrics_collector.register_custom_metric(name, metric_type, description, unit, labels)

def record_custom_metric(name: str, value: float, labels: Dict[str, str] = None):
    """Registra valor de métrica personalizada"""
    metrics_collector.record_custom_metric(name, value, labels)

def get_latest_metrics() -> Dict[str, Any]:
    """Obtiene las métricas más recientes"""
    return metrics_collector.get_latest_metrics()

def get_metrics_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del metrics collector"""
    return metrics_collector.get_stats()

def get_prometheus_metrics() -> str:
    """Obtiene métricas en formato Prometheus"""
    return metrics_collector.get_prometheus_metrics()

async def stop_metrics_collector():
    """Detiene el metrics collector"""
    await metrics_collector.stop() 