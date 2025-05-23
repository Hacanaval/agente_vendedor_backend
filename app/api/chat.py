from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.usuario import Usuario
from app.models.empresa import Empresa
from typing import Dict, Any, Optional
from app.services.rag import consultar_rag
from pydantic import BaseModel, Field
import logging
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
import aiohttp
import tempfile
import os
from app.services.llm_client import generar_respuesta
from app.services.prompts import prompt_vision, prompt_audio

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tipo: Optional[str] = Field(default=None, pattern="^(inventario|contexto|venta)$")
    tono: str = Field(default="formal", pattern="^(formal|informal|amigable|profesional)$")
    instrucciones: str = Field(default="", max_length=500)
    llm: str = Field(default="openai", pattern="^(openai|gemini|cohere|local)$")

@router.post("/", response_model=Dict[str, Any])
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de chat tipo RAG: responde consultas de inventario, venta o contexto según tipo.
    Si 'tipo' no viene, se clasifica automáticamente usando LLM.
    
    - tipo: "inventario" (consulta productos), "contexto" (consulta info empresa) o "venta" (consulta info venta)
    - tono: "formal", "informal", "amigable", "profesional"
    - instrucciones: instrucciones adicionales para el LLM
    - llm: modelo de lenguaje a usar (por ahora solo "openai")
    """
    try:
        empresa_id = getattr(req, "empresa_id", None)
        if not empresa_id:
            raise HTTPException(status_code=400, detail="Debes especificar empresa_id para el chat.")

        # Obtener info de la empresa
        empresa = await db.get(Empresa, empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        # Clasificación automática si no viene tipo
        tipo = req.tipo
        if not tipo:
            tipo = await clasificar_tipo_mensaje_llm(req.mensaje)

        # Consultar RAG
        respuesta = await consultar_rag(
            mensaje=req.mensaje,
            tipo=tipo,
            empresa_id=empresa_id,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa=empresa.nombre,
            tono=req.tono,
            instrucciones=req.instrucciones,
            usuario_id=None,
            llm=req.llm
        )
        
        return respuesta

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error en endpoint chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al procesar la consulta"
        )

# --- Imagen ---
class ChatImagenRequest(BaseModel):
    imagen_url: Optional[str] = None
    mensaje: Optional[str] = None  # prompt adicional opcional
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "gpt-4-vision-preview"

MAX_IMAGE_SIZE_MB = 2
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]

async def procesar_imagen_openai_vision(image_bytes: bytes, prompt: str, llm: str = "gpt-4-vision-preview") -> str:
    """
    Procesa la imagen con OpenAI Vision y retorna la descripción generada.
    Si el LLM no entiende la imagen, retorna un mensaje claro.
    """
    from openai import AsyncOpenAI
    import base64
    client = AsyncOpenAI()
    try:
        # OpenAI Vision espera la imagen como base64
        b64_image = base64.b64encode(image_bytes).decode()
        vision_prompt = prompt_vision(prompt)
        response = await client.chat.completions.create(
            model=llm,
            messages=[
                {"role": "system", "content": vision_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt or "Describe la imagen de forma útil para ventas."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]}
            ],
            max_tokens=256,
            temperature=0.2
        )
        desc = response.choices[0].message.content.strip()
        if not desc or "no puedo" in desc.lower():
            return "No puedo interpretar la imagen con claridad."
        return desc
    except Exception as e:
        logging.error(f"Error en OpenAI Vision: {str(e)}")
        return "No puedo interpretar la imagen con claridad."

@router.post("/imagen", summary="Procesa una imagen (archivo o URL) y responde usando visión + RAG", response_model=Dict[str, Any])
async def chat_imagen(
    request: Request,
    imagen: Optional[UploadFile] = File(None, description="Imagen a procesar (JPEG/PNG, máx 2MB)"),
    imagen_url: Optional[str] = Form(None, description="URL pública de la imagen (opcional)"),
    mensaje: Optional[str] = Form(None, description="Prompt adicional para la imagen (opcional)"),
    tono: Optional[str] = Form("formal"),
    instrucciones: Optional[str] = Form(""),
    llm: Optional[str] = Form("gpt-4-vision-preview"),
    empresa_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para procesar imágenes con OpenAI Vision y pipeline RAG.
    - Acepta imagen como archivo (multipart/form-data) o como URL (campo imagen_url).
    - Tamaño máximo: 2MB. Tipos permitidos: JPEG, PNG.
    - Ejemplo de request (archivo):
      curl -F "imagen=@/ruta/imagen.jpg" -F "mensaje=Describe esto" -F "tono=formal" http://localhost:8000/chat/imagen
    - Ejemplo de request (URL):
      curl -X POST -F "imagen_url=https://.../img.png" http://localhost:8000/chat/imagen
    - Puedes forzar el LLM con el campo 'llm'.
    - Si el LLM no entiende la imagen, lo indica en la respuesta.
    """
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Debes especificar empresa_id para el chat.")

    # 1. Obtener bytes de la imagen
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
        # Descargar la imagen
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

    # 2. Procesar imagen con OpenAI Vision
    descripcion = await procesar_imagen_openai_vision(image_bytes, mensaje, llm=llm)

    # 3. Usar la descripción como entrada al pipeline RAG
    empresa = await db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        respuesta = await consultar_rag(
            mensaje=descripcion,
            tipo="inventario",
            empresa_id=empresa_id,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa=empresa.nombre,
            tono=tono,
            instrucciones=instrucciones,
            usuario_id=None,
            llm=llm
        )
    except Exception as e:
        logging.error(f"Error en pipeline RAG tras procesar imagen: {str(e)}")
        respuesta = {"respuesta": "No se pudo procesar la imagen correctamente.", "contexto": "", "prompt": {}}

    return {
        "descripcion_imagen": descripcion,
        "respuesta_agente": respuesta.get("respuesta", "No se pudo generar respuesta."),
        "contexto": respuesta.get("contexto", ""),
        "prompt": respuesta.get("prompt", {})
    }

