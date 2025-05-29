"""
📈 Auto-scaler Service Enterprise
Servicio de auto-scaling basado en métricas con decisiones inteligentes
"""
import asyncio
import time
import logging
import psutil
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN AUTO-SCALING
# ===============================

# Configuración por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

AUTO_SCALING_CONFIG = {
    "production": {
        "min_instances": 3,
        "max_instances": 20,
        "target_cpu_percent": 70,
        "target_memory_percent": 80,
        "scale_up_threshold": 80,
        "scale_down_threshold": 30,
        "scale_up_cooldown": 300,    # 5 minutos
        "scale_down_cooldown": 600,  # 10 minutos
        "metrics_window": 300,       # 5 minutos
        "evaluation_interval": 60    # 1 minuto
    },
    "staging": {
        "min_instances": 2,
        "max_instances": 10,
        "target_cpu_percent": 75,
        "target_memory_percent": 85,
        "scale_up_threshold": 85,
        "scale_down_threshold": 40,
        "scale_up_cooldown": 180,    # 3 minutos
        "scale_down_cooldown": 300,  # 5 minutos
        "metrics_window": 180,       # 3 minutos
        "evaluation_interval": 45    # 45 segundos
    },
    "development": {
        "min_instances": 1,
        "max_instances": 3,
        "target_cpu_percent": 80,
        "target_memory_percent": 90,
        "scale_up_threshold": 90,
        "scale_down_threshold": 50,
        "scale_up_cooldown": 60,     # 1 minuto
        "scale_down_cooldown": 120,  # 2 minutos
        "metrics_window": 120,       # 2 minutos
        "evaluation_interval": 30    # 30 segundos
    }
}

# Configuración actual
AS_CONFIG = AUTO_SCALING_CONFIG.get(ENVIRONMENT, AUTO_SCALING_CONFIG["development"])

