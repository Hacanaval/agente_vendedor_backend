from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.empresa import Empresa
from typing import Dict, Any, Optional, List
from app.services.rag import consultar_rag
from pydantic import BaseModel, Field
import logging
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
import aiohttp
import tempfile
import os
from app.services.llm_client import generar_respuesta
from app.services.prompts import prompt_vision, prompt_audio
from app.models.mensaje import Mensaje
from sqlalchemy import insert, select, or_
from datetime import datetime
import google.generativeai as genai
import base64
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tipo: Optional[str] = Field(default=None, pattern="^(inventario|contexto|venta)$")
    tono: str = Field(default="formal", pattern="^(formal|informal|amigable|profesional)$")
    instrucciones: str = Field(default="", max_length=500)
    llm: str = Field(default="gemini", pattern="^(gemini|cohere|local)$")
    chat_id: Optional[str] = Field(default=None)

@router.post("/", response_model=Dict[str, Any])
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de chat tipo RAG: responde consultas de inventario, venta o contexto según tipo.
    Si 'tipo' no viene, se clasifica automáticamente usando LLM.
    Mantiene historial de conversación usando chat_id.
    """
    try:
        nombre_empresa = "Sextinvalle"
        chat_id = req.chat_id or "default"

        # Guardar mensaje del usuario
        mensaje_usuario = Mensaje(
            chat_id=chat_id,
            remitente="usuario",
            mensaje=req.mensaje,
            timestamp=datetime.now(),
            tipo_mensaje=None,  # Se actualizará después de la clasificación
            estado_venta=None,
            metadatos=None
        )
        db.add(mensaje_usuario)
        await db.flush()

        # Clasificar tipo de mensaje si no viene especificado
        tipo = req.tipo
        if not tipo:
            tipo = clasificar_tipo_mensaje_llm(req.mensaje)
        logging.info(f"[chat] Tipo de consulta final: {tipo}")
        mensaje_usuario.tipo_mensaje = tipo

        # Consultar RAG con el chat_id para mantener contexto
        respuesta = await consultar_rag(
            mensaje=req.mensaje,
            tipo=tipo,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa=nombre_empresa,
            tono=req.tono,
            instrucciones=req.instrucciones,
            llm=req.llm,
            chat_id=chat_id
        )

        # Guardar respuesta del agente con el estado de venta y metadatos
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

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error en endpoint chat: {str(e)}")
        return {
            "respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes intentarlo de otra forma o preguntar algo más específico?",
            "tipo_mensaje": None,
            "estado_venta": None,
            "metadatos": None
        }

# --- Imagen ---
class ChatImagenRequest(BaseModel):
    imagen_url: Optional[str] = None
    mensaje: Optional[str] = None  # prompt adicional opcional
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "gemini-pro-vision"

MAX_IMAGE_SIZE_MB = 2
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]

async def procesar_imagen_gemini(image_bytes: bytes, prompt: str, llm: str = "gemini-pro-vision") -> str:
    """
    Procesa la imagen con Gemini (Google) y retorna la descripción generada.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise Exception("GOOGLE_API_KEY no configurada")
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(llm)
    try:
        # (adaptar según la API de Gemini para procesar imágenes, por ejemplo, usando model.generate_content con un objeto de imagen)
        response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}])
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error en Gemini Vision: {str(e)}")
        raise

