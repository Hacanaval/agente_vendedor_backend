import os
from typing import Dict, Any, Optional
import asyncio
import logging
import google.generativeai as genai

# Configuración
DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel(DEFAULT_MODEL)

async def generar_respuesta_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    reintentos: int = 3,
    **kwargs
) -> str:
    """
    Genera una respuesta usando OpenAI de forma asíncrona, con reintentos y logging robusto.
    """
    logging.info(f"[generar_respuesta_gemini] Entrada: prompt={prompt[:100]}..., system_prompt={system_prompt[:100] if system_prompt else None}")
    full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
    for intento in range(1, reintentos + 1):
        try:
            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logging.error(f"[generar_respuesta_gemini] Error (intento {intento}): {str(e)}")
            if intento == reintentos:
                raise Exception(f"Error al consultar Gemini tras {reintentos} intentos: {str(e)}")

async def generar_respuesta(prompt: str, llm: str = "gemini", system_prompt: Optional[str] = None, **kwargs) -> str:
    """
    Función principal para generar respuestas usando diferentes LLMs.
    Por ahora solo soporta Gemini (Google), pero está diseñada para ser extensible.
    """
    logging.info(f"[generar_respuesta] Entrada: llm={llm}, prompt={prompt[:100]}..., system_prompt={system_prompt[:100] if system_prompt else None}")
    if llm == "gemini":
        return await generar_respuesta_gemini(prompt, system_prompt=system_prompt, **kwargs)
    else:
        raise ValueError(f"LLM no soportado: {llm}") 