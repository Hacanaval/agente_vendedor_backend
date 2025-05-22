import os
from typing import List
from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_embedding(text: str) -> List[float]:
    """
    Genera embeddings usando OpenAI de forma asíncrona.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    
    try:
        response = await client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        raise RuntimeError(f"Error al generar embedding: {str(e)}") 