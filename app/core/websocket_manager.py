"""
WebSocket Manager Enterprise
Gestión avanzada de conexiones WebSocket para alta concurrencia
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from app.core.rate_limiting import rate_limiter, get_client_identifier

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN ENTERPRISE
# ===============================

# Límites de conexiones
MAX_CONNECTIONS_GLOBAL = 500        # Máximo total de conexiones
MAX_CONNECTIONS_PER_IP = 10         # Máximo por IP
MAX_CONNECTIONS_PER_CHAT = 5        # Máximo por chat room

# Configuración de heartbeat
HEARTBEAT_INTERVAL = 30             # Ping cada 30 segundos
HEARTBEAT_TIMEOUT = 60              # Timeout si no responde en 60s
CONNECTION_TIMEOUT = 300            # 5 minutos timeout total

# Configuración de mensajes
MAX_MESSAGE_SIZE = 10240           # 10KB máximo por mensaje
MESSAGE_RATE_LIMIT = 60            # 60 mensajes por minuto por conexión

# Configuración de limpieza
CLEANUP_INTERVAL = 60              # Limpiar conexiones muertas cada minuto
STATS_UPDATE_INTERVAL = 30         # Actualizar estadísticas cada 30s

# ===============================
# TIPOS Y ESTRUCTURAS
# ===============================

class ConnectionState(Enum):
    """Estados de conexión WebSocket"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class ConnectionInfo:
    """Información detallada de una conexión WebSocket"""
    connection_id: str
    websocket: WebSocket
    chat_id: str
    client_ip: str
    user_agent: str
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    last_message: Optional[datetime] = None
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_alive(self) -> bool:
        """Verifica si la conexión está viva"""
        if self.state == ConnectionState.DISCONNECTED:
            return False
        
        now = datetime.now()
        
        # Verificar timeout general
        if (now - self.connected_at).seconds > CONNECTION_TIMEOUT:
            return False
        
        # Verificar heartbeat timeout
        if self.last_ping and not self.last_pong:
            if (now - self.last_ping).seconds > HEARTBEAT_TIMEOUT:
                return False
        
        return True
    
    @property
    def connection_duration(self) -> timedelta:
        """Duración de la conexión"""
        return datetime.now() - self.connected_at

# ===============================
# WEBSOCKET MANAGER ENTERPRISE
# ===============================