# --- Texto ---
class ChatTextoRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "openai"

@router.post("/texto", summary="Procesa solo texto con LLM de texto", response_model=Dict[str, Any])
async def chat_texto(
    req: ChatTextoRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para procesar mensajes de texto con LLM de texto.
    - Ejemplo de request:
      curl -X POST http://localhost:8000/chat/texto -H "Content-Type: application/json" -d '{"mensaje": "¿Qué productos tienen?", "tono": "formal"}'
    - Puedes forzar el LLM con el campo 'llm'.
    """
    empresa_id = getattr(req, "empresa_id", None)
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Debes especificar empresa_id para el chat.")

    empresa = await db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        respuesta = await consultar_rag(
            mensaje=req.mensaje,
            tipo="inventario",
            empresa_id=empresa_id,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa=empresa.nombre,
            tono=req.tono,
            instrucciones=req.instrucciones,
            usuario_id=None,
            llm=req.llm
        )
    except Exception as e:
        logging.error(f"Error en pipeline RAG texto: {str(e)}")
        respuesta = {"respuesta": "No se pudo procesar el mensaje de texto.", "contexto": "", "prompt": {}}
    return respuesta

# --- Audio ---
from fastapi import UploadFile

@router.post("/audio", summary="Procesa audio (stub/mock)", response_model=Dict[str, Any])
async def chat_audio(
    audio: UploadFile = File(..., description="Archivo de audio (máx 10MB, formatos soportados: mp3, wav)"),
    tono: Optional[str] = Form("formal"),
    instrucciones: Optional[str] = Form(""),
    llm: Optional[str] = Form("openai-whisper"),
    empresa_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para procesar audio (stub/mock, integración futura con Whisper/Gemini).
    - Ejemplo de request:
      curl -F "audio=@/ruta/audio.mp3" http://localhost:8000/chat/audio
    - Puedes forzar el LLM/transcriptor con el campo 'llm'.
    - Tamaño máximo recomendado: 10MB.
    """
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Debes especificar empresa_id para el chat.")

    # Validar tipo y tamaño
    audio.file.seek(0, 2)
    size_mb = audio.file.tell() / (1024 * 1024)
    audio.file.seek(0)
    if size_mb > 10:
        raise HTTPException(status_code=400, detail="El audio supera el tamaño máximo de 10MB")
    # TODO: Integrar transcripción real (Whisper, Gemini, etc.)
    transcripcion = "[Transcripción simulada: integración futura con Whisper/Gemini]"
    audio_prompt = prompt_audio(transcripcion)
    empresa = await db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    try:
        respuesta = await consultar_rag(
            mensaje=audio_prompt,
            tipo="contexto",
            empresa_id=empresa_id,
            db=db,
            nombre_agente="Agente Vendedor",
            nombre_empresa=empresa.nombre,
            tono=tono,
            instrucciones=instrucciones,
            usuario_id=None,
            llm=llm
        )
    except Exception as e:
        logging.error(f"Error en pipeline RAG audio: {str(e)}")
        respuesta = {"respuesta": "No se pudo procesar el audio.", "contexto": "", "prompt": {}}
    return {
        "transcripcion": transcripcion,
        **respuesta
    }

# --- Smart Router ---
class ChatSmartRequest(BaseModel):
    tipo: Optional[str] = None  # "texto", "imagen", "audio"
    mensaje: Optional[str] = None
    imagen_url: Optional[str] = None
    audio_url: Optional[str] = None
    tono: Optional[str] = "formal"
    instrucciones: Optional[str] = ""
    llm: Optional[str] = "openai"

@router.post("/", summary="Router inteligente: enruta según tipo o payload", response_model=Dict[str, Any])
async def chat_router(
    req: ChatSmartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Router inteligente que enruta a /chat/texto, /chat/imagen o /chat/audio según el tipo o el payload recibido.
    - Ejemplo de request:
      curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"tipo": "texto", "mensaje": "Hola"}'
    - Puedes forzar el tipo y el LLM con los campos 'tipo' y 'llm'.
    """
    empresa_id = getattr(req, "empresa_id", None)
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Debes especificar empresa_id para el chat.")

    tipo = req.tipo
    if not tipo:
        # Autodetectar según payload
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
            empresa_id=empresa_id
        ), db)
    elif tipo == "imagen":
        # Redirigir a /chat/imagen (solo soporta imagen_url aquí)
        return await chat_imagen(
            request=None,
            imagen=None,
            imagen_url=req.imagen_url,
            mensaje=req.mensaje,
            tono=req.tono,
            instrucciones=req.instrucciones,
            llm=req.llm,
            empresa_id=empresa_id,
            db=db
        )
    elif tipo == "audio":
        # Redirigir a /chat/audio (solo soporta audio_url aquí, integración futura)
        return {"respuesta": "Procesamiento de audio por URL no implementado aún."}
    else:
        raise HTTPException(status_code=400, detail="Tipo de input no soportado")