# Métricas para auto-scaling con pesos
SCALING_METRICS = {
    "cpu_utilization": {
        "weight": 0.3,
        "scale_up_threshold": AS_CONFIG["scale_up_threshold"],
        "scale_down_threshold": AS_CONFIG["scale_down_threshold"],
        "measurement_window": AS_CONFIG["metrics_window"]
    },
    "memory_utilization": {
        "weight": 0.2,
        "scale_up_threshold": AS_CONFIG["target_memory_percent"],
        "scale_down_threshold": AS_CONFIG["target_memory_percent"] - 30,
        "measurement_window": AS_CONFIG["metrics_window"]
    },
    "request_rate": {
        "weight": 0.3,
        "scale_up_threshold": 100,  # requests/minute por instancia
        "scale_down_threshold": 20,
        "measurement_window": 180   # 3 minutos
    },
    "response_time": {
        "weight": 0.2,
        "scale_up_threshold": 2000,  # ms
        "scale_down_threshold": 500,
        "measurement_window": 180
    }
}

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class ScalingAction(Enum):
    """Acciones de escalado"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"
    COOLDOWN = "cooldown"

class ScalingReason(Enum):
    """Razones de escalado"""
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_REQUEST_RATE = "high_request_rate"
    HIGH_RESPONSE_TIME = "high_response_time"
    LOW_UTILIZATION = "low_utilization"
    MANUAL_TRIGGER = "manual_trigger"
    PREDICTIVE = "predictive"

@dataclass
class MetricDataPoint:
    """Punto de datos de métrica"""
    timestamp: datetime
    value: float
    instance_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScalingMetrics:
    """Métricas para decisiones de escalado"""
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    request_rate: float = 0.0
    response_time: float = 0.0
    active_instances: int = 0
    healthy_instances: int = 0
    total_requests: int = 0
    error_rate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_weighted_score(self) -> float:
        """Calcula score ponderado para decisión de escalado"""
        score = 0.0
        
        # CPU (normalizado a 0-100)
        cpu_score = min(self.cpu_utilization / 100, 1.0)
        score += cpu_score * SCALING_METRICS["cpu_utilization"]["weight"]
        
        # Memory (normalizado a 0-100)
        memory_score = min(self.memory_utilization / 100, 1.0)
        score += memory_score * SCALING_METRICS["memory_utilization"]["weight"]
        
        # Request rate (normalizado basado en threshold)
        request_threshold = SCALING_METRICS["request_rate"]["scale_up_threshold"]
        request_score = min(self.request_rate / request_threshold, 1.0)
        score += request_score * SCALING_METRICS["request_rate"]["weight"]
        
        # Response time (normalizado basado en threshold)
        response_threshold = SCALING_METRICS["response_time"]["scale_up_threshold"]
        response_score = min(self.response_time / response_threshold, 1.0)
        score += response_score * SCALING_METRICS["response_time"]["weight"]
        
        return score

@dataclass
class ScalingDecision:
    """Decisión de escalado"""
    action: ScalingAction
    reason: ScalingReason
    current_instances: int
    target_instances: int
    confidence: float
    metrics: ScalingMetrics
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def instances_change(self) -> int:
        """Cambio en número de instancias"""
        return self.target_instances - self.current_instances

@dataclass
class ScalingEvent:
    """Evento de escalado ejecutado"""
    event_id: str
    decision: ScalingDecision
    execution_start: datetime
    execution_end: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    actual_instances_before: int = 0
    actual_instances_after: int = 0

# ===============================
# METRICS COLLECTOR
# ===============================

class MetricsCollector:
    """Recolector de métricas del sistema"""
    
    def __init__(self):
        self.metrics_history: Dict[str, List[MetricDataPoint]] = {
            "cpu_utilization": [],
            "memory_utilization": [],
            "request_rate": [],
            "response_time": []
        }
        self.max_history_size = 1000  # Máximo puntos por métrica
    
    async def collect_system_metrics(self) -> Dict[str, float]:
        """Recolecta métricas del sistema actual"""
        try:
            # CPU utilization
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory utilization
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk utilization (opcional)
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            return {
                "cpu_utilization": cpu_percent,
                "memory_utilization": memory_percent,
                "disk_utilization": disk_percent,
                "available_memory_gb": memory.available / (1024**3),
                "total_memory_gb": memory.total / (1024**3)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas del sistema: {e}")
            return {
                "cpu_utilization": 0.0,
                "memory_utilization": 0.0,
                "disk_utilization": 0.0,
                "available_memory_gb": 0.0,
                "total_memory_gb": 0.0
            }
    
    async def collect_application_metrics(self) -> Dict[str, float]:
        """Recolecta métricas de la aplicación"""
        try:
            # Importar load balancer para obtener métricas
            from app.core.load_balancer import get_load_balancer_stats
            
            lb_stats = get_load_balancer_stats()
            
            # Extraer métricas relevantes
            performance = lb_stats.get("performance", {})
            load_balancer = lb_stats.get("load_balancer", {})
            
            total_requests = performance.get("total_requests", 0)
            uptime_seconds = load_balancer.get("uptime_seconds", 1)
            
            # Calcular request rate (requests per minute)
            request_rate = (total_requests / max(uptime_seconds, 1)) * 60
            
            # Response time promedio (simulado por ahora)
            # En producción se obtendría de métricas reales
            avg_response_time = 500.0  # ms
            
            return {
                "request_rate": request_rate,
                "response_time": avg_response_time,
                "total_requests": total_requests,
                "success_rate": performance.get("success_rate", 100.0),
                "error_rate": 100.0 - performance.get("success_rate", 100.0),
                "active_instances": load_balancer.get("total_instances", 1),
                "healthy_instances": load_balancer.get("healthy_instances", 1)
            }
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas de aplicación: {e}")
            return {
                "request_rate": 0.0,
                "response_time": 1000.0,
                "total_requests": 0,
                "success_rate": 100.0,
                "error_rate": 0.0,
                "active_instances": 1,
                "healthy_instances": 1
            }
    
    async def collect_all_metrics(self) -> ScalingMetrics:
        """Recolecta todas las métricas para escalado"""
        try:
            # Recolectar métricas del sistema y aplicación
            system_metrics = await self.collect_system_metrics()
            app_metrics = await self.collect_application_metrics()
            
            # Crear objeto de métricas
            metrics = ScalingMetrics(
                cpu_utilization=system_metrics["cpu_utilization"],
                memory_utilization=system_metrics["memory_utilization"],
                request_rate=app_metrics["request_rate"],
                response_time=app_metrics["response_time"],
                active_instances=app_metrics["active_instances"],
                healthy_instances=app_metrics["healthy_instances"],
                total_requests=app_metrics["total_requests"],
                error_rate=app_metrics["error_rate"]
            )
            
            # Almacenar en historial
            await self._store_metrics_history(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error recolectando métricas: {e}")
            # Retornar métricas por defecto
            return ScalingMetrics()
    
    async def _store_metrics_history(self, metrics: ScalingMetrics):
        """Almacena métricas en el historial"""
        try:
            timestamp = datetime.now()
            
            # Almacenar cada métrica
            metric_values = {
                "cpu_utilization": metrics.cpu_utilization,
                "memory_utilization": metrics.memory_utilization,
                "request_rate": metrics.request_rate,
                "response_time": metrics.response_time
            }
            
            for metric_name, value in metric_values.items():
                data_point = MetricDataPoint(
                    timestamp=timestamp,
                    value=value
                )
                
                self.metrics_history[metric_name].append(data_point)
                
                # Limpiar historial si excede el límite
                if len(self.metrics_history[metric_name]) > self.max_history_size:
                    self.metrics_history[metric_name] = self.metrics_history[metric_name][-self.max_history_size:]
                    
        except Exception as e:
            logger.error(f"❌ Error almacenando historial de métricas: {e}")
    
    def get_metric_trend(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Obtiene tendencia de una métrica en una ventana de tiempo"""
        try:
            if metric_name not in self.metrics_history:
                return {"trend": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
            
            # Filtrar datos en la ventana de tiempo
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_data = [
                dp for dp in self.metrics_history[metric_name]
                if dp.timestamp >= cutoff_time
            ]
            
            if len(recent_data) < 2:
                return {"trend": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
            
            values = [dp.value for dp in recent_data]
            
            # Calcular tendencia (diferencia entre promedio de primera y segunda mitad)
            mid_point = len(values) // 2
            first_half_avg = statistics.mean(values[:mid_point]) if mid_point > 0 else 0
            second_half_avg = statistics.mean(values[mid_point:])
            trend = second_half_avg - first_half_avg
            
            return {
                "trend": trend,
                "avg": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "count": len(values)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando tendencia de {metric_name}: {e}")
            return {"trend": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

# ===============================
# SCALING POLICY ENGINE
# ===============================

class ScalingPolicy:
    """Motor de políticas de escalado"""
    
    def __init__(self):
        self.config = AS_CONFIG.copy()
        self.last_scale_up = None
        self.last_scale_down = None
        self.scaling_history: List[ScalingEvent] = []
    
    async def evaluate_scaling_decision(
        self, 
        metrics: ScalingMetrics,
        metrics_collector: MetricsCollector
    ) -> ScalingDecision:
        """Evalúa si es necesario escalar y en qué dirección"""
        try:
            current_instances = metrics.active_instances
            
            # Verificar cooldown periods
            if await self._is_in_cooldown():
                return ScalingDecision(
                    action=ScalingAction.COOLDOWN,
                    reason=ScalingReason.MANUAL_TRIGGER,
                    current_instances=current_instances,
                    target_instances=current_instances,
                    confidence=1.0,
                    metrics=metrics,
                    metadata={"cooldown_remaining": await self._get_cooldown_remaining()}
                )
            
            # Evaluar necesidad de scale up
            scale_up_decision = await self._evaluate_scale_up(metrics, metrics_collector)
            if scale_up_decision.action == ScalingAction.SCALE_UP:
                return scale_up_decision
            
            # Evaluar necesidad de scale down
            scale_down_decision = await self._evaluate_scale_down(metrics, metrics_collector)
            if scale_down_decision.action == ScalingAction.SCALE_DOWN:
                return scale_down_decision
            
            # No action needed
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                reason=ScalingReason.MANUAL_TRIGGER,
                current_instances=current_instances,
                target_instances=current_instances,
                confidence=0.5,
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"❌ Error evaluando decisión de escalado: {e}")
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                reason=ScalingReason.MANUAL_TRIGGER,
                current_instances=metrics.active_instances,
                target_instances=metrics.active_instances,
                confidence=0.0,
                metrics=metrics
            )
    
    async def _evaluate_scale_up(
        self, 
        metrics: ScalingMetrics, 
        metrics_collector: MetricsCollector
    ) -> ScalingDecision:
        """Evalúa necesidad de scale up"""
        current_instances = metrics.active_instances
        max_instances = self.config["max_instances"]
        
        # No escalar si ya estamos en el máximo
        if current_instances >= max_instances:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                reason=ScalingReason.MANUAL_TRIGGER,
                current_instances=current_instances,
                target_instances=current_instances,
                confidence=0.0,
                metrics=metrics,
                metadata={"reason": "max_instances_reached"}
            )
        
        # Evaluar cada métrica
        scale_up_reasons = []
        confidence_scores = []
        
        # CPU
        if metrics.cpu_utilization > SCALING_METRICS["cpu_utilization"]["scale_up_threshold"]:
            scale_up_reasons.append(ScalingReason.HIGH_CPU)
            confidence_scores.append(
                min(metrics.cpu_utilization / 100, 1.0) * SCALING_METRICS["cpu_utilization"]["weight"]
            )
        
        # Memory
        if metrics.memory_utilization > SCALING_METRICS["memory_utilization"]["scale_up_threshold"]:
            scale_up_reasons.append(ScalingReason.HIGH_MEMORY)
            confidence_scores.append(
                min(metrics.memory_utilization / 100, 1.0) * SCALING_METRICS["memory_utilization"]["weight"]
            )
        
        # Request rate
        request_threshold = SCALING_METRICS["request_rate"]["scale_up_threshold"]
        if metrics.request_rate > request_threshold:
            scale_up_reasons.append(ScalingReason.HIGH_REQUEST_RATE)
            confidence_scores.append(
                min(metrics.request_rate / request_threshold, 1.0) * SCALING_METRICS["request_rate"]["weight"]
            )
        
        # Response time
        response_threshold = SCALING_METRICS["response_time"]["scale_up_threshold"]
        if metrics.response_time > response_threshold:
            scale_up_reasons.append(ScalingReason.HIGH_RESPONSE_TIME)
            confidence_scores.append(
                min(metrics.response_time / response_threshold, 1.0) * SCALING_METRICS["response_time"]["weight"]
            )
        
        # Decidir si escalar
        if scale_up_reasons:
            # Calcular número de instancias objetivo
            weighted_score = metrics.get_weighted_score()
            
            # Escalado conservador: +1 instancia por defecto, más si la carga es muy alta
            if weighted_score > 0.9:
                instances_to_add = 2
            elif weighted_score > 0.7:
                instances_to_add = 1
            else:
                instances_to_add = 1
            
            target_instances = min(current_instances + instances_to_add, max_instances)
            confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            return ScalingDecision(
                action=ScalingAction.SCALE_UP,
                reason=scale_up_reasons[0],  # Razón principal
                current_instances=current_instances,
                target_instances=target_instances,
                confidence=confidence,
                metrics=metrics,
                metadata={
                    "all_reasons": [r.value for r in scale_up_reasons],
                    "weighted_score": weighted_score,
                    "confidence_scores": confidence_scores
                }
            )
        
        return ScalingDecision(
            action=ScalingAction.NO_ACTION,
            reason=ScalingReason.MANUAL_TRIGGER,
            current_instances=current_instances,
            target_instances=current_instances,
            confidence=0.0,
            metrics=metrics
        )
    
    async def _evaluate_scale_down(
        self, 
        metrics: ScalingMetrics, 
        metrics_collector: MetricsCollector
    ) -> ScalingDecision:
        """Evalúa necesidad de scale down"""
        current_instances = metrics.active_instances
        min_instances = self.config["min_instances"]
        
        # No escalar si ya estamos en el mínimo
        if current_instances <= min_instances:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                reason=ScalingReason.MANUAL_TRIGGER,
                current_instances=current_instances,
                target_instances=current_instances,
                confidence=0.0,
                metrics=metrics,
                metadata={"reason": "min_instances_reached"}
            )
        
        # Evaluar si todas las métricas están por debajo del threshold de scale down
        cpu_low = metrics.cpu_utilization < SCALING_METRICS["cpu_utilization"]["scale_down_threshold"]
        memory_low = metrics.memory_utilization < SCALING_METRICS["memory_utilization"]["scale_down_threshold"]
        request_low = metrics.request_rate < SCALING_METRICS["request_rate"]["scale_down_threshold"]
        response_ok = metrics.response_time < SCALING_METRICS["response_time"]["scale_down_threshold"]
        
        # Verificar tendencias para evitar scale down prematuro
        cpu_trend = metrics_collector.get_metric_trend("cpu_utilization", 5)
        memory_trend = metrics_collector.get_metric_trend("memory_utilization", 5)
        
        # Solo scale down si las métricas están bajas Y las tendencias son estables/decrecientes
        stable_trends = cpu_trend["trend"] <= 5 and memory_trend["trend"] <= 5  # No incremento significativo
        
        if cpu_low and memory_low and request_low and response_ok and stable_trends:
            # Escalado conservador: -1 instancia
            target_instances = max(current_instances - 1, min_instances)
            
            # Confidence basado en qué tan bajas están las métricas
            cpu_confidence = max(0, (SCALING_METRICS["cpu_utilization"]["scale_down_threshold"] - metrics.cpu_utilization) / 100)
            memory_confidence = max(0, (SCALING_METRICS["memory_utilization"]["scale_down_threshold"] - metrics.memory_utilization) / 100)
            
            confidence = (cpu_confidence + memory_confidence) / 2
            
            return ScalingDecision(
                action=ScalingAction.SCALE_DOWN,
                reason=ScalingReason.LOW_UTILIZATION,
                current_instances=current_instances,
                target_instances=target_instances,
                confidence=confidence,
                metrics=metrics,
                metadata={
                    "cpu_trend": cpu_trend,
                    "memory_trend": memory_trend,
                    "stable_trends": stable_trends
                }
            )
        
        return ScalingDecision(
            action=ScalingAction.NO_ACTION,
            reason=ScalingReason.MANUAL_TRIGGER,
            current_instances=current_instances,
            target_instances=current_instances,
            confidence=0.0,
            metrics=metrics
        )
    
    async def _is_in_cooldown(self) -> bool:
        """Verifica si estamos en período de cooldown"""
        now = datetime.now()
        
        # Verificar cooldown de scale up
        if self.last_scale_up:
            scale_up_cooldown = timedelta(seconds=self.config["scale_up_cooldown"])
            if now - self.last_scale_up < scale_up_cooldown:
                return True
        
        # Verificar cooldown de scale down
        if self.last_scale_down:
            scale_down_cooldown = timedelta(seconds=self.config["scale_down_cooldown"])
            if now - self.last_scale_down < scale_down_cooldown:
                return True
        
        return False
    
    async def _get_cooldown_remaining(self) -> Dict[str, float]:
        """Obtiene tiempo restante de cooldown"""
        now = datetime.now()
        remaining = {"scale_up": 0.0, "scale_down": 0.0}
        
        if self.last_scale_up:
            scale_up_cooldown = timedelta(seconds=self.config["scale_up_cooldown"])
            time_since = now - self.last_scale_up
            if time_since < scale_up_cooldown:
                remaining["scale_up"] = (scale_up_cooldown - time_since).total_seconds()
        
        if self.last_scale_down:
            scale_down_cooldown = timedelta(seconds=self.config["scale_down_cooldown"])
            time_since = now - self.last_scale_down
            if time_since < scale_down_cooldown:
                remaining["scale_down"] = (scale_down_cooldown - time_since).total_seconds()
        
        return remaining
    
    def record_scaling_event(self, event: ScalingEvent):
        """Registra un evento de escalado"""
        self.scaling_history.append(event)
        
        # Actualizar timestamps de cooldown
        if event.decision.action == ScalingAction.SCALE_UP:
            self.last_scale_up = event.execution_start
        elif event.decision.action == ScalingAction.SCALE_DOWN:
            self.last_scale_down = event.execution_start
        
        # Limpiar historial antiguo
        if len(self.scaling_history) > 100:
            self.scaling_history = self.scaling_history[-100:]

