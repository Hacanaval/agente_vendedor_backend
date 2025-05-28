"""
Sistema de WebSockets para streaming de respuestas RAG en tiempo real
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json
import logging
from datetime import datetime

from app.core.database import get_db
from app.services.rag import consultar_rag
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
from app.services.chat_control_service import ChatControlService
from app.models.mensaje import Mensaje
from app.models.responses import StatusEnum, TipoMensajeEnum
from app.core.exceptions import RAGException, TimeoutException

router = APIRouter(prefix="/ws", tags=["WebSockets"])
logger = logging.getLogger(__name__)

# Configuración de timeouts para websockets
WS_TIMEOUT_SECONDS = 45  # Timeout más largo para websockets
WS_PING_INTERVAL = 30  # Ping cada 30 segundos


class ConnectionManager:
    """Gestor de conexiones WebSocket"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_connections: Dict[str, List[str]] = {}  # chat_id -> [connection_ids]
    
    async def connect(self, websocket: WebSocket, connection_id: str, chat_id: str):
        """Acepta una nueva conexión WebSocket"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = []
        self.chat_connections[chat_id].append(connection_id)
        
        logger.info(f"WebSocket conectado: {connection_id} para chat {chat_id}")
        
        # Enviar mensaje de bienvenida
        await self.send_message(connection_id, {
            "type": "connection_status",
            "status": "connected",
            "message": "Conexión WebSocket establecida",
            "chat_id": chat_id,
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, connection_id: str, chat_id: str):
        """Desconecta una conexión WebSocket"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if chat_id in self.chat_connections:
            if connection_id in self.chat_connections[chat_id]:
                self.chat_connections[chat_id].remove(connection_id)
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        logger.info(f"WebSocket desconectado: {connection_id} del chat {chat_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Envía un mensaje a una conexión específica"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Error enviando mensaje a {connection_id}: {e}")
                # Remover conexión problemática
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
    
    async def broadcast_to_chat(self, chat_id: str, message: Dict[str, Any]):
        """Envía un mensaje a todas las conexiones de un chat"""
        if chat_id in self.chat_connections:
            for connection_id in self.chat_connections[chat_id].copy():
                await self.send_message(connection_id, message)
    
    async def send_typing_indicator(self, chat_id: str, typing: bool = True):
        """Envía indicador de escritura"""
        message = {
            "type": "typing",
            "typing": typing,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_chat(chat_id, message)
    
    async def send_error(self, connection_id: str, error_message: str, error_code: str = "unknown"):
        """Envía un mensaje de error"""
        message = {
            "type": "error",
            "status": StatusEnum.ERROR,
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_message(connection_id, message)


# Instancia global del gestor de conexiones
manager = ConnectionManager()


@router.websocket("/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str):
    """
    WebSocket endpoint para chat en tiempo real con streaming de respuestas.
    
    Protocolo de mensajes:
    
    Cliente -> Servidor:
    {
        "type": "message",
        "mensaje": "texto del usuario",
        "tono": "amigable",
        "instrucciones": "",
        "llm": "gemini"
    }
    
    Servidor -> Cliente:
    {
        "type": "response_start|response_chunk|response_end|typing|error",
        "content": "contenido del chunk",
        "chat_id": "id_del_chat",
        "tipo_mensaje": "inventario|venta|cliente|general",
        "timestamp": "2024-01-01T00:00:00"
    }
    """
    
    # Generar ID único para esta conexión
    connection_id = f"{chat_id}_{datetime.now().timestamp()}"
    
    try:
        # Conectar WebSocket
        await manager.connect(websocket, connection_id, chat_id)
        
        # Configurar ping/pong para mantener conexión viva
        async def ping_pong():
            try:
                while True:
                    await asyncio.sleep(WS_PING_INTERVAL)
                    await websocket.ping()
            except:
                pass
        
        # Iniciar ping/pong en background
        ping_task = asyncio.create_task(ping_pong())
        
        try:
            while True:
                # Recibir mensaje del cliente
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Validar estructura del mensaje
                if message_data.get("type") != "message":
                    await manager.send_error(
                        connection_id, 
                        "Tipo de mensaje no válido. Use 'message'",
                        "invalid_message_type"
                    )
                    continue
                
                mensaje = message_data.get("mensaje", "").strip()
                if not mensaje:
                    await manager.send_error(
                        connection_id, 
                        "Mensaje vacío",
                        "empty_message"
                    )
                    continue
                
                # Procesar mensaje con streaming
                await process_message_streaming(
                    mensaje=mensaje,
                    chat_id=chat_id,
                    connection_id=connection_id,
                    tono=message_data.get("tono", "amigable"),
                    instrucciones=message_data.get("instrucciones", ""),
                    llm=message_data.get("llm", "gemini")
                )
                
        except WebSocketDisconnect:
            logger.info(f"Cliente desconectado: {connection_id}")
        except Exception as e:
            logger.error(f"Error en WebSocket {connection_id}: {e}")
            await manager.send_error(connection_id, f"Error interno: {str(e)[:100]}", "internal_error")
        finally:
            ping_task.cancel()
            
    except Exception as e:
        logger.error(f"Error estableciendo conexión WebSocket: {e}")
    finally:
        manager.disconnect(connection_id, chat_id)


async def process_message_streaming(
    mensaje: str,
    chat_id: str, 
    connection_id: str,
    tono: str = "amigable",
    instrucciones: str = "",
    llm: str = "gemini"
):
    """
    Procesa un mensaje con streaming de respuesta en tiempo real
    """
    try:
        # Obtener sesión de base de datos
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # 1. Verificar control de chatbot
            await manager.send_typing_indicator(chat_id, True)
            
            debe_responder, razon = await asyncio.wait_for(
                ChatControlService.debe_responder_ia(db, chat_id),
                timeout=3.0
            )
            
            if not debe_responder:
                # Guardar mensaje del usuario
                mensaje_usuario = Mensaje(
                    chat_id=chat_id,
                    remitente="usuario",
                    mensaje=mensaje,
                    timestamp=datetime.now(),
                    tipo_mensaje="contexto"
                )
                db.add(mensaje_usuario)
                await db.commit()
                
                # Enviar respuesta de IA desactivada
                await manager.send_message(connection_id, {
                    "type": "response_complete",
                    "status": StatusEnum.WARNING,
                    "respuesta": f"🔴 {razon}. Este chat está siendo atendido por un humano.",
                    "tipo_mensaje": "error",
                    "chat_id": chat_id,
                    "metadatos": {"ia_desactivada": True, "razon": razon},
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            # 2. Clasificar tipo de mensaje
            await manager.send_message(connection_id, {
                "type": "processing",
                "stage": "classification",
                "message": "Clasificando consulta...",
                "timestamp": datetime.now().isoformat()
            })
            
            try:
                tipo = await asyncio.wait_for(
                    clasificar_tipo_mensaje_llm(mensaje),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                tipo = "general"
            
            # 3. Guardar mensaje del usuario
            mensaje_usuario = Mensaje(
                chat_id=chat_id,
                remitente="usuario",
                mensaje=mensaje,
                timestamp=datetime.now(),
                tipo_mensaje=tipo
            )
            db.add(mensaje_usuario)
            await db.flush()
            
            # 4. Procesar con RAG
            await manager.send_message(connection_id, {
                "type": "processing",
                "stage": "rag_retrieval",
                "message": f"Procesando consulta de tipo: {tipo}...",
                "timestamp": datetime.now().isoformat()
            })
            
            # Procesar con RAG usando timeout extendido para WebSockets
            respuesta = await asyncio.wait_for(
                consultar_rag(
                    mensaje=mensaje,
                    tipo=tipo,
                    db=db,
                    nombre_agente="Agente Vendedor",
                    nombre_empresa="Sextinvalle",
                    tono=tono,
                    instrucciones=instrucciones,
                    llm=llm,
                    chat_id=chat_id
                ),
                timeout=WS_TIMEOUT_SECONDS
            )
            
            # 5. Simular streaming de la respuesta (chunking)
            respuesta_texto = respuesta["respuesta"]
            chunks = split_response_into_chunks(respuesta_texto)
            
            await manager.send_typing_indicator(chat_id, False)
            
            # Enviar inicio de respuesta
            await manager.send_message(connection_id, {
                "type": "response_start",
                "tipo_mensaje": tipo,
                "chat_id": chat_id,
                "total_chunks": len(chunks),
                "timestamp": datetime.now().isoformat()
            })
            
            # Enviar chunks con delay realista
            for i, chunk in enumerate(chunks):
                await manager.send_message(connection_id, {
                    "type": "response_chunk",
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().isoformat()
                })
                # Delay para simular escritura natural
                await asyncio.sleep(0.1 + len(chunk) * 0.02)  # 50ms base + 20ms por carácter
            
            # 6. Guardar respuesta del agente
            mensaje_agente = Mensaje(
                chat_id=chat_id,
                remitente="agente",
                mensaje=respuesta_texto,
                timestamp=datetime.now(),
                tipo_mensaje=tipo,
                estado_venta=respuesta.get("estado_venta"),
                metadatos=respuesta.get("metadatos", {})
            )
            db.add(mensaje_agente)
            await db.commit()
            
            # 7. Enviar finalización
            await manager.send_message(connection_id, {
                "type": "response_end",
                "status": StatusEnum.SUCCESS,
                "respuesta_completa": respuesta_texto,
                "tipo_mensaje": tipo,
                "chat_id": chat_id,
                "metadatos": respuesta.get("metadatos", {}),
                "estado_venta": respuesta.get("estado_venta"),
                "timestamp": datetime.now().isoformat()
            })
            
        except asyncio.TimeoutError:
            await manager.send_error(
                connection_id,
                f"La consulta tomó más tiempo del esperado ({WS_TIMEOUT_SECONDS}s). Intenta de nuevo.",
                "timeout_error"
            )
            await db.rollback()
            
        except Exception as e:
            logger.error(f"Error procesando mensaje streaming: {e}")
            await manager.send_error(
                connection_id,
                f"Error procesando consulta: {str(e)[:100]}",
                "processing_error"
            )
            await db.rollback()
            
        finally:
            await db.close()
            
    except Exception as e:
        logger.error(f"Error crítico en process_message_streaming: {e}")
        await manager.send_error(
            connection_id,
            "Error interno del servidor",
            "critical_error"
        )


def split_response_into_chunks(response: str, chunk_size: int = 50) -> List[str]:
    """
    Divide una respuesta en chunks para streaming.
    Intenta dividir por oraciones para mejor UX.
    """
    if len(response) <= chunk_size:
        return [response]
    
    # Intentar dividir por oraciones
    sentences = response.replace('. ', '.|').replace('? ', '?|').replace('! ', '!|').split('|')
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Si aún hay chunks muy largos, dividir por palabras
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            words = chunk.split(' ')
            temp_chunk = ""
            for word in words:
                if len(temp_chunk) + len(word) + 1 <= chunk_size:
                    temp_chunk += f" {word}" if temp_chunk else word
                else:
                    if temp_chunk:
                        final_chunks.append(temp_chunk.strip())
                    temp_chunk = word
            if temp_chunk:
                final_chunks.append(temp_chunk.strip())
    
    return final_chunks


@router.get("/connections/stats")
async def get_connection_stats():
    """
    Endpoint para obtener estadísticas de conexiones WebSocket activas.
    Útil para monitoreo y debugging.
    """
    return {
        "active_connections": len(manager.active_connections),
        "active_chats": len(manager.chat_connections),
        "connections_per_chat": {
            chat_id: len(connections) 
            for chat_id, connections in manager.chat_connections.items()
        },
        "timestamp": datetime.now().isoformat()
    } 