class WebSocketManagerEnterprise:
    """
    Gestor avanzado de conexiones WebSocket con características enterprise:
    - Límites de conexiones por IP/chat/global
    - Heartbeat automático con detección de conexiones muertas
    - Rate limiting por conexión
    - Estadísticas en tiempo real
    - Gestión automática de memoria
    - Soporte para autenticación
    """
    
    def __init__(self):
        # Storage principal de conexiones
        self.connections: Dict[str, ConnectionInfo] = {}
        
        # Índices para búsqueda rápida
        self.connections_by_chat: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_ip: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_user: Dict[str, Set[str]] = defaultdict(set)
        
        # Estadísticas
        self.stats = {
            "total_connections": 0,
            "peak_connections": 0,
            "total_messages": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "connections_rejected": 0,
            "heartbeat_timeouts": 0,
            "start_time": datetime.now()
        }
        
        # Tareas en background
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        
        # Control de estado
        self._running = False
        
        logger.info("🔌 WebSocket Manager Enterprise inicializado")
    
    async def start(self):
        """Inicia las tareas en background del manager"""
        if self._running:
            return
        
        self._running = True
        
        # Iniciar tareas de mantenimiento
        self._cleanup_task = asyncio.create_task(self._cleanup_dead_connections())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._stats_task = asyncio.create_task(self._update_stats_loop())
        
        logger.info("🚀 WebSocket Manager Enterprise iniciado")
    
    async def stop(self):
        """Detiene el manager y cierra todas las conexiones"""
        self._running = False
        
        # Cancelar tareas
        for task in [self._cleanup_task, self._heartbeat_task, self._stats_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Cerrar todas las conexiones
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id, "server_shutdown")
        
        logger.info("🛑 WebSocket Manager Enterprise detenido")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        chat_id: str,
        client_ip: str,
        user_agent: str = "",
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Acepta una nueva conexión WebSocket con validaciones enterprise
        
        Returns:
            connection_id si se acepta, None si se rechaza
        """
        # Verificar límites de conexiones
        if not self._can_accept_connection(client_ip, chat_id):
            await websocket.close(code=1008, reason="Connection limit exceeded")
            self.stats["connections_rejected"] += 1
            return None
        
        # Generar ID único
        connection_id = f"{chat_id}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Aceptar conexión
            await websocket.accept()
            
            # Crear info de conexión
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                chat_id=chat_id,
                client_ip=client_ip,
                user_agent=user_agent,
                user_id=user_id,
                state=ConnectionState.CONNECTED
            )
            
            # Almacenar conexión
            self.connections[connection_id] = connection_info
            self.connections_by_chat[chat_id].add(connection_id)
            self.connections_by_ip[client_ip].add(connection_id)
            if user_id:
                self.connections_by_user[user_id].add(connection_id)
            
            # Actualizar estadísticas
            self.stats["total_connections"] = len(self.connections)
            self.stats["peak_connections"] = max(
                self.stats["peak_connections"], 
                self.stats["total_connections"]
            )
            
            logger.info(f"🔗 WebSocket conectado: {connection_id} (IP: {client_ip}, Chat: {chat_id})")
            
            # Enviar mensaje de bienvenida
            await self.send_to_connection(connection_id, {
                "type": "connection_established",
                "connection_id": connection_id,
                "chat_id": chat_id,
                "server_time": datetime.now().isoformat(),
                "limits": {
                    "max_message_size": MAX_MESSAGE_SIZE,
                    "heartbeat_interval": HEARTBEAT_INTERVAL
                }
            })
            
            return connection_id
            
        except Exception as e:
            logger.error(f"❌ Error aceptando conexión: {e}")
            self.stats["connections_rejected"] += 1
            return None
    
    async def disconnect(self, connection_id: str, reason: str = "normal"):
        """Desconecta una conexión WebSocket"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        connection.state = ConnectionState.DISCONNECTING
        
        try:
            # Enviar mensaje de despedida si es posible
            if reason != "error":
                await self.send_to_connection(connection_id, {
                    "type": "connection_closing",
                    "reason": reason,
                    "duration_seconds": connection.connection_duration.total_seconds()
                })
            
            # Cerrar WebSocket
            await connection.websocket.close()
            
        except Exception as e:
            logger.warning(f"Error cerrando WebSocket {connection_id}: {e}")
        
        # Limpiar de todos los índices
        self._remove_connection_from_indexes(connection_id)
        
        # Actualizar estadísticas
        self.stats["total_connections"] = len(self.connections)
        
        logger.info(f"🔌 WebSocket desconectado: {connection_id} (razón: {reason})")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Envía un mensaje a una conexión específica
        
        Returns:
            True si se envió exitosamente, False si falló
        """
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        
        try:
            # Verificar rate limiting
            allowed, _ = await rate_limiter.check_rate_limit(
                f"ws:{connection_id}", 
                "chat_websocket"
            )
            
            if not allowed:
                logger.warning(f"Rate limit excedido para WebSocket {connection_id}")
                return False
            
            # Serializar mensaje
            message_text = json.dumps(message, ensure_ascii=False)
            message_bytes = len(message_text.encode('utf-8'))
            
            # Verificar tamaño del mensaje
            if message_bytes > MAX_MESSAGE_SIZE:
                logger.warning(f"Mensaje demasiado grande para {connection_id}: {message_bytes} bytes")
                return False
            
            # Enviar mensaje
            await connection.websocket.send_text(message_text)
            
            # Actualizar estadísticas
            connection.bytes_sent += message_bytes
            connection.last_message = datetime.now()
            self.stats["total_bytes_sent"] += message_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje a {connection_id}: {e}")
            # Marcar para desconexión
            asyncio.create_task(self.disconnect(connection_id, "send_error"))
            return False
    
    async def broadcast_to_chat(self, chat_id: str, message: Dict[str, Any]) -> int:
        """
        Envía un mensaje a todas las conexiones de un chat
        
        Returns:
            Número de conexiones que recibieron el mensaje exitosamente
        """
        if chat_id not in self.connections_by_chat:
            return 0
        
        connection_ids = list(self.connections_by_chat[chat_id])
        successful_sends = 0
        
        # Enviar a todas las conexiones en paralelo
        tasks = []
        for connection_id in connection_ids:
            task = asyncio.create_task(self.send_to_connection(connection_id, message))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result is True:
                successful_sends += 1
        
        return successful_sends
    
    async def ping_connection(self, connection_id: str) -> bool:
        """Envía ping a una conexión específica"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        
        try:
            await connection.websocket.ping()
            connection.last_ping = datetime.now()
            return True
        except Exception as e:
            logger.warning(f"Error en ping a {connection_id}: {e}")
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas detalladas de conexiones"""
        now = datetime.now()
        uptime = now - self.stats["start_time"]
        
        # Estadísticas por estado
        states = defaultdict(int)
        for conn in self.connections.values():
            states[conn.state.value] += 1
        
        # Estadísticas por chat
        chat_stats = {
            chat_id: len(conn_ids) 
            for chat_id, conn_ids in self.connections_by_chat.items()
        }
        
        # Estadísticas por IP
        ip_stats = {
            ip: len(conn_ids) 
            for ip, conn_ids in self.connections_by_ip.items()
        }
        
        return {
            "current_connections": len(self.connections),
            "peak_connections": self.stats["peak_connections"],
            "total_messages": self.stats["total_messages"],
            "total_bytes_sent": self.stats["total_bytes_sent"],
            "total_bytes_received": self.stats["total_bytes_received"],
            "connections_rejected": self.stats["connections_rejected"],
            "heartbeat_timeouts": self.stats["heartbeat_timeouts"],
            "uptime_seconds": uptime.total_seconds(),
            "connections_by_state": dict(states),
            "connections_by_chat": chat_stats,
            "connections_by_ip": ip_stats,
            "limits": {
                "max_global": MAX_CONNECTIONS_GLOBAL,
                "max_per_ip": MAX_CONNECTIONS_PER_IP,
                "max_per_chat": MAX_CONNECTIONS_PER_CHAT,
                "max_message_size": MAX_MESSAGE_SIZE
            }
        }
    
    # ===============================
    # MÉTODOS PRIVADOS
    # ===============================
    
    def _can_accept_connection(self, client_ip: str, chat_id: str) -> bool:
        """Verifica si se puede aceptar una nueva conexión"""
        # Verificar límite global
        if len(self.connections) >= MAX_CONNECTIONS_GLOBAL:
            logger.warning(f"Límite global de conexiones alcanzado: {len(self.connections)}")
            return False
        
        # Verificar límite por IP
        if len(self.connections_by_ip[client_ip]) >= MAX_CONNECTIONS_PER_IP:
            logger.warning(f"Límite de conexiones por IP alcanzado para {client_ip}")
            return False
        
        # Verificar límite por chat
        if len(self.connections_by_chat[chat_id]) >= MAX_CONNECTIONS_PER_CHAT:
            logger.warning(f"Límite de conexiones por chat alcanzado para {chat_id}")
            return False
        
        return True
    
    def _remove_connection_from_indexes(self, connection_id: str):
        """Remueve una conexión de todos los índices"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remover de índices
        self.connections_by_chat[connection.chat_id].discard(connection_id)
        self.connections_by_ip[connection.client_ip].discard(connection_id)
        
        if connection.user_id:
            self.connections_by_user[connection.user_id].discard(connection_id)
        
        # Limpiar índices vacíos
        if not self.connections_by_chat[connection.chat_id]:
            del self.connections_by_chat[connection.chat_id]
        if not self.connections_by_ip[connection.client_ip]:
            del self.connections_by_ip[connection.client_ip]
        if connection.user_id and not self.connections_by_user[connection.user_id]:
            del self.connections_by_user[connection.user_id]
        
        # Remover conexión principal
        del self.connections[connection_id]
    
    async def _cleanup_dead_connections(self):
        """Tarea en background para limpiar conexiones muertas"""
        while self._running:
            try:
                dead_connections = []
                
                for connection_id, connection in self.connections.items():
                    if not connection.is_alive:
                        dead_connections.append(connection_id)
                
                # Desconectar conexiones muertas
                for connection_id in dead_connections:
                    await self.disconnect(connection_id, "timeout")
                
                if dead_connections:
                    logger.info(f"🧹 Limpiadas {len(dead_connections)} conexiones muertas")
                
                await asyncio.sleep(CLEANUP_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error en cleanup de conexiones: {e}")
                await asyncio.sleep(CLEANUP_INTERVAL)
    
    async def _heartbeat_loop(self):
        """Tarea en background para enviar heartbeats"""
        while self._running:
            try:
                now = datetime.now()
                ping_tasks = []
                
                for connection_id, connection in self.connections.items():
                    # Verificar si necesita ping
                    needs_ping = (
                        connection.last_ping is None or 
                        (now - connection.last_ping).seconds >= HEARTBEAT_INTERVAL
                    )
                    
                    if needs_ping and connection.state == ConnectionState.CONNECTED:
                        task = asyncio.create_task(self.ping_connection(connection_id))
                        ping_tasks.append(task)
                
                # Ejecutar pings en paralelo
                if ping_tasks:
                    await asyncio.gather(*ping_tasks, return_exceptions=True)
                
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error en heartbeat loop: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    async def _update_stats_loop(self):
        """Tarea en background para actualizar estadísticas"""
        while self._running:
            try:
                # Actualizar contadores principales
                self.stats["total_connections"] = len(self.connections)
                
                # Calcular estadísticas adicionales si es necesario
                # (por ahora solo actualizamos el contador principal)
                
                await asyncio.sleep(STATS_UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error actualizando estadísticas: {e}")
                await asyncio.sleep(STATS_UPDATE_INTERVAL)

# ===============================
# INSTANCIA GLOBAL
# ===============================

# Instancia global del WebSocket Manager Enterprise
ws_manager = WebSocketManagerEnterprise() 