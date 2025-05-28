from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from typing import Dict, Any, Optional, List
from app.services.rag import consultar_rag
from pydantic import BaseModel, Field
import logging
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
from app.services.llm_client import generar_respuesta
from app.services.prompts import prompt_vision, prompt_audio
from app.models.mensaje import Mensaje
from app.services.chat_control_service import ChatControlService
from sqlalchemy import insert, select
from datetime import datetime
import aiohttp
import tempfile
import os
import base64
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
from app.models.responses import ChatResponse, ErrorResponse, StatusEnum, TipoMensajeEnum, ListResponse, HealthResponse
from app.core.exceptions import BadRequest, TimeoutException, RAGException, DatabaseException

load_dotenv()

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Configuración de timeouts
CHAT_TIMEOUT_SECONDS = 20  # Timeout total para el endpoint
CLASSIFICATION_TIMEOUT_SECONDS = 5  # Timeout para clasificación

def mapear_tipo_mensaje(tipo: str) -> str:
    """Mapea tipos de mensaje a valores válidos del enum TipoMensajeEnum"""
    mapeo = {
        "contexto": "general",
        "empresa": "general",
        "informacion": "general",
        "consulta": "general"
    }
    return mapeo.get(tipo.lower(), tipo)

# ----------- Modelos de Request -----------

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tipo: Optional[str] = Field(default=None)
    tono: str = Field(default="amigable")
    instrucciones: str = Field(default="", max_length=500)
    llm: str = Field(default="gemini")
    chat_id: Optional[str] = Field(default=None)

class ChatTextoRequest(BaseModel):
    mensaje: str = Field(..., min_length=0, max_length=1000)
    tono: str = Field(default="amigable")
    instrucciones: str = Field(default="", max_length=500)
    llm: str = Field(default="gemini")
    chat_id: Optional[str] = Field(default=None)

# ----------- Endpoint Principal Unificado -----------

