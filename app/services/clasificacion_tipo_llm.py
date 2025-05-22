import os
from openai import AsyncOpenAI
from app.services.prompts import SYSTEM_PROMPT_CLASIFICACION

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def clasificar_tipo_mensaje_llm(mensaje: str) -> str:
    prompt = SYSTEM_PROMPT_CLASIFICACION.format(mensaje=mensaje)
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1,
        temperature=0,
    )
    categoria = response.choices[0].message.content.strip().lower()
    if categoria not in ["inventario", "venta", "contexto"]:
        categoria = "contexto"
    return categoria 