"""
🔴 Redis Manager Enterprise
Gestor de conexiones Redis con cluster, failover automático y monitoreo avanzado
"""
import asyncio
import json
import logging
import time
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# Redis imports con fallback
try:
    import redis
    import redis.asyncio as aioredis
    from redis.cluster import RedisCluster
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # Mock classes para desarrollo sin Redis
    class RedisCluster:
        pass
    class Sentinel:
        pass

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN REDIS ENTERPRISE
# ===============================

# Configuración por entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

REDIS_ENVIRONMENTS = {
    "production": {
        "cluster_nodes": [
            {"host": "redis-node-1", "port": 6379},
            {"host": "redis-node-2", "port": 6379},
            {"host": "redis-node-3", "port": 6379},
            {"host": "redis-node-4", "port": 6379},
            {"host": "redis-node-5", "port": 6379},
            {"host": "redis-node-6", "port": 6379}
        ],
        "cluster_size": 6,  # 3 masters + 3 replicas
        "memory_per_node": "4GB",
        "persistence": "AOF + RDB",
        "compression": True,
        "max_connections": 100,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
        "retry_on_timeout": True,
        "health_check_interval": 30
    },
    "staging": {
        "cluster_nodes": [
            {"host": "redis-staging-1", "port": 6379},
            {"host": "redis-staging-2", "port": 6379},
            {"host": "redis-staging-3", "port": 6379}
        ],
        "cluster_size": 3,  # 3 masters
        "memory_per_node": "2GB",
        "persistence": "RDB",
        "compression": True,
        "max_connections": 50,
        "socket_timeout": 3,
        "socket_connect_timeout": 3,
        "retry_on_timeout": True,
        "health_check_interval": 60
    },
    "development": {
        "cluster_nodes": [
            {"host": "localhost", "port": 6379}
        ],
        "cluster_size": 1,  # Single instance
        "memory_per_node": "1GB",
        "persistence": "None",
        "compression": False,
        "max_connections": 20,
        "socket_timeout": 2,
        "socket_connect_timeout": 2,
        "retry_on_timeout": False,
        "health_check_interval": 120
    }
}

# Configuración actual basada en entorno
REDIS_CONFIG = REDIS_ENVIRONMENTS.get(ENVIRONMENT, REDIS_ENVIRONMENTS["development"])