@router.post("/texto", response_model=ChatResponse)
async def chat_texto(
    req: ChatTextoRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint principal unificado para chat de texto.
    Clasifica automáticamente el tipo de mensaje y procesa con RAG.
    """
    chat_id = req.chat_id or "default"
    
    try:
        # Ejecutar con timeout global
        resultado = await asyncio.wait_for(
            _procesar_chat_texto(req, db, chat_id),
            timeout=CHAT_TIMEOUT_SECONDS
        )
        
        # Convertir resultado a ChatResponse
        tipo_mapeado = mapear_tipo_mensaje(resultado.get("tipo_mensaje", "general"))
        return ChatResponse(
            status=StatusEnum.SUCCESS,
            message="Respuesta generada correctamente",
            respuesta=resultado["respuesta"],
            tipo_mensaje=TipoMensajeEnum(tipo_mapeado),
            chat_id=chat_id,
            metadatos=resultado.get("metadatos", {})
        )
        
    except asyncio.TimeoutError:
        logger.warning(f"Timeout en chat_texto después de {CHAT_TIMEOUT_SECONDS}s para chat_id: {chat_id}")
        await db.rollback()
        raise TimeoutException("chat_texto", CHAT_TIMEOUT_SECONDS)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en chat_texto: {str(e)}", exc_info=True)
        raise RAGException(
            message=f"Error procesando consulta: {str(e)[:100]}",
            rag_type="chat_texto",
            details={"chat_id": chat_id, "mensaje_length": len(req.mensaje)}
        )


async def _procesar_chat_texto(
    req: ChatTextoRequest,
    db: AsyncSession,
    chat_id: str
) -> Dict[str, Any]:
    """Procesamiento interno del chat de texto"""
    
    # 🔥 VERIFICAR SI LA IA DEBE RESPONDER (CONTROL DE CHATBOT)
    try:
        debe_responder, razon = await asyncio.wait_for(
            ChatControlService.debe_responder_ia(db, chat_id),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout verificando control de chatbot, asumiendo que debe responder")
        debe_responder, razon = True, ""
    
    if not debe_responder:
        # Guardar mensaje del usuario pero no responder con IA
        mensaje_usuario = Mensaje(
            chat_id=chat_id,
            remitente="usuario",
            mensaje=req.mensaje.strip(),
            timestamp=datetime.now(),
            tipo_mensaje="contexto"
        )
        db.add(mensaje_usuario)
        await db.commit()
        
        return {
            "respuesta": f"🔴 {razon}. Este chat está siendo atendido por un humano.",
            "tipo_mensaje": "error",
            "chat_id": chat_id,
            "metadatos": {
                "ia_desactivada": True,
                "razon": razon
            }
        }
    
    # Validación mejorada de mensajes vacíos o inválidos
    mensaje_limpio = req.mensaje.strip()
    if not mensaje_limpio:
        return {
            "respuesta": "Hola, soy el asistente de Sextinvalle. ¿En qué puedo ayudarte hoy? Puedes preguntarme sobre nuestros productos, servicios o hacer un pedido.",
            "tipo_mensaje": "saludo",
            "chat_id": chat_id,
            "metadatos": {"mensaje_vacio": True}
        }
    
    # Validación de mensajes muy cortos o sin sentido
    if len(mensaje_limpio) < 2:
        raise BadRequest(
            message="Mensaje muy corto. Por favor, proporciona más información sobre lo que necesitas.",
            details={"mensaje_length": len(mensaje_limpio), "chat_id": chat_id}
        )
    
    # Clasificar tipo de mensaje automáticamente con timeout
    try:
        tipo = await asyncio.wait_for(
            clasificar_tipo_mensaje_llm(mensaje_limpio),
            timeout=CLASSIFICATION_TIMEOUT_SECONDS
        )
        logger.info(f"[chat_texto] Mensaje clasificado como: {tipo}")
    except asyncio.TimeoutError:
        logger.warning(f"Timeout en clasificación, usando tipo por defecto")
        tipo = "general"  # Tipo por defecto
    
    # Guardar mensaje del usuario
    mensaje_usuario = Mensaje(
        chat_id=chat_id,
        remitente="usuario",
        mensaje=mensaje_limpio,
        timestamp=datetime.now(),
        tipo_mensaje=tipo
    )
    db.add(mensaje_usuario)
    await db.flush()
    
    # Procesar con RAG (ya tiene su propio manejo de timeouts)
    respuesta = await consultar_rag(
        mensaje=mensaje_limpio,
        tipo=tipo,
        db=db,
        nombre_agente="Agente Vendedor",
        nombre_empresa="Sextinvalle",
        tono=req.tono,
        instrucciones=req.instrucciones,
        llm=req.llm,
        chat_id=chat_id
    )
    
    # Guardar respuesta del agente
    mensaje_agente = Mensaje(
        chat_id=chat_id,
        remitente="agente",
        mensaje=respuesta["respuesta"],
        timestamp=datetime.now(),
        tipo_mensaje=tipo,
        estado_venta=respuesta.get("estado_venta"),
        metadatos=respuesta.get("metadatos")
    )
    db.add(mensaje_agente)
    await db.commit()
    
    return {
        "respuesta": respuesta["respuesta"],
        "tipo_mensaje": tipo,
        "chat_id": chat_id,
        "metadatos": respuesta.get("metadatos", {})
    }

# ----------- Endpoint para Imágenes -----------

@router.post("/imagen", response_model=ChatResponse)
async def procesar_imagen_gemini(
    imagen: UploadFile = File(...),
    mensaje: str = Form(""),
    llm: str = Form("gemini"),
    chat_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Procesa imágenes usando Gemini Vision.
    """
    try:
        chat_id = chat_id or "default"
        
        # Validar tipo de archivo
        tipos_permitidos = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
        if imagen.content_type not in tipos_permitidos:
            raise BadRequest(
                message=f"Tipo de archivo no soportado. Tipos permitidos: {', '.join(tipos_permitidos)}",
                details={"content_type": imagen.content_type, "tipos_permitidos": tipos_permitidos}
            )
        
        # Validar tamaño de archivo (máximo 10MB)
        contenido_imagen = await imagen.read()
        if len(contenido_imagen) > 10 * 1024 * 1024:  # 10MB
            raise BadRequest(
                message="El archivo es demasiado grande. Máximo 10MB.",
                details={"tamaño_archivo": len(contenido_imagen), "limite_mb": 10}
            )
        
        # Verificar que la imagen no esté vacía
        if len(contenido_imagen) == 0:
            raise BadRequest(
                message="El archivo de imagen está vacío.",
                details={"tamaño_archivo": 0}
            )
        
        # Configurar Gemini para visión
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RAGException(
                message="API key de Google no configurada",
                rag_type="vision",
                details={"servicio": "gemini_vision"}
            )
        
        genai.configure(api_key=api_key)
        
        try:
            # Usar el modelo correcto para visión
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Preparar la imagen para Gemini con el formato correcto
            import PIL.Image
            import io
            
            # Convertir bytes a imagen PIL
            imagen_pil = PIL.Image.open(io.BytesIO(contenido_imagen))
            
            # Generar descripción de la imagen
            prompt_descripcion = prompt_vision(mensaje)
            
            # Generar contenido con imagen
            response = model.generate_content([prompt_descripcion, imagen_pil])
            
            # Verificar que la respuesta sea válida
            if not response.text:
                descripcion_imagen = "No se pudo procesar la imagen. Por favor, intenta con otra imagen."
            else:
                descripcion_imagen = response.text.strip()
            
        except Exception as gemini_error:
            logging.error(f"Error específico de Gemini Vision: {str(gemini_error)}")
            descripcion_imagen = "No se pudo analizar la imagen en este momento. Por favor, describe lo que necesitas en texto."
        
        # Clasificar el tipo de consulta basado en la descripción y mensaje
        consulta_completa = f"{mensaje} {descripcion_imagen}" if mensaje else descripcion_imagen
        tipo = await clasificar_tipo_mensaje_llm(consulta_completa)
        
        # Procesar con RAG usando la descripción
        respuesta_rag = await consultar_rag(
            mensaje=consulta_completa,
            tipo=tipo,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa="Sextinvalle",
            llm=llm,
            chat_id=chat_id
        )
        
        # Guardar en historial
        mensaje_usuario = Mensaje(
            chat_id=chat_id,
            remitente="usuario",
            mensaje=f"[IMAGEN] {mensaje}" if mensaje else "[IMAGEN]",
            timestamp=datetime.now(),
            tipo_mensaje=tipo,
            metadatos={
                "descripcion_imagen": descripcion_imagen,
                "tipo_archivo": imagen.content_type,
                "tamaño_archivo": len(contenido_imagen)
            }
        )
        db.add(mensaje_usuario)
        
        mensaje_agente = Mensaje(
            chat_id=chat_id,
            remitente="agente",
            mensaje=respuesta_rag["respuesta"],
            timestamp=datetime.now(),
            tipo_mensaje=tipo,
            estado_venta=respuesta_rag.get("estado_venta"),
            metadatos=respuesta_rag.get("metadatos")
        )
        db.add(mensaje_agente)
        await db.commit()
        
        return ChatResponse(
            status=StatusEnum.SUCCESS,
            message="Imagen procesada correctamente",
            respuesta=respuesta_rag["respuesta"],
            tipo_mensaje=TipoMensajeEnum(mapear_tipo_mensaje(tipo)),
            chat_id=chat_id,
            metadatos={
                "descripcion_imagen": descripcion_imagen,
                "tipo_archivo": imagen.content_type,
                "tamaño_archivo": len(contenido_imagen),
                "estado_venta": respuesta_rag.get("estado_venta"),
                **respuesta_rag.get("metadatos", {})
            }
        )
        
    except (BadRequest, RAGException, TimeoutException):
        # Re-lanzar excepciones personalizadas sin modificar
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error procesando imagen: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise RAGException(
            message=f"Error interno procesando imagen: {str(e)[:100]}",
            rag_type="vision",
            details={"tipo_archivo": imagen.content_type if 'imagen' in locals() else "unknown"}
        )

# ----------- Endpoint para Audio -----------

@router.post("/audio", response_model=ChatResponse)
async def procesar_audio(
    audio: UploadFile = File(...),
    llm: str = Form("gemini"),
    chat_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Procesa audio transcribiéndolo y procesando el texto resultante.
    """
    try:
        chat_id = chat_id or "default"
        
        # Validar tipo de archivo de audio
        tipos_audio_permitidos = [
            "audio/mpeg", "audio/mp3", "audio/wav", "audio/m4a", 
            "audio/mp4", "audio/webm", "audio/ogg", "audio/x-wav"
        ]
        
        if audio.content_type not in tipos_audio_permitidos:
            raise BadRequest(
                message=f"Tipo de archivo de audio no soportado. Tipos permitidos: {', '.join(tipos_audio_permitidos)}",
                details={"content_type": audio.content_type, "tipos_permitidos": tipos_audio_permitidos}
            )
        
        # Validar tamaño de archivo (máximo 25MB para Whisper)
        contenido = await audio.read()
        if len(contenido) > 25 * 1024 * 1024:  # 25MB
            raise BadRequest(
                message="El archivo de audio es demasiado grande. Máximo 25MB.",
                details={"tamaño_archivo": len(contenido), "limite_mb": 25}
            )
        
        if len(contenido) == 0:
            raise BadRequest(
                message="El archivo de audio está vacío.",
                details={"tamaño_archivo": 0}
            )
        
        # Guardar archivo temporal
        extension = ".mp3"  # Default
        if audio.content_type == "audio/ogg":
            extension = ".ogg"
        elif audio.content_type == "audio/wav":
            extension = ".wav"
        elif audio.content_type == "audio/m4a":
            extension = ".m4a"
        elif audio.content_type == "audio/webm":
            extension = ".webm"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(contenido)
            temp_file_path = temp_file.name
        
        try:
            # Importar el servicio de transcripción
            from app.services.audio_transcription import audio_service
            
            # Verificar si el servicio está disponible
            if not audio_service.is_available():
                return ChatResponse(
                    status=StatusEnum.WARNING,
                    message="Servicio de transcripción no disponible",
                    respuesta="Lo siento, el servicio de transcripción de audio no está disponible en este momento. Por favor, escribe tu consulta en texto.",
                    tipo_mensaje=TipoMensajeEnum.ERROR,
                    chat_id=chat_id,
                    metadatos={"error": "transcripcion_no_disponible"}
                )
            
            # Transcribir audio
            transcripcion = await audio_service.transcribir_audio(temp_file_path, audio.content_type)
            
            if transcripcion and len(transcripcion.strip()) > 0:
                # Clasificar y procesar la transcripción
                tipo = await clasificar_tipo_mensaje_llm(transcripcion)
                
                respuesta_rag = await consultar_rag(
                    mensaje=transcripcion,
                    tipo=tipo,
                    db=db,
                    nombre_agente="Agente Vendedor",
                    nombre_empresa="Sextinvalle",
                    llm=llm,
                    chat_id=chat_id
                )
                
                # Guardar en historial
                mensaje_usuario = Mensaje(
                    chat_id=chat_id,
                    remitente="usuario",
                    mensaje=f"[AUDIO] {transcripcion}",
                    timestamp=datetime.now(),
                    tipo_mensaje=tipo,
                    metadatos={
                        "transcripcion": transcripcion,
                        "tipo_archivo": audio.content_type,
                        "tamaño_archivo": len(contenido)
                    }
                )
                db.add(mensaje_usuario)
                
                mensaje_agente = Mensaje(
                    chat_id=chat_id,
                    remitente="agente",
                    mensaje=respuesta_rag["respuesta"],
                    timestamp=datetime.now(),
                    tipo_mensaje=tipo,
                    estado_venta=respuesta_rag.get("estado_venta"),
                    metadatos=respuesta_rag.get("metadatos")
                )
                db.add(mensaje_agente)
                await db.commit()
                
                return ChatResponse(
                    status=StatusEnum.SUCCESS,
                    message="Audio transcrito y procesado correctamente",
                    respuesta=respuesta_rag["respuesta"],
                    tipo_mensaje=TipoMensajeEnum(mapear_tipo_mensaje(tipo)),
                    chat_id=chat_id,
                    metadatos={
                        "transcripcion": transcripcion,
                        "tipo_archivo": audio.content_type,
                        "tamaño_archivo": len(contenido),
                        "estado_venta": respuesta_rag.get("estado_venta"),
                        **respuesta_rag.get("metadatos", {})
                    }
                )
            else:
                # Guardar intento fallido en historial
                mensaje_usuario = Mensaje(
                    chat_id=chat_id,
                    remitente="usuario",
                    mensaje="[AUDIO] No se pudo transcribir",
                    timestamp=datetime.now(),
                    tipo_mensaje="contexto",
                    metadatos={
                        "error_transcripcion": True,
                        "tipo_archivo": audio.content_type,
                        "tamaño_archivo": len(contenido)
                    }
                )
                db.add(mensaje_usuario)
                await db.commit()
                
                return ChatResponse(
                    status=StatusEnum.WARNING,
                    message="No se pudo transcribir el audio",
                    respuesta="Lo siento, no pude entender tu mensaje de audio. Por favor, intenta hablar más claro o escribe tu consulta en texto.",
                    tipo_mensaje=TipoMensajeEnum.ERROR,
                    chat_id=chat_id,
                    metadatos={
                        "error": "transcripcion_fallida",
                        "tipo_archivo": audio.content_type,
                        "tamaño_archivo": len(contenido)
                    }
                )
                
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except BadRequest:
        # Re-lanzar BadRequest sin modificar
        raise
    except Exception as e:
        logging.error(f"Error procesando audio: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise RAGException(
            message=f"Error interno al procesar el audio: {str(e)[:100]}",
            rag_type="audio",
            details={"tipo_archivo": audio.content_type if 'audio' in locals() else "unknown"}
        )

# ----------- Endpoint de Historial -----------

@router.get("/historial/{chat_id}", response_model=ListResponse)
async def obtener_historial(
    chat_id: str,
    limite: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial de conversación de un chat específico.
    """
    try:
        result = await db.execute(
            select(Mensaje)
            .where(Mensaje.chat_id == chat_id)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        mensajes = result.scalars().all()
        
        datos_mensajes = [
            {
                "id": m.id,
                "remitente": m.remitente,
                "mensaje": m.mensaje,
                "timestamp": m.timestamp,
                "tipo_mensaje": m.tipo_mensaje,
                "estado_venta": m.estado_venta,
                "metadatos": m.metadatos
            }
            for m in reversed(mensajes)  # Orden cronológico
        ]
        
        return ListResponse(
            status=StatusEnum.SUCCESS,
            message=f"Historial obtenido correctamente: {len(datos_mensajes)} mensajes",
            data=datos_mensajes,
            total=len(datos_mensajes),
            metadata={"chat_id": chat_id, "limite": limite}
        )
        
    except Exception as e:
        logging.error(f"Error obteniendo historial: {str(e)}")
        raise DatabaseException(
            message=f"Error al obtener el historial: {str(e)[:100]}",
            operation="obtener_historial",
            details={"chat_id": chat_id, "limite": limite}
        )

# ----------- Endpoint de Salud -----------

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Endpoint de verificación de salud del servicio de chat.
    """
    try:
        # Verificar dependencias del chat
        dependencies = {}
        
        # Verificar Google API Key
        google_api_disponible = bool(os.getenv("GOOGLE_API_KEY"))
        dependencies["google_api_key"] = "available" if google_api_disponible else "missing"
        
        # Verificar servicio de audio
        try:
            from app.services.audio_transcription import audio_service
            dependencies["audio_transcription"] = "available" if audio_service.is_available() else "not_available"
        except ImportError:
            dependencies["audio_transcription"] = "not_available"
        
        # Determinar estado general
        status = StatusEnum.SUCCESS
        message = "Servicio de chat funcionando correctamente"
        
        if not google_api_disponible:
            status = StatusEnum.WARNING
            message = "Servicio de chat con advertencias: Google API Key faltante"
        
        return HealthResponse(
            status=status,
            message=message,
            service_name="Chat Service",
            version="1.0.0",
            dependencies=dependencies
        )
        
    except Exception as e:
        logging.error(f"Error en health check del chat: {str(e)}")
        return HealthResponse(
            status=StatusEnum.ERROR,
            message=f"Error en health check: {str(e)}",
            service_name="Chat Service", 
            version="1.0.0",
            dependencies={}
        )

