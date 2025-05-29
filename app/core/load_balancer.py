"""
⚖️ Load Balancer Manager Enterprise
Gestor de load balancing con múltiples algoritmos y health monitoring
"""
import asyncio
import time
import random
import logging
import hashlib
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import os
import psutil
import uuid

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN LOAD BALANCER
# ===============================

# Configuración por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

LOAD_BALANCER_CONFIG = {
    "production": {
        "algorithm": "weighted_round_robin",
        "health_check": {
            "interval": 30,
            "timeout": 5,
            "retries": 3,
            "endpoint": "/health"
        },
        "sticky_sessions": {
            "enabled": True,
            "cookie_name": "AGENTE_VENDEDOR_SESSION",
            "ttl": 3600
        },
        "rate_limiting": {
            "requests_per_minute": 1000,
            "burst_size": 100
        },
        "circuit_breaker": {
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "half_open_max_calls": 3
        }
    },
    "staging": {
        "algorithm": "least_connections",
        "health_check": {
            "interval": 45,
            "timeout": 3,
            "retries": 2,
            "endpoint": "/health"
        },
        "sticky_sessions": {
            "enabled": True,
            "cookie_name": "AGENTE_VENDEDOR_SESSION",
            "ttl": 1800
        },
        "rate_limiting": {
            "requests_per_minute": 500,
            "burst_size": 50
        },
        "circuit_breaker": {
            "failure_threshold": 3,
            "recovery_timeout": 30,
            "half_open_max_calls": 2
        }
    },
    "development": {
        "algorithm": "round_robin",
        "health_check": {
            "interval": 60,
            "timeout": 2,
            "retries": 1,
            "endpoint": "/health"
        },
        "sticky_sessions": {
            "enabled": False,
            "cookie_name": "AGENTE_VENDEDOR_SESSION",
            "ttl": 900
        },
        "rate_limiting": {
            "requests_per_minute": 100,
            "burst_size": 20
        },
        "circuit_breaker": {
            "failure_threshold": 2,
            "recovery_timeout": 15,
            "half_open_max_calls": 1
        }
    }
}

# Configuración actual
LB_CONFIG = LOAD_BALANCER_CONFIG.get(ENVIRONMENT, LOAD_BALANCER_CONFIG["development"])

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class LoadBalancingAlgorithm(Enum):
    """Algoritmos de load balancing disponibles"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_LEAST_CONNECTIONS = "weighted_least_connections"
    RESPONSE_TIME = "response_time"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"

class InstanceStatus(Enum):
    """Estados de instancia"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"

class CircuitBreakerState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class ServiceInstance:
    """Instancia de servicio en el load balancer"""
    instance_id: str
    host: str
    port: int
    weight: float = 1.0
    status: InstanceStatus = InstanceStatus.UNKNOWN
    
    # Métricas de performance
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_response_time: float = 0.0
    
    # Health check
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    # Metadata
    capabilities: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    region: str = "default"
    zone: str = "default"
    
    # Timestamps
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def is_healthy(self) -> bool:
        """Verifica si la instancia está saludable"""
        return self.status == InstanceStatus.HEALTHY
    
    @property
    def success_rate(self) -> float:
        """Calcula tasa de éxito de requests"""
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100
    
    @property
    def load_score(self) -> float:
        """Calcula score de carga (menor es mejor)"""
        # Combina conexiones activas, tiempo de respuesta y tasa de error
        connection_factor = self.active_connections / max(self.weight, 1)
        response_factor = self.avg_response_time / 1000  # Normalizar a segundos
        error_factor = (self.failed_requests / max(self.total_requests, 1)) * 10
        
        return connection_factor + response_factor + error_factor
    
    def update_metrics(self, response_time: float, success: bool):
        """Actualiza métricas de la instancia"""
        self.total_requests += 1
        self.last_response_time = response_time
        
        if not success:
            self.failed_requests += 1
        
        # Actualizar promedio de tiempo de respuesta (moving average)
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * 0.9) + (response_time * 0.1)
        
        self.last_seen = datetime.now()

@dataclass
class LoadBalancerRequest:
    """Request para load balancing"""
    request_id: str
    client_ip: str
    path: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def ip_hash(self) -> int:
        """Hash del IP para IP-based routing"""
        return hash(self.client_ip)