@router.post("/imagen", summary="Procesa una imagen (archivo o URL) y responde usando visión + RAG", response_model=Dict[str, Any])
async def chat_imagen(request: Request, imagen: Optional[UploadFile] = File(None), imagen_url: Optional[str] = Form(None), mensaje: Optional[str] = Form(None), tono: Optional[str] = Form("formal"), instrucciones: Optional[str] = Form(""), llm: Optional[str] = Form("gemini-pro-vision"), db: AsyncSession = Depends(get_db)):
    logging.info("Recibida petición en /chat/imagen")
    try:
        image_bytes = None
        if imagen is not None:
            if imagen.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=400, detail="Tipo de imagen no permitido. Solo JPEG o PNG.")
            imagen.file.seek(0, 2)
            size_mb = imagen.file.tell() / (1024 * 1024)
            imagen.file.seek(0)
            if size_mb > MAX_IMAGE_SIZE_MB:
                raise HTTPException(status_code=400, detail=f"La imagen supera el tamaño máximo de {MAX_IMAGE_SIZE_MB}MB")
            image_bytes = await imagen.read()
        elif imagen_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(imagen_url) as resp:
                    if resp.status != 200:
                        raise HTTPException(status_code=400, detail="No se pudo descargar la imagen desde la URL")
                    content_type = resp.headers.get("Content-Type", "")
                    if content_type not in ALLOWED_IMAGE_TYPES:
                        raise HTTPException(status_code=400, detail="Tipo de imagen no permitido en la URL. Solo JPEG o PNG.")
                    image_bytes = await resp.read()
                    size_mb = len(image_bytes) / (1024 * 1024)
                    if size_mb > MAX_IMAGE_SIZE_MB:
                        raise HTTPException(status_code=400, detail=f"La imagen supera el tamaño máximo de {MAX_IMAGE_SIZE_MB}MB")
        else:
            raise HTTPException(status_code=400, detail="Debes enviar una imagen como archivo o una imagen_url")
        logging.info(f"Imagen recibida en /chat/imagen: {bool(image_bytes)} bytes, mensaje: {mensaje}")
        descripcion = await procesar_imagen_gemini(image_bytes, mensaje, llm=llm)
        respuesta = await consultar_rag(
            mensaje=descripcion,
            tipo="inventario",
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa="Sextinvalle",
            tono=tono,
            instrucciones=instrucciones,
            llm=llm
        )
        logging.info(f"Respuesta generada en /chat/imagen: {respuesta}")
        return {
            "descripcion_imagen": descripcion,
            "respuesta_agente": respuesta.get("respuesta", "")
        }
    except Exception as e:
        logging.error(f"Error en /chat/imagen: {str(e)}")
        return {"descripcion_imagen": "Esta función aún no está disponible.", "respuesta_agente": "Esta función aún no está disponible."}

# --- Texto ---
class ChatTextoRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "gemini"

@router.post("/texto", summary="Procesa solo texto con LLM de texto", response_model=Dict[str, Any])
async def chat_texto(request: Request, db: AsyncSession = Depends(get_db)):
    logging.info("[chat_texto] Recibida petición en /chat/texto")
    data = await request.json()
    logging.info(f"[chat_texto] Payload recibido: {data}")
    try:
        chat_id = str(data.get("chat_id", "pruebas"))
        mensaje_usuario = data["mensaje"]

        # NUEVO: Permitir 'tipo' explícito, o clasificar si no viene
        tipo = data.get("tipo")
        if not tipo:
            from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
            tipo = clasificar_tipo_mensaje_llm(mensaje_usuario)
        logging.info(f"[chat_texto] Tipo de consulta final: {tipo}")

        # Detectar si hay una venta pendiente de confirmación para este chat
        result = await db.execute(
            select(Mensaje).where(
                Mensaje.chat_id == chat_id,
                Mensaje.estado_venta == "pendiente"
            ).order_by(Mensaje.timestamp.desc())
        )
        venta_pendiente = result.scalars().first()
        confirmaciones = ["si", "sí", "confirmo", "ok", "dale", "de acuerdo", "acepto", "listo"]
        if venta_pendiente and any(c in mensaje_usuario.lower() for c in confirmaciones):
            await db.execute(
                insert(Mensaje).values(
                    chat_id=chat_id,
                    remitente="bot",
                    mensaje="¡Listo! Pedido registrado. Pronto te contactaremos para coordinar la entrega.",
                    timestamp=datetime.utcnow(),
                    estado_venta="cerrada"
                )
            )
            venta_pendiente.estado_venta = "cerrada"
            await db.commit()
            return {"respuesta": "¡Listo! Pedido registrado. Pronto te contactaremos para coordinar la entrega."}

        # Persistir mensaje de usuario
        await db.execute(insert(Mensaje).values(
            chat_id=chat_id,
            remitente="usuario",
            mensaje=mensaje_usuario,
            timestamp=datetime.utcnow(),
            estado_venta=None
        ))

        respuesta = await consultar_rag(
            mensaje=mensaje_usuario,
            tipo=tipo,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa="Sextinvalle",
            tono=data.get("tono", "formal"),
            instrucciones=data.get("instrucciones", ""),
            llm=data.get("llm", "gemini")
        )
        logging.info(f"[chat_texto] Respuesta de consultar_rag: {respuesta}")
        logging.info("[chat_texto] Justo antes de return")
        logging.info(f"[chat_texto] Mensaje del usuario: {mensaje_usuario}")
        logging.info(f"[chat_texto] Respuesta generada: {respuesta.get('respuesta', '')}")

        # Si la respuesta contiene una invitación a confirmar, marcamos venta pendiente
        if any(palabra in respuesta.get("respuesta", "").lower() for palabra in ["¿deseas", "quieres confirmar", "te gustaría agregarlo", "confirmar pedido"]):
            await db.execute(insert(Mensaje).values(
                chat_id=chat_id,
                remitente="bot",
                mensaje=respuesta.get("respuesta", ""),
                timestamp=datetime.utcnow(),
                estado_venta="pendiente"
            ))
        else:
            await db.execute(insert(Mensaje).values(
                chat_id=chat_id,
                remitente="bot",
                mensaje=respuesta.get("respuesta", ""),
                timestamp=datetime.utcnow(),
                estado_venta=None
            ))
        await db.commit()
        return {"respuesta": respuesta.get("respuesta", "")}
    except Exception as e:
        logging.error(f"[chat_texto] Error en /chat/texto: {str(e)}")
        return {"respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes intentarlo de otra forma o preguntar algo más específico?"}

