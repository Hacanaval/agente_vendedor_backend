import os
from app.services.retrieval.faiss_retriever import FAISSRetriever
from app.services.retrieval.pinecone_retriever import PineconeRetriever

def get_retriever(db):
    backend = os.getenv("RETRIEVER_BACKEND", "faiss")
    if backend == "faiss":
        return FAISSRetriever(db)
    elif backend == "pinecone":
        return PineconeRetriever(db)
    else:
        raise ValueError(f"Backend de retrieval no soportado: {backend}") 