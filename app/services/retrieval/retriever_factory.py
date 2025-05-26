import os
from app.services.retrieval.faiss_retriever import FAISSRetriever
from app.services.retrieval.pinecone_retriever import PineconeRetriever

def get_retriever(db, empresa_id=None):
    """
    Factory para obtener el retriever correcto según configuración/env.
    Soporta FAISS (default) y Pinecone, fácil de extender.
    """
    backend = os.getenv("RETRIEVER_BACKEND", "faiss").lower()
    if backend == "faiss":
        return FAISSRetriever(db)
    elif backend == "pinecone":
        # Si Pinecone necesita empresa_id en el constructor, lo pasamos; si no, solo db.
        return PineconeRetriever(empresa_id=empresa_id, db=db) if empresa_id else PineconeRetriever(db=db)
    else:
        raise ValueError(f"Backend de retrieval no soportado: {backend}. Opciones válidas: 'faiss', 'pinecone'.")

