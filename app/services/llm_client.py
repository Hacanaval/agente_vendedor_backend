import os
from typing import Dict, Any, Optional
import openai
from openai import AsyncOpenAI
import asyncio
import logging

# Configuración
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
DEFAULT_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

# Cliente OpenAI async
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generar_respuesta_openai(
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
    logging.info(f"[generar_respuesta_openai] Entrada: prompt={prompt[:100]}..., system_prompt={system_prompt[:100] if system_prompt else None}")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    delay = 1
    for intento in range(1, reintentos + 1):
        try:
            logging.info(f"[generar_respuesta_openai] Llamando a OpenAI (intento {intento})")
            response = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            logging.info(f"[generar_respuesta_openai] Respuesta recibida de OpenAI (intento {intento})")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"[generar_respuesta_openai] Error al consultar OpenAI (intento {intento}): {str(e)}")
            if intento == reintentos:
                raise Exception(f"Error al consultar OpenAI tras {reintentos} intentos: {str(e)}")
            await asyncio.sleep(delay)
            delay *= 2

async def generar_respuesta(
    prompt: str,
    llm: str = "openai",
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """
    Función principal para generar respuestas usando diferentes LLMs.
    Por ahora solo soporta OpenAI, pero está diseñada para ser extensible.
    """
    logging.info(f"[generar_respuesta] Entrada: llm={llm}, prompt={prompt[:100]}..., system_prompt={system_prompt[:100] if system_prompt else None}")
    if llm == "openai":
        logging.info("[generar_respuesta] Antes de llamar a generar_respuesta_openai")
        respuesta = await generar_respuesta_openai(prompt, system_prompt=system_prompt, **kwargs)
        logging.info(f"[generar_respuesta] Respuesta de generar_respuesta_openai: {respuesta[:200]}...")
        return respuesta
    # Aquí puedes agregar otros LLMs en el futuro:
    # elif llm == "gemini":
    #     return await generar_respuesta_gemini(prompt, **kwargs)
    # elif llm == "cohere":
    #     return await generar_respuesta_cohere(prompt, **kwargs)
    # elif llm == "local":
    #     return await generar_respuesta_local(prompt, **kwargs)
    else:
        raise ValueError(f"LLM no soportado: {llm}") 