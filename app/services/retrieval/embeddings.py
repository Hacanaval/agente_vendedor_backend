import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("embedding-001") # (o el modelo de embedding que corresponda en Gemini)

async def generar_embedding_gemini(texto: str) -> list:
    """
    Genera embeddings usando Gemini (Google) de forma asíncrona.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY no configurada")
    try:
        # (adaptar según la API de Gemini para embeddings, por ejemplo, usando model.embed_content)
        response = model.embed_content(texto)
        return response.embedding
    except Exception as e:
        logging.error(f"Error al generar embedding con Gemini: {str(e)}")
        raise 