# --- Audio ---
@router.post("/audio", summary="Procesa audio (transcribe y responde)", response_model=Dict[str, Any])
async def chat_audio(audio: UploadFile = File(...), tono: Optional[str] = Form("formal"), instrucciones: Optional[str] = Form(""), llm: Optional[str] = Form("gemini"), db: AsyncSession = Depends(get_db)):
    logging.info("Recibida petición en /chat/audio")
    try:
        audio.file.seek(0, 2)
        size_mb = audio.file.tell() / (1024 * 1024)
        audio.file.seek(0)
        if size_mb > 10:
            raise HTTPException(status_code=400, detail="El audio supera el tamaño máximo de 10MB")
        # --- Transcripción con OpenAI Whisper (API asíncrona v1.x) ---
        try:
            audio_bytes = await audio.read()
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
                tmp_audio.write(audio_bytes)
                tmp_audio.flush()
                tmp_audio.seek(0)
                client = genai.GenerativeModel(llm)
                with open(tmp_audio.name, "rb") as f:
                    transcript = client.generate_content([{"text": "Transcribe este audio"}, {"mime_type": "audio/mpeg", "data": base64.b64encode(f.read()).decode()}])
            transcripcion = transcript.text
        except Exception as e:
            logging.error(f"Error en transcripción Whisper: {str(e)}")
            transcripcion = "Esta función aún no está disponible."
        audio_prompt = prompt_audio(transcripcion)
        respuesta = await consultar_rag(
            mensaje=audio_prompt,
            tipo="contexto",
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa="Sextinvalle",
            tono=tono,
            instrucciones=instrucciones,
            llm=llm
        )
        logging.info(f"Respuesta generada en /chat/audio: {respuesta}")
        return {
            "transcripcion": transcripcion,
            "respuesta": respuesta.get("respuesta", "")
        }
    except Exception as e:
        logging.error(f"Error en /chat/audio: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en /chat/audio")

# --- Smart Router ---
class ChatSmartRequest(BaseModel):
    tipo: Optional[str] = None  # "texto", "imagen", "audio"
    mensaje: Optional[str] = None
    imagen_url: Optional[str] = None
    audio_url: Optional[str] = None
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "gemini"

@router.post("/", summary="Router inteligente: enruta según tipo o payload", response_model=Dict[str, Any])
async def chat_router(
    req: ChatSmartRequest,
    db: AsyncSession = Depends(get_db)
):
    tipo = req.tipo
    if not tipo:
        if req.imagen_url:
            tipo = "imagen"
        elif req.audio_url:
            tipo = "audio"
        elif req.mensaje:
            tipo = "texto"
        else:
            raise HTTPException(status_code=400, detail="No se pudo determinar el tipo de input")
    if tipo == "texto":
        return await chat_texto(ChatTextoRequest(
            mensaje=req.mensaje,
            tono=req.tono,
            instrucciones=req.instrucciones,
            llm=req.llm,
            empresa_id=1  # TODO: Volver a usar empresa_id dinámico en multiempresa
        ), db)
    elif tipo == "imagen":
        return await chat_imagen(
            request=None,
            imagen=None,
            imagen_url=req.imagen_url,
            mensaje=req.mensaje,
            tono=req.tono,
            instrucciones=req.instrucciones,
            llm=req.llm,
            empresa_id=1,  # TODO: Volver a usar empresa_id dinámico en multiempresa
            db=db
        )
    elif tipo == "audio":
        return {"respuesta": "Procesamiento de audio por URL no implementado aún."}
    else:
        raise HTTPException(status_code=400, detail="Tipo de input no soportado")

@router.get("/historial/{chat_id}", summary="Historial de mensajes de un chat", response_model=List[dict])
async def historial_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Mensaje).where(Mensaje.chat_id == chat_id).order_by(Mensaje.timestamp.asc())
    )
    mensajes = result.scalars().all()
    return [
        {
            "id": m.id,
            "chat_id": m.chat_id,
            "remitente": m.remitente,
            "mensaje": m.mensaje,
            "timestamp": m.timestamp.isoformat()
        }
        for m in mensajes
    ]
