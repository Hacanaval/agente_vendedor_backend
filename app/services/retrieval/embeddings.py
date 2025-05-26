# app/services/retrieval/embeddings.py
import os
import logging
import google.generativeai as genai

# Configuración de Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

async def generar_embedding_gemini(texto: str) -> list:
    """
    Genera embeddings usando el modelo de Gemini.
    """
    try:
        # Usar el modelo de embeddings de Google
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texto,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logging.error(f"Error al generar embedding con Gemini: {str(e)}")
        raise

async def get_embedding(texto: str) -> list:
    """
    Función principal para generar embeddings.
    Actualmente solo soporta Gemini.
    """
    return await generar_embedding_gemini(texto)