@dataclass
class CircuitBreaker:
    """Circuit breaker para una instancia"""
    instance_id: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.failure_threshold = LB_CONFIG["circuit_breaker"]["failure_threshold"]
        self.recovery_timeout = LB_CONFIG["circuit_breaker"]["recovery_timeout"]
        self.half_open_max_calls = LB_CONFIG["circuit_breaker"]["half_open_max_calls"]
    
    def record_success(self):
        """Registra una llamada exitosa"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Registra una llamada fallida"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Verifica si se puede ejecutar una llamada"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False

# ===============================
# ALGORITMOS DE LOAD BALANCING
# ===============================

class LoadBalancingStrategy:
    """Clase base para estrategias de load balancing"""
    
    def __init__(self, name: str):
        self.name = name
        self.state = {}
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        """Selecciona una instancia según el algoritmo"""
        raise NotImplementedError

class RoundRobinStrategy(LoadBalancingStrategy):
    """Estrategia Round Robin simple"""
    
    def __init__(self):
        super().__init__("round_robin")
        self.current_index = 0
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        # Filtrar solo instancias saludables
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        # Round robin
        selected = healthy_instances[self.current_index % len(healthy_instances)]
        self.current_index += 1
        
        return selected

class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Estrategia Round Robin Ponderado"""
    
    def __init__(self):
        super().__init__("weighted_round_robin")
        self.current_weights = {}
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        # Implementar Weighted Round Robin
        total_weight = sum(instance.weight for instance in healthy_instances)
        if total_weight == 0:
            return healthy_instances[0]
        
        # Encontrar instancia con mayor peso efectivo
        best_instance = None
        best_current_weight = -1
        
        for instance in healthy_instances:
            current_weight = self.current_weights.get(instance.instance_id, 0)
            current_weight += instance.weight
            
            if current_weight > best_current_weight:
                best_current_weight = current_weight
                best_instance = instance
            
            self.current_weights[instance.instance_id] = current_weight
        
        # Reducir peso de la instancia seleccionada
        if best_instance:
            self.current_weights[best_instance.instance_id] -= total_weight
        
        return best_instance