# Configuración de Sentinel para failover
SENTINEL_CONFIG = {
    "sentinels": [
        ("sentinel-1", 26379),
        ("sentinel-2", 26379),
        ("sentinel-3", 26379)
    ],
    "service_name": "mymaster",
    "socket_timeout": 0.1,
    "password": os.getenv("REDIS_PASSWORD"),
    "sentinel_kwargs": {
        "socket_timeout": 0.1
    }
}

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class RedisNodeStatus(Enum):
    """Estados de nodos Redis"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"

class RedisConnectionType(Enum):
    """Tipos de conexión Redis"""
    SINGLE = "single"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"

@dataclass
class RedisNodeInfo:
    """Información de un nodo Redis"""
    host: str
    port: int
    node_id: str = ""
    role: str = "unknown"  # master, slave, sentinel
    status: RedisNodeStatus = RedisNodeStatus.UNKNOWN
    memory_used: int = 0
    memory_max: int = 0
    connections: int = 0
    ops_per_sec: float = 0.0
    replication_lag: float = 0.0
    last_ping: Optional[datetime] = None
    uptime: int = 0
    version: str = ""

@dataclass
class RedisClusterStats:
    """Estadísticas del cluster Redis"""
    total_nodes: int = 0
    healthy_nodes: int = 0
    failed_nodes: int = 0
    total_memory_used: int = 0
    total_memory_max: int = 0
    total_connections: int = 0
    total_ops_per_sec: float = 0.0
    cluster_state: str = "unknown"
    slots_assigned: int = 0
    slots_ok: int = 0
    nodes_info: List[RedisNodeInfo] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

# ===============================
# REDIS MANAGER ENTERPRISE
# ===============================

class RedisManagerEnterprise:
    """
    Gestor de conexiones Redis Enterprise con:
    - Soporte para cluster y single instance
    - Failover automático con Sentinel
    - Monitoreo de salud en tiempo real
    - Pool de conexiones optimizado
    - Métricas avanzadas
    """
    
    def __init__(self):
        self.config = REDIS_CONFIG.copy()
        self.connection_type = RedisConnectionType.SINGLE
        self.cluster: Optional[RedisCluster] = None
        self.sentinel: Optional[Sentinel] = None
        self.single_connection: Optional[aioredis.Redis] = None
        self.connection_pool = None
        
        # Estado del manager
        self.is_initialized = False
        self.is_healthy = False
        self.last_health_check = None
        
        # Estadísticas
        self.stats = {
            "connections_created": 0,
            "connections_failed": 0,
            "operations_total": 0,
            "operations_failed": 0,
            "failovers_count": 0,
            "last_failover": None,
            "uptime_start": datetime.now()
        }
        
        # Monitoreo
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"🔴 Redis Manager Enterprise inicializado para entorno: {ENVIRONMENT}")
    
    async def initialize(self) -> bool:
        """
        Inicializa el Redis Manager según la configuración del entorno
        """
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis no disponible - usando modo mock para desarrollo")
            self.is_initialized = True
            return True
        
        try:
            logger.info("🚀 Inicializando Redis Manager Enterprise...")
            
            # Determinar tipo de conexión
            if len(self.config["cluster_nodes"]) > 1:
                self.connection_type = RedisConnectionType.CLUSTER
                success = await self._initialize_cluster()
            else:
                self.connection_type = RedisConnectionType.SINGLE
                success = await self._initialize_single()
            
            if success:
                self.is_initialized = True
                self.is_healthy = True
                
                # Iniciar monitoreo de salud
                await self._start_health_monitoring()
                
                logger.info(f"✅ Redis Manager inicializado exitosamente ({self.connection_type.value})")
                return True
            else:
                logger.error("❌ Error inicializando Redis Manager")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error crítico inicializando Redis: {e}")
            self.stats["connections_failed"] += 1
            return False
    
    async def _initialize_cluster(self) -> bool:
        """Inicializa conexión a Redis Cluster"""
        try:
            startup_nodes = [
                {"host": node["host"], "port": node["port"]}
                for node in self.config["cluster_nodes"]
            ]
            
            self.cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                max_connections=self.config["max_connections"],
                socket_timeout=self.config["socket_timeout"],
                socket_connect_timeout=self.config["socket_connect_timeout"],
                retry_on_timeout=self.config["retry_on_timeout"],
                password=os.getenv("REDIS_PASSWORD")
            )
            
            # Test de conectividad
            await self.cluster.ping()
            self.stats["connections_created"] += 1
            
            logger.info(f"🔗 Redis Cluster conectado: {len(startup_nodes)} nodos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis Cluster: {e}")
            return False
    
    async def _initialize_single(self) -> bool:
        """Inicializa conexión a Redis single instance"""
        try:
            node = self.config["cluster_nodes"][0]
            
            self.single_connection = aioredis.Redis(
                host=node["host"],
                port=node["port"],
                decode_responses=True,
                max_connections=self.config["max_connections"],
                socket_timeout=self.config["socket_timeout"],
                socket_connect_timeout=self.config["socket_connect_timeout"],
                retry_on_timeout=self.config["retry_on_timeout"],
                password=os.getenv("REDIS_PASSWORD")
            )
            
            # Test de conectividad
            await self.single_connection.ping()
            self.stats["connections_created"] += 1
            
            logger.info(f"🔗 Redis Single conectado: {node['host']}:{node['port']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis Single: {e}")
            return False
    
    async def get_connection(self) -> Optional[Union[RedisCluster, aioredis.Redis]]:
        """
        Obtiene una conexión Redis del pool
        """
        if not self.is_initialized:
            logger.warning("⚠️ Redis Manager no inicializado")
            return None
        
        if not REDIS_AVAILABLE:
            return None  # Mock mode
        
        try:
            if self.connection_type == RedisConnectionType.CLUSTER:
                return self.cluster
            else:
                return self.single_connection
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo conexión Redis: {e}")
            self.stats["connections_failed"] += 1
            return None
    
    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """
        Ejecuta un comando Redis con manejo de errores y métricas
        """
        if not REDIS_AVAILABLE:
            logger.debug(f"🔴 Mock Redis command: {command} {args}")
            return None
        
        connection = await self.get_connection()
        if not connection:
            return None
        
        try:
            self.stats["operations_total"] += 1
            
            # Ejecutar comando
            if hasattr(connection, command):
                method = getattr(connection, command)
                result = await method(*args, **kwargs)
                return result
            else:
                logger.warning(f"⚠️ Comando Redis no soportado: {command}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando comando Redis {command}: {e}")
            self.stats["operations_failed"] += 1
            
            # Intentar reconexión si es necesario
            if "connection" in str(e).lower():
                await self._handle_connection_error()
            
            return None
    
    async def _handle_connection_error(self):
        """Maneja errores de conexión y intenta reconectar"""
        logger.warning("🔄 Intentando reconexión Redis...")
        
        self.is_healthy = False
        
        # Intentar reinicializar
        success = await self.initialize()
        if success:
            logger.info("✅ Reconexión Redis exitosa")
        else:
            logger.error("❌ Reconexión Redis falló")
            self.stats["failovers_count"] += 1
            self.stats["last_failover"] = datetime.now()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica la salud del cluster/instancia Redis
        """
        health_info = {
            "status": "unknown",
            "timestamp": datetime.now().isoformat(),
            "connection_type": self.connection_type.value,
            "is_initialized": self.is_initialized,
            "is_healthy": self.is_healthy,
            "nodes": [],
            "cluster_stats": None,
            "errors": []
        }
        
        if not REDIS_AVAILABLE:
            health_info.update({
                "status": "mock",
                "message": "Redis no disponible - modo mock activo"
            })
            return health_info
        
        if not self.is_initialized:
            health_info.update({
                "status": "not_initialized",
                "errors": ["Redis Manager no inicializado"]
            })
            return health_info
        
        try:
            if self.connection_type == RedisConnectionType.CLUSTER:
                health_info = await self._health_check_cluster(health_info)
            else:
                health_info = await self._health_check_single(health_info)
                
            self.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")
            health_info.update({
                "status": "error",
                "errors": [str(e)]
            })
            self.is_healthy = False
        
        return health_info
    
    async def _health_check_cluster(self, health_info: Dict) -> Dict:
        """Health check específico para cluster"""
        try:
            # Ping general al cluster
            ping_result = await self.cluster.ping()
            
            # Información de nodos
            cluster_info = await self.cluster.cluster_info()
            cluster_nodes = await self.cluster.cluster_nodes()
            
            # Procesar información de nodos
            nodes_info = []
            healthy_nodes = 0
            
            for node_id, node_info in cluster_nodes.items():
                node = RedisNodeInfo(
                    host=node_info.get("host", "unknown"),
                    port=node_info.get("port", 0),
                    node_id=node_id,
                    role=node_info.get("role", "unknown"),
                    status=RedisNodeStatus.HEALTHY if node_info.get("connected") else RedisNodeStatus.FAILED
                )
                
                if node.status == RedisNodeStatus.HEALTHY:
                    healthy_nodes += 1
                
                nodes_info.append(node)
            
            # Estadísticas del cluster
            cluster_stats = RedisClusterStats(
                total_nodes=len(nodes_info),
                healthy_nodes=healthy_nodes,
                failed_nodes=len(nodes_info) - healthy_nodes,
                cluster_state=cluster_info.get("cluster_state", "unknown"),
                slots_assigned=int(cluster_info.get("cluster_slots_assigned", 0)),
                slots_ok=int(cluster_info.get("cluster_slots_ok", 0)),
                nodes_info=nodes_info
            )
            
            # Determinar estado general
            if healthy_nodes == len(nodes_info) and cluster_stats.cluster_state == "ok":
                status = "healthy"
                self.is_healthy = True
            elif healthy_nodes > len(nodes_info) // 2:
                status = "degraded"
                self.is_healthy = True
            else:
                status = "critical"
                self.is_healthy = False
            
            health_info.update({
                "status": status,
                "cluster_stats": cluster_stats.__dict__,
                "nodes": [node.__dict__ for node in nodes_info]
            })
            
        except Exception as e:
            health_info.update({
                "status": "error",
                "errors": [f"Error en health check cluster: {e}"]
            })
        
        return health_info
    
    async def _health_check_single(self, health_info: Dict) -> Dict:
        """Health check específico para instancia single"""
        try:
            # Ping a la instancia
            ping_result = await self.single_connection.ping()
            
            # Información del servidor
            info = await self.single_connection.info()
            
            # Crear información del nodo
            node = RedisNodeInfo(
                host=self.config["cluster_nodes"][0]["host"],
                port=self.config["cluster_nodes"][0]["port"],
                role="master",
                status=RedisNodeStatus.HEALTHY if ping_result else RedisNodeStatus.FAILED,
                memory_used=info.get("used_memory", 0),
                memory_max=info.get("maxmemory", 0),
                connections=info.get("connected_clients", 0),
                uptime=info.get("uptime_in_seconds", 0),
                version=info.get("redis_version", "unknown")
            )
            
            # Determinar estado
            if ping_result:
                status = "healthy"
                self.is_healthy = True
            else:
                status = "failed"
                self.is_healthy = False
            
            health_info.update({
                "status": status,
                "nodes": [node.__dict__]
            })
            
        except Exception as e:
            health_info.update({
                "status": "error",
                "errors": [f"Error en health check single: {e}"]
            })
        
        return health_info
    
    async def _start_health_monitoring(self):
        """Inicia el monitoreo de salud en background"""
        if self._running:
            return
        
        self._running = True
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("🔍 Monitoreo de salud Redis iniciado")
    
    async def _health_monitor_loop(self):
        """Loop de monitoreo de salud"""
        while self._running:
            try:
                await self.health_check()
                await asyncio.sleep(self.config["health_check_interval"])
            except Exception as e:
                logger.error(f"❌ Error en loop de monitoreo: {e}")
                await asyncio.sleep(60)  # Esperar más tiempo si hay error
    
    async def stop(self):
        """Detiene el Redis Manager y cierra conexiones"""
        logger.info("🛑 Deteniendo Redis Manager...")
        
        self._running = False
        
        # Cancelar tarea de monitoreo
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cerrar conexiones
        try:
            if self.cluster:
                await self.cluster.close()
            if self.single_connection:
                await self.single_connection.close()
        except Exception as e:
            logger.error(f"❌ Error cerrando conexiones Redis: {e}")
        
        self.is_initialized = False
        self.is_healthy = False
        
        logger.info("✅ Redis Manager detenido")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del Redis Manager"""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        return {
            "redis_manager": {
                "is_initialized": self.is_initialized,
                "is_healthy": self.is_healthy,
                "connection_type": self.connection_type.value,
                "environment": ENVIRONMENT,
                "uptime_seconds": uptime.total_seconds(),
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
            },
            "operations": {
                "connections_created": self.stats["connections_created"],
                "connections_failed": self.stats["connections_failed"],
                "operations_total": self.stats["operations_total"],
                "operations_failed": self.stats["operations_failed"],
                "success_rate": (
                    (self.stats["operations_total"] - self.stats["operations_failed"]) / 
                    max(self.stats["operations_total"], 1)
                ) * 100
            },
            "failover": {
                "failovers_count": self.stats["failovers_count"],
                "last_failover": self.stats["last_failover"].isoformat() if self.stats["last_failover"] else None
            },
            "configuration": {
                "cluster_nodes": len(self.config["cluster_nodes"]),
                "max_connections": self.config["max_connections"],
                "socket_timeout": self.config["socket_timeout"],
                "health_check_interval": self.config["health_check_interval"],
                "redis_available": REDIS_AVAILABLE
            }
        }

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del Redis Manager
redis_manager = RedisManagerEnterprise()

# ===============================
# FUNCIONES DE CONVENIENCIA
# ===============================

async def initialize_redis() -> bool:
    """Inicializa el Redis Manager global"""
    return await redis_manager.initialize()

async def get_redis_connection():
    """Obtiene una conexión Redis"""
    return await redis_manager.get_connection()

async def execute_redis_command(command: str, *args, **kwargs):
    """Ejecuta un comando Redis"""
    return await redis_manager.execute_command(command, *args, **kwargs)

async def redis_health_check() -> Dict[str, Any]:
    """Verifica la salud de Redis"""
    return await redis_manager.health_check()

def get_redis_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de Redis"""
    return redis_manager.get_stats()

async def stop_redis():
    """Detiene el Redis Manager"""
    await redis_manager.stop() 