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
from sqlalchemy import insert, select
from datetime import datetime
import aiohttp
import tempfile
import os
import base64
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/chat", tags=["chat"])

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

@router.post("/texto", response_model=Dict[str, Any])
async def chat_texto(
    req: ChatTextoRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint principal unificado para chat de texto.
    Clasifica automáticamente el tipo de mensaje y procesa con RAG.
    """
    try:
        chat_id = req.chat_id or "default"
        
        # Validación mejorada de mensajes vacíos o inválidos
        mensaje_limpio = req.mensaje.strip()
        if not mensaje_limpio:
            return {
                "respuesta": "Hola, soy el asistente de Sextinvalle. ¿En qué puedo ayudarte hoy? Puedes preguntarme sobre nuestros productos, servicios o hacer un pedido.",
                "tipo_mensaje": "contexto",
                "estado_venta": None,
                "metadatos": {"mensaje_vacio": True}
            }
        
        # Validación de mensajes muy cortos o sin sentido
        if len(mensaje_limpio) < 2:
            return {
                "respuesta": "No entendí tu mensaje. ¿Podrías ser más específico? Puedo ayudarte con información sobre productos, precios o realizar un pedido.",
                "tipo_mensaje": "contexto", 
                "estado_venta": None,
                "metadatos": {"mensaje_muy_corto": True}
            }
        
        # Clasificar tipo de mensaje automáticamente
        tipo = await clasificar_tipo_mensaje_llm(mensaje_limpio)
        logging.info(f"[chat_texto] Mensaje clasificado como: {tipo}")
        
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
        
        # Procesar con RAG
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
            "estado_venta": respuesta.get("estado_venta"),
            "metadatos": respuesta.get("metadatos")
        }
        
    except Exception as e:
        await db.rollback()
        logging.error(f"Error en chat_texto: {str(e)}")
        return {
            "respuesta": "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
            "tipo_mensaje": "contexto",
            "estado_venta": None,
            "metadatos": {"error": True}
        }

# ----------- Endpoint para Imágenes -----------

@router.post("/imagen", response_model=Dict[str, Any])
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
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de archivo no soportado. Tipos permitidos: {', '.join(tipos_permitidos)}"
            )
        
        # Validar tamaño de archivo (máximo 10MB)
        contenido_imagen = await imagen.read()
        if len(contenido_imagen) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="El archivo es demasiado grande. Máximo 10MB.")
        
        # Verificar que la imagen no esté vacía
        if len(contenido_imagen) == 0:
            raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")
        
        # Configurar Gemini para visión
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="API key de Google no configurada")
        
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
        
        return {
            "descripcion_imagen": descripcion_imagen,
            "respuesta": respuesta_rag["respuesta"],
            "tipo_mensaje": tipo,
            "estado_venta": respuesta_rag.get("estado_venta"),
            "metadatos": respuesta_rag.get("metadatos")
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error procesando imagen: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar la imagen: {str(e)}")

# ----------- Endpoint para Audio -----------

@router.post("/audio", response_model=Dict[str, Any])
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
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo de audio no soportado. Tipos permitidos: {', '.join(tipos_audio_permitidos)}"
            )
        
        # Validar tamaño de archivo (máximo 25MB para Whisper)
        contenido = await audio.read()
        if len(contenido) > 25 * 1024 * 1024:  # 25MB
            raise HTTPException(status_code=400, detail="El archivo de audio es demasiado grande. Máximo 25MB.")
        
        if len(contenido) == 0:
            raise HTTPException(status_code=400, detail="El archivo de audio está vacío.")
        
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
                return {
                    "transcripcion": "Servicio de transcripción no disponible",
                    "respuesta": "Lo siento, el servicio de transcripción de audio no está disponible en este momento. Por favor, escribe tu consulta en texto.",
                    "tipo_mensaje": "contexto",
                    "estado_venta": None,
                    "metadatos": {"error": "transcripcion_no_disponible"}
                }
            
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
                
                return {
                    "transcripcion": transcripcion,
                    "respuesta": respuesta_rag["respuesta"],
                    "tipo_mensaje": tipo,
                    "estado_venta": respuesta_rag.get("estado_venta"),
                    "metadatos": respuesta_rag.get("metadatos")
                }
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
                
                return {
                    "transcripcion": "No se pudo transcribir el audio",
                    "respuesta": "Lo siento, no pude entender tu mensaje de audio. Por favor, intenta hablar más claro o escribe tu consulta en texto.",
                    "tipo_mensaje": "contexto",
                    "estado_venta": None,
                    "metadatos": {"error": "transcripcion_fallida"}
                }
                
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logging.error(f"Error procesando audio: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar el audio: {str(e)}")

# ----------- Endpoint de Historial -----------

@router.get("/historial/{chat_id}", response_model=List[Dict[str, Any]])
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
        
        return [
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
        
    except Exception as e:
        logging.error(f"Error obteniendo historial: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener el historial")

# ----------- Endpoint de Salud -----------

@router.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud del servicio de chat.
    """
    return {
        "status": "ok",
        "service": "chat",
        "timestamp": datetime.now(),
        "llm_disponible": bool(os.getenv("GOOGLE_API_KEY"))
    }