# ===============================
# AUTO-SCALER SERVICE
# ===============================

class AutoScalerService:
    """
    Servicio de auto-scaling enterprise con:
    - Recolección de métricas en tiempo real
    - Decisiones de escalado inteligentes
    - Gestión de cooldown periods
    - Historial de eventos de escalado
    - Predicción basada en tendencias
    """
    
    def __init__(self):
        self.config = AS_CONFIG.copy()
        self.metrics_collector = MetricsCollector()
        self.scaling_policy = ScalingPolicy()
        
        # Estado del auto-scaler
        self.enabled = True
        self.current_instances = 1
        self.target_instances = 1
        
        # Estadísticas
        self.stats = {
            "total_evaluations": 0,
            "scale_up_events": 0,
            "scale_down_events": 0,
            "scaling_failures": 0,
            "last_evaluation": None,
            "last_scaling_event": None,
            "start_time": datetime.now()
        }
        
        # Tasks de background
        self._evaluation_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"📈 Auto-scaler Service inicializado para entorno: {ENVIRONMENT}")
    
    async def start(self):
        """Inicia el auto-scaler"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar loop de evaluación
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        
        logger.info("🚀 Auto-scaler Service iniciado")
    
    async def stop(self):
        """Detiene el auto-scaler"""
        self._running = False
        
        if self._evaluation_task and not self._evaluation_task.done():
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Auto-scaler Service detenido")
    
    async def _evaluation_loop(self):
        """Loop principal de evaluación de escalado"""
        while self._running:
            try:
                if self.enabled:
                    await self._evaluate_and_scale()
                
                await asyncio.sleep(self.config["evaluation_interval"])
                
            except Exception as e:
                logger.error(f"❌ Error en loop de evaluación: {e}")
                await asyncio.sleep(60)  # Esperar más tiempo si hay error
    
    async def _evaluate_and_scale(self):
        """Evalúa métricas y ejecuta escalado si es necesario"""
        try:
            self.stats["total_evaluations"] += 1
            self.stats["last_evaluation"] = datetime.now()
            
            # Recolectar métricas
            metrics = await self.metrics_collector.collect_all_metrics()
            
            # Evaluar decisión de escalado
            decision = await self.scaling_policy.evaluate_scaling_decision(
                metrics, self.metrics_collector
            )
            
            # Ejecutar escalado si es necesario
            if decision.action in [ScalingAction.SCALE_UP, ScalingAction.SCALE_DOWN]:
                await self._execute_scaling_decision(decision)
            
            logger.debug(f"Evaluación completada: {decision.action.value} (confianza: {decision.confidence:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Error en evaluación y escalado: {e}")
            self.stats["scaling_failures"] += 1
    
    async def _execute_scaling_decision(self, decision: ScalingDecision):
        """Ejecuta una decisión de escalado"""
        try:
            event_id = f"scale_{int(time.time())}"
            
            # Crear evento de escalado
            event = ScalingEvent(
                event_id=event_id,
                decision=decision,
                execution_start=datetime.now(),
                actual_instances_before=self.current_instances
            )
            
            logger.info(f"🔄 Ejecutando escalado: {decision.action.value} "
                       f"({decision.current_instances} → {decision.target_instances})")
            
            # Simular escalado (en producción sería llamada a orquestador)
            success = await self._simulate_scaling(decision)
            
            # Completar evento
            event.execution_end = datetime.now()
            event.success = success
            event.actual_instances_after = decision.target_instances if success else decision.current_instances
            
            if success:
                self.current_instances = decision.target_instances
                self.target_instances = decision.target_instances
                
                if decision.action == ScalingAction.SCALE_UP:
                    self.stats["scale_up_events"] += 1
                elif decision.action == ScalingAction.SCALE_DOWN:
                    self.stats["scale_down_events"] += 1
                
                self.stats["last_scaling_event"] = datetime.now()
                
                logger.info(f"✅ Escalado exitoso: {event.actual_instances_after} instancias activas")
            else:
                self.stats["scaling_failures"] += 1
                event.error_message = "Simulación de escalado falló"
                logger.error(f"❌ Escalado falló: {event.error_message}")
            
            # Registrar evento
            self.scaling_policy.record_scaling_event(event)
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando escalado: {e}")
            self.stats["scaling_failures"] += 1
    
    async def _simulate_scaling(self, decision: ScalingDecision) -> bool:
        """Simula escalado (en producción sería integración real)"""
        try:
            # Simular tiempo de escalado
            scaling_time = 2.0 if decision.action == ScalingAction.SCALE_UP else 1.0
            await asyncio.sleep(scaling_time)
            
            # Simular éxito (95% de probabilidad)
            import random
            return random.random() > 0.05
            
        except Exception as e:
            logger.error(f"❌ Error en simulación de escalado: {e}")
            return False
    
    # ===============================
    # GESTIÓN MANUAL
    # ===============================
    
    async def manual_scale(self, target_instances: int, reason: str = "manual") -> bool:
        """Escalado manual"""
        try:
            if target_instances < self.config["min_instances"] or target_instances > self.config["max_instances"]:
                logger.error(f"Target instances {target_instances} fuera de rango "
                           f"({self.config['min_instances']}-{self.config['max_instances']})")
                return False
            
            # Crear decisión manual
            current_metrics = await self.metrics_collector.collect_all_metrics()
            
            action = ScalingAction.SCALE_UP if target_instances > self.current_instances else ScalingAction.SCALE_DOWN
            if target_instances == self.current_instances:
                action = ScalingAction.NO_ACTION
            
            decision = ScalingDecision(
                action=action,
                reason=ScalingReason.MANUAL_TRIGGER,
                current_instances=self.current_instances,
                target_instances=target_instances,
                confidence=1.0,
                metrics=current_metrics,
                metadata={"manual_reason": reason}
            )
            
            # Ejecutar escalado
            if action != ScalingAction.NO_ACTION:
                await self._execute_scaling_decision(decision)
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en escalado manual: {e}")
            return False
    
    def enable_auto_scaling(self):
        """Habilita auto-scaling"""
        self.enabled = True
        logger.info("✅ Auto-scaling habilitado")
    
    def disable_auto_scaling(self):
        """Deshabilita auto-scaling"""
        self.enabled = False
        logger.info("⏸️ Auto-scaling deshabilitado")
    
    # ===============================
    # MÉTRICAS Y ESTADÍSTICAS
    # ===============================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del auto-scaler"""
        uptime = datetime.now() - self.stats["start_time"]
        
        # Calcular eficiencia
        total_scaling_events = self.stats["scale_up_events"] + self.stats["scale_down_events"]
        success_rate = 0.0
        if total_scaling_events > 0:
            success_rate = ((total_scaling_events - self.stats["scaling_failures"]) / total_scaling_events) * 100
        
        # Estadísticas de cooldown
        cooldown_remaining = asyncio.create_task(self.scaling_policy._get_cooldown_remaining())
        
        return {
            "auto_scaler": {
                "enabled": self.enabled,
                "current_instances": self.current_instances,
                "target_instances": self.target_instances,
                "uptime_seconds": uptime.total_seconds()
            },
            "configuration": {
                "min_instances": self.config["min_instances"],
                "max_instances": self.config["max_instances"],
                "scale_up_threshold": self.config["scale_up_threshold"],
                "scale_down_threshold": self.config["scale_down_threshold"],
                "evaluation_interval": self.config["evaluation_interval"]
            },
            "performance": {
                "total_evaluations": self.stats["total_evaluations"],
                "scale_up_events": self.stats["scale_up_events"],
                "scale_down_events": self.stats["scale_down_events"],
                "scaling_failures": self.stats["scaling_failures"],
                "success_rate": round(success_rate, 2),
                "evaluations_per_minute": self.stats["total_evaluations"] / max(uptime.total_seconds() / 60, 1)
            },
            "recent_activity": {
                "last_evaluation": self.stats["last_evaluation"].isoformat() if self.stats["last_evaluation"] else None,
                "last_scaling_event": self.stats["last_scaling_event"].isoformat() if self.stats["last_scaling_event"] else None,
                "recent_events": len([e for e in self.scaling_policy.scaling_history if 
                                    (datetime.now() - e.execution_start).total_seconds() < 3600])  # Última hora
            },
            "scaling_history": [
                {
                    "event_id": event.event_id,
                    "action": event.decision.action.value,
                    "reason": event.decision.reason.value,
                    "instances_before": event.actual_instances_before,
                    "instances_after": event.actual_instances_after,
                    "success": event.success,
                    "timestamp": event.execution_start.isoformat()
                }
                for event in self.scaling_policy.scaling_history[-10:]  # Últimos 10 eventos
            ]
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del auto-scaler
auto_scaler = AutoScalerService()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_auto_scaler():
    """Inicializa el auto-scaler"""
    await auto_scaler.start()

async def manual_scale_instances(target_instances: int, reason: str = "manual") -> bool:
    """Escalado manual de instancias"""
    return await auto_scaler.manual_scale(target_instances, reason)

def enable_auto_scaling():
    """Habilita auto-scaling"""
    auto_scaler.enable_auto_scaling()

def disable_auto_scaling():
    """Deshabilita auto-scaling"""
    auto_scaler.disable_auto_scaling()

async def get_current_metrics() -> ScalingMetrics:
    """Obtiene métricas actuales"""
    return await auto_scaler.metrics_collector.collect_all_metrics()

def get_auto_scaler_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del auto-scaler"""
    return auto_scaler.get_stats()

async def stop_auto_scaler():
    """Detiene el auto-scaler"""
    await auto_scaler.stop() 