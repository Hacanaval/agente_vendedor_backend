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
    mensaje: str = Field(..., min_length=1, max_length=1000)
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
        
        # Clasificar tipo de mensaje automáticamente
        tipo = await clasificar_tipo_mensaje_llm(req.mensaje)
        logging.info(f"[chat_texto] Mensaje clasificado como: {tipo}")
        
        # Guardar mensaje del usuario
        mensaje_usuario = Mensaje(
            chat_id=chat_id,
            remitente="usuario",
            mensaje=req.mensaje,
            timestamp=datetime.now(),
            tipo_mensaje=tipo
        )
        db.add(mensaje_usuario)
        await db.flush()
        
        # Procesar con RAG
        respuesta = await consultar_rag(
            mensaje=req.mensaje,
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
            "metadatos": None
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
        
        # Leer y procesar la imagen
        contenido_imagen = await imagen.read()
        
        # Configurar Gemini para visión
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Preparar la imagen para Gemini
        imagen_data = {
            'mime_type': imagen.content_type,
            'data': contenido_imagen
        }
        
        # Generar descripción de la imagen
        prompt_descripcion = prompt_vision(mensaje)
        response = model.generate_content([prompt_descripcion, imagen_data])
        descripcion_imagen = response.text
        
        # Clasificar el tipo de consulta basado en la descripción
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
            metadatos={"descripcion_imagen": descripcion_imagen}
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
            "respuesta_agente": respuesta_rag["respuesta"],
            "tipo_mensaje": tipo,
            "estado_venta": respuesta_rag.get("estado_venta")
        }
        
    except Exception as e:
        await db.rollback()
        logging.error(f"Error procesando imagen: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar la imagen")

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
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            contenido = await audio.read()
            temp_file.write(contenido)
            temp_file_path = temp_file.name
        
        try:
            # Transcribir con Gemini (si está disponible) o usar un servicio alternativo
            # Por ahora, simulamos la transcripción
            transcripcion = "Transcripción no disponible temporalmente"
            
            # TODO: Implementar transcripción real con Gemini o Whisper
            # transcripcion = await transcribir_audio_gemini(temp_file_path)
            
            if transcripcion and transcripcion != "Transcripción no disponible temporalmente":
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
                    tipo_mensaje=tipo
                )
                db.add(mensaje_usuario)
                
                mensaje_agente = Mensaje(
                    chat_id=chat_id,
                    remitente="agente",
                    mensaje=respuesta_rag["respuesta"],
                    timestamp=datetime.now(),
                    tipo_mensaje=tipo,
                    estado_venta=respuesta_rag.get("estado_venta")
                )
                db.add(mensaje_agente)
                await db.commit()
                
                return {
                    "transcripcion": transcripcion,
                    "respuesta": respuesta_rag["respuesta"],
                    "tipo_mensaje": tipo,
                    "estado_venta": respuesta_rag.get("estado_venta")
                }
            else:
                return {
                    "transcripcion": "No se pudo transcribir el audio",
                    "respuesta": "Lo siento, no pude procesar tu mensaje de audio. Intenta enviarlo de nuevo o escribe tu consulta.",
                    "tipo_mensaje": "contexto",
                    "estado_venta": None
                }
                
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logging.error(f"Error procesando audio: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al procesar el audio")

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