class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Estrategia Least Connections"""
    
    def __init__(self):
        super().__init__("least_connections")
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        # Seleccionar instancia con menos conexiones activas
        return min(healthy_instances, key=lambda x: x.active_connections / max(x.weight, 1))

class ResponseTimeStrategy(LoadBalancingStrategy):
    """Estrategia basada en tiempo de respuesta"""
    
    def __init__(self):
        super().__init__("response_time")
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        # Seleccionar instancia con mejor tiempo de respuesta
        return min(healthy_instances, key=lambda x: x.avg_response_time)

class IPHashStrategy(LoadBalancingStrategy):
    """Estrategia IP Hash para sticky sessions"""
    
    def __init__(self):
        super().__init__("ip_hash")
    
    async def select_instance(
        self, 
        instances: List[ServiceInstance], 
        request: LoadBalancerRequest
    ) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        # Hash del IP para consistencia
        ip_hash = abs(hash(request.client_ip))
        index = ip_hash % len(healthy_instances)
        
        return healthy_instances[index]

# ===============================
# LOAD BALANCER MANAGER
# ===============================

class LoadBalancerManager:
    """
    Gestor de load balancing enterprise con:
    - Múltiples algoritmos de balanceo
    - Health checking automático
    - Circuit breaker pattern
    - Sticky sessions
    - Rate limiting
    - Métricas avanzadas
    """
    
    def __init__(self):
        self.config = LB_CONFIG.copy()
        self.instances: Dict[str, ServiceInstance] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Estrategias de load balancing
        self.strategies = {
            LoadBalancingAlgorithm.ROUND_ROBIN: RoundRobinStrategy(),
            LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy(),
            LoadBalancingAlgorithm.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
            LoadBalancingAlgorithm.RESPONSE_TIME: ResponseTimeStrategy(),
            LoadBalancingAlgorithm.IP_HASH: IPHashStrategy()
        }
        
        # Configurar algoritmo actual
        algorithm_name = self.config["algorithm"]
        self.current_algorithm = LoadBalancingAlgorithm(algorithm_name)
        self.current_strategy = self.strategies[self.current_algorithm]
        
        # Sticky sessions
        self.session_store: Dict[str, str] = {}  # session_id -> instance_id
        
        # Rate limiting
        self.rate_limiter: Dict[str, List[float]] = {}  # client_ip -> timestamps
        
        # Métricas
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "requests_per_instance": {},
            "algorithm_switches": 0,
            "circuit_breaker_trips": 0,
            "rate_limit_hits": 0,
            "sticky_session_hits": 0,
            "start_time": datetime.now()
        }
        
        # Health monitoring
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"⚖️ Load Balancer Manager inicializado con algoritmo: {algorithm_name}")
    
    async def start(self):
        """Inicia el load balancer"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar health monitoring
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        logger.info("🚀 Load Balancer Manager iniciado")
    
    async def stop(self):
        """Detiene el load balancer"""
        self._running = False
        
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Load Balancer Manager detenido")
    
    # ===============================
    # GESTIÓN DE INSTANCIAS
    # ===============================
    
    async def register_instance(self, instance: ServiceInstance) -> bool:
        """Registra nueva instancia en el balanceador"""
        try:
            instance_id = instance.instance_id
            
            # Verificar si ya existe
            if instance_id in self.instances:
                logger.warning(f"Instancia {instance_id} ya registrada, actualizando...")
            
            # Registrar instancia
            self.instances[instance_id] = instance
            
            # Crear circuit breaker
            self.circuit_breakers[instance_id] = CircuitBreaker(instance_id)
            
            # Inicializar métricas
            self.stats["requests_per_instance"][instance_id] = 0
            
            logger.info(f"✅ Instancia registrada: {instance_id} ({instance.host}:{instance.port})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registrando instancia: {e}")
            return False
    
    async def deregister_instance(self, instance_id: str) -> bool:
        """Desregistra instancia del balanceador"""
        try:
            if instance_id not in self.instances:
                logger.warning(f"Instancia {instance_id} no encontrada")
                return False
            
            # Marcar como draining primero
            self.instances[instance_id].status = InstanceStatus.DRAINING
            
            # Esperar que terminen las conexiones activas (timeout)
            timeout = 30  # segundos
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                if self.instances[instance_id].active_connections == 0:
                    break
                await asyncio.sleep(1)
            
            # Remover instancia
            del self.instances[instance_id]
            del self.circuit_breakers[instance_id]
            
            # Limpiar sticky sessions
            sessions_to_remove = [
                session_id for session_id, inst_id in self.session_store.items()
                if inst_id == instance_id
            ]
            for session_id in sessions_to_remove:
                del self.session_store[session_id]
            
            logger.info(f"✅ Instancia desregistrada: {instance_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error desregistrando instancia: {e}")
            return False
    
    async def update_instance_weight(self, instance_id: str, weight: float) -> bool:
        """Actualiza peso de instancia basado en métricas"""
        try:
            if instance_id not in self.instances:
                return False
            
            # Validar peso
            weight = max(0.1, min(10.0, weight))  # Entre 0.1 y 10.0
            
            old_weight = self.instances[instance_id].weight
            self.instances[instance_id].weight = weight
            
            logger.debug(f"Peso actualizado para {instance_id}: {old_weight} → {weight}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando peso: {e}")
            return False
    
    async def get_healthy_instances(self) -> List[ServiceInstance]:
        """Obtiene lista de instancias saludables"""
        healthy = []
        
        for instance in self.instances.values():
            # Verificar estado de salud
            if instance.is_healthy:
                # Verificar circuit breaker
                circuit_breaker = self.circuit_breakers.get(instance.instance_id)
                if circuit_breaker and circuit_breaker.can_execute():
                    healthy.append(instance)
        
        return healthy
    
    # ===============================
    # DISTRIBUCIÓN DE REQUESTS
    # ===============================
    
    async def distribute_request(self, request: LoadBalancerRequest) -> Optional[ServiceInstance]:
        """Distribuye request según algoritmo configurado"""
        try:
            self.stats["total_requests"] += 1
            
            # 1. Verificar rate limiting
            if not await self._check_rate_limit(request.client_ip):
                self.stats["rate_limit_hits"] += 1
                logger.warning(f"Rate limit excedido para IP: {request.client_ip}")
                return None
            
            # 2. Verificar sticky sessions
            if self.config["sticky_sessions"]["enabled"] and request.session_id:
                sticky_instance = await self._get_sticky_session_instance(request.session_id)
                if sticky_instance:
                    self.stats["sticky_session_hits"] += 1
                    return sticky_instance
            
            # 3. Obtener instancias saludables
            healthy_instances = await self.get_healthy_instances()
            if not healthy_instances:
                logger.warning("No hay instancias saludables disponibles")
                return None
            
            # 4. Aplicar algoritmo de load balancing
            selected_instance = await self.current_strategy.select_instance(
                healthy_instances, request
            )
            
            if selected_instance:
                # Actualizar métricas
                selected_instance.active_connections += 1
                self.stats["requests_per_instance"][selected_instance.instance_id] += 1
                
                # Actualizar sticky session si está habilitado
                if self.config["sticky_sessions"]["enabled"] and request.session_id:
                    await self._set_sticky_session(request.session_id, selected_instance.instance_id)
            
            return selected_instance
            
        except Exception as e:
            logger.error(f"❌ Error distribuyendo request: {e}")
            self.stats["failed_requests"] += 1
            return None
    
    async def complete_request(
        self, 
        instance: ServiceInstance, 
        response_time: float, 
        success: bool
    ):
        """Completa un request y actualiza métricas"""
        try:
            # Actualizar conexiones activas
            instance.active_connections = max(0, instance.active_connections - 1)
            
            # Actualizar métricas de instancia
            instance.update_metrics(response_time, success)
            
            # Actualizar circuit breaker
            circuit_breaker = self.circuit_breakers.get(instance.instance_id)
            if circuit_breaker:
                if success:
                    circuit_breaker.record_success()
                else:
                    circuit_breaker.record_failure()
                    if circuit_breaker.state == CircuitBreakerState.OPEN:
                        self.stats["circuit_breaker_trips"] += 1
            
            # Actualizar estadísticas globales
            if success:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error completando request: {e}")
    
    # ===============================
    # STICKY SESSIONS
    # ===============================
    
    async def _get_sticky_session_instance(self, session_id: str) -> Optional[ServiceInstance]:
        """Obtiene instancia para sticky session"""
        instance_id = self.session_store.get(session_id)
        if not instance_id:
            return None
        
        instance = self.instances.get(instance_id)
        if not instance or not instance.is_healthy:
            # Limpiar sesión inválida
            del self.session_store[session_id]
            return None
        
        # Verificar circuit breaker
        circuit_breaker = self.circuit_breakers.get(instance_id)
        if circuit_breaker and not circuit_breaker.can_execute():
            return None
        
        return instance
    
    async def _set_sticky_session(self, session_id: str, instance_id: str):
        """Establece sticky session"""
        self.session_store[session_id] = instance_id
        
        # Limpiar sesiones expiradas periódicamente
        if len(self.session_store) > 10000:  # Límite de sesiones
            await self._cleanup_expired_sessions()
    
    async def _cleanup_expired_sessions(self):
        """Limpia sesiones expiradas"""
        # Implementación simplificada - en producción usar TTL
        if len(self.session_store) > 5000:
            # Remover 20% de sesiones más antiguas
            sessions_to_remove = list(self.session_store.keys())[:len(self.session_store) // 5]
            for session_id in sessions_to_remove:
                del self.session_store[session_id]
    
    # ===============================
    # RATE LIMITING
    # ===============================
    
    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Verifica rate limiting para un cliente"""
        now = time.time()
        window = 60  # 1 minuto
        max_requests = self.config["rate_limiting"]["requests_per_minute"]
        
        # Obtener timestamps de requests del cliente
        if client_ip not in self.rate_limiter:
            self.rate_limiter[client_ip] = []
        
        timestamps = self.rate_limiter[client_ip]
        
        # Limpiar timestamps antiguos
        timestamps[:] = [ts for ts in timestamps if now - ts < window]
        
        # Verificar límite
        if len(timestamps) >= max_requests:
            return False
        
        # Añadir timestamp actual
        timestamps.append(now)
        
        return True
    
    # ===============================
    # HEALTH MONITORING
    # ===============================
    
    async def _health_monitor_loop(self):
        """Loop de monitoreo de salud"""
        while self._running:
            try:
                await self._check_all_instances_health()
                await asyncio.sleep(self.config["health_check"]["interval"])
            except Exception as e:
                logger.error(f"❌ Error en health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_instances_health(self):
        """Verifica salud de todas las instancias"""
        for instance in list(self.instances.values()):
            await self._check_instance_health(instance)
    
    async def _check_instance_health(self, instance: ServiceInstance):
        """Verifica salud de una instancia específica"""
        try:
            # Simulación de health check (en producción sería HTTP request)
            # Por ahora, marcar como saludable si no hay muchos errores
            
            if instance.total_requests > 0:
                error_rate = (instance.failed_requests / instance.total_requests) * 100
                
                if error_rate > 50:  # Más del 50% de errores
                    instance.status = InstanceStatus.UNHEALTHY
                    instance.consecutive_failures += 1
                else:
                    instance.status = InstanceStatus.HEALTHY
                    instance.consecutive_successes += 1
                    instance.consecutive_failures = 0
            else:
                # Sin requests, asumir saludable
                instance.status = InstanceStatus.HEALTHY
            
            instance.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Error verificando salud de {instance.instance_id}: {e}")
            instance.status = InstanceStatus.UNHEALTHY
            instance.consecutive_failures += 1
    
    # ===============================
    # GESTIÓN DE ALGORITMOS
    # ===============================
    
    async def switch_algorithm(self, algorithm: LoadBalancingAlgorithm) -> bool:
        """Cambia algoritmo de load balancing"""
        try:
            if algorithm not in self.strategies:
                logger.error(f"Algoritmo no soportado: {algorithm}")
                return False
            
            old_algorithm = self.current_algorithm
            self.current_algorithm = algorithm
            self.current_strategy = self.strategies[algorithm]
            self.stats["algorithm_switches"] += 1
            
            logger.info(f"🔄 Algoritmo cambiado: {old_algorithm.value} → {algorithm.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cambiando algoritmo: {e}")
            return False
    
    # ===============================
    # MÉTRICAS Y ESTADÍSTICAS
    # ===============================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del load balancer"""
        uptime = datetime.now() - self.stats["start_time"]
        total_requests = self.stats["total_requests"]
        
        # Calcular métricas derivadas
        success_rate = 0.0
        if total_requests > 0:
            success_rate = (self.stats["successful_requests"] / total_requests) * 100
        
        # Estadísticas de instancias
        instance_stats = {}
        for instance_id, instance in self.instances.items():
            circuit_breaker = self.circuit_breakers.get(instance_id)
            
            instance_stats[instance_id] = {
                "status": instance.status.value,
                "weight": instance.weight,
                "active_connections": instance.active_connections,
                "total_requests": instance.total_requests,
                "success_rate": instance.success_rate,
                "avg_response_time": instance.avg_response_time,
                "load_score": instance.load_score,
                "circuit_breaker_state": circuit_breaker.state.value if circuit_breaker else "unknown",
                "last_health_check": instance.last_health_check.isoformat() if instance.last_health_check else None
            }
        
        return {
            "load_balancer": {
                "algorithm": self.current_algorithm.value,
                "total_instances": len(self.instances),
                "healthy_instances": len([i for i in self.instances.values() if i.is_healthy]),
                "uptime_seconds": uptime.total_seconds()
            },
            "performance": {
                "total_requests": total_requests,
                "successful_requests": self.stats["successful_requests"],
                "failed_requests": self.stats["failed_requests"],
                "success_rate": round(success_rate, 2),
                "requests_per_second": total_requests / max(uptime.total_seconds(), 1)
            },
            "features": {
                "sticky_session_hits": self.stats["sticky_session_hits"],
                "rate_limit_hits": self.stats["rate_limit_hits"],
                "circuit_breaker_trips": self.stats["circuit_breaker_trips"],
                "algorithm_switches": self.stats["algorithm_switches"]
            },
            "instances": instance_stats,
            "configuration": {
                "sticky_sessions_enabled": self.config["sticky_sessions"]["enabled"],
                "rate_limiting_enabled": True,
                "circuit_breaker_enabled": True,
                "health_check_interval": self.config["health_check"]["interval"]
            }
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del load balancer
load_balancer = LoadBalancerManager()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_load_balancer():
    """Inicializa el load balancer"""
    await load_balancer.start()

async def register_service_instance(
    instance_id: str,
    host: str,
    port: int,
    weight: float = 1.0,
    capabilities: List[str] = None
) -> bool:
    """Registra una instancia de servicio"""
    instance = ServiceInstance(
        instance_id=instance_id,
        host=host,
        port=port,
        weight=weight,
        capabilities=capabilities or [],
        status=InstanceStatus.HEALTHY
    )
    return await load_balancer.register_instance(instance)

async def distribute_request_to_instance(
    client_ip: str,
    path: str,
    method: str = "GET",
    session_id: str = None,
    headers: Dict[str, str] = None
) -> Optional[ServiceInstance]:
    """Distribuye un request a una instancia"""
    request = LoadBalancerRequest(
        request_id=str(uuid.uuid4()),
        client_ip=client_ip,
        path=path,
        method=method,
        session_id=session_id,
        headers=headers or {}
    )
    return await load_balancer.distribute_request(request)

async def complete_service_request(
    instance: ServiceInstance,
    response_time: float,
    success: bool = True
):
    """Completa un request de servicio"""
    await load_balancer.complete_request(instance, response_time, success)

def get_load_balancer_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del load balancer"""
    return load_balancer.get_stats()

async def stop_load_balancer():
    """Detiene el load balancer"""
    await load_balancer.stop() 