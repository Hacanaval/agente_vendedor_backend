import os
import logging
from typing import Literal
import google.generativeai as genai
from app.services.prompts import SYSTEM_PROMPT_CLASIFICACION

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

DEFAULT_MODEL = os.getenv("LLM_CLASIFICACION_MODEL", "gemini-2.0-flash")
model = genai.GenerativeModel(DEFAULT_MODEL)

async def clasificar_tipo_mensaje_llm(mensaje: str) -> Literal["inventario", "venta", "contexto"]:
    """
    Clasifica un mensaje en 'inventario', 'venta' o 'contexto' usando Gemini (Google).
    Si el resultado no es válido, retorna 'contexto' por defecto.
    """
    prompt = f"{SYSTEM_PROMPT_CLASIFICACION}\nUsuario: {mensaje}\nRespuesta:"
    try:
        response = await model.generate_content_async(prompt)
        categoria = response.text.strip().lower()
        if categoria not in {"inventario", "venta", "contexto"}:
            categoria = "contexto"
        logging.info(f"[clasificar_tipo_mensaje_llm] Mensaje: {mensaje} -> Categoría: {categoria}")
        return categoria
    except Exception as e:
        logging.error(f"[clasificar_tipo_mensaje_llm] Error al clasificar: {str(e)}")
        return "contexto"
