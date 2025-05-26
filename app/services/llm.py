import os
import logging
from typing import Optional, Dict, Any

# Gemini (Google)
import google.generativeai as genai

# OpenAI (descomentar si lo usas)
# import openai
# from openai import AsyncOpenAI

# TODO: Agrega imports de Claude, Ollama, u otros cuando los integres

# Configuración
DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS", "300"))
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))

# Configuración de Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel(DEFAULT_MODEL)

# Configuración OpenAI (asíncrono) — solo si lo activas
# client_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generar_respuesta(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    reintentos: int = 3,
    **kwargs
) -> str:
    """
    Genera una respuesta usando Gemini (Google).
    Soporta: Gemini (Google), y fácilmente extensible.
    """
    logging.info(f"[generar_respuesta] Entrada: prompt={prompt[:100]}..., system_prompt={system_prompt[:100] if system_prompt else None}")
    full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
    for intento in range(1, reintentos + 1):
        try:
            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logging.error(f"[generar_respuesta] Error (intento {intento}): {str(e)}")
            if intento == reintentos:
                raise Exception(f"Error al consultar Gemini tras {reintentos} intentos: {str(e)}")

# Función sync para scripts sencillos o debugging
def generar_respuesta_llm_sync(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Solo Gemini por ahora. Para usos rápidos en terminal/notebooks.
    """
    full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
    response = model.generate_content(full_prompt)
    return response.text.strip()
