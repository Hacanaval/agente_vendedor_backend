import faiss
import numpy as np
from typing import List, Dict, Any
from app.services.retrieval.embeddings import get_embedding
from app.models.producto import Producto
from sqlalchemy.future import select
import logging
import asyncio

class FAISSRetriever:
    def __init__(self, db):
        self.db = db
        self.index = None
        self.id_map = []  # Mapea posición en FAISS a producto_id

    async def build_index(self):
        try:
            # Cargar todos los productos activos y con stock > 0
            result = await self.db.execute(
                select(Producto).where(
                    Producto.activo == True,
                    Producto.stock > 0
                )
            )
            productos = result.scalars().all()
            if not productos:
                self.index = None
                self.id_map = []
                return
            embeddings = []
            self.id_map = []
            for p in productos:
                emb = await self._get_embedding_with_retries(f"{p.nombre} {p.descripcion}")
                embeddings.append(emb)
                self.id_map.append(p.id)
            arr = np.array(embeddings).astype('float32')
            self.index = faiss.IndexFlatL2(arr.shape[1])
            self.index.add(arr)
        except Exception as e:
            logging.error(f"Error al construir el índice FAISS: {str(e)}")
            self.index = None
            self.id_map = []

    async def search(self, query: str, top_k: int = 5) -> List[int]:
        try:
            if not self.index:
                await self.build_index()
                if not self.index:
                    return []
            emb = np.array([await self._get_embedding_with_retries(query)]).astype('float32')
            D, I = self.index.search(emb, top_k)
            return [self.id_map[i] for i in I[0] if i < len(self.id_map)]
        except Exception as e:
            logging.error(f"Error en búsqueda semántica FAISS: {str(e)}")
            return []

    async def sync_with_db(self):
        await self.build_index()

    async def _get_embedding_with_retries(self, text: str, reintentos: int = 3) -> Any:
        delay = 1
        for intento in range(1, reintentos + 1):
            try:
                return await get_embedding(text)
            except Exception as e:
                logging.error(f"Error al generar embedding (intento {intento}): {str(e)}")
                if intento == reintentos:
                    raise
                await asyncio.sleep(delay)
                delay *= 2 