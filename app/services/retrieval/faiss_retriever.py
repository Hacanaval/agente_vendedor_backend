import faiss
import numpy as np
from typing import List, Any
from app.services.retrieval.embeddings import get_embedding
from app.models.producto import Producto
from sqlalchemy.future import select
import logging
import asyncio

class FAISSRetriever:
    def __init__(self, db):
        self.db = db
        self.index = None
        self.id_map = []  # Posición en FAISS -> producto_id

    async def build_index(self):
        """
        Reconstruye el índice FAISS con productos activos y stock > 0.
        """
        try:
            result = await self.db.execute(
                select(Producto).where(
                    Producto.activo == True,
                    Producto.stock > 0
                )
            )
            productos = result.scalars().all()
            if not productos:
                logging.warning("[FAISSRetriever] No hay productos activos con stock > 0 para indexar.")
                self.index = None
                self.id_map = []
                return

            embeddings = []
            self.id_map = []
            for p in productos:
                try:
                    emb = await self._get_embedding_with_retries(f"{p.nombre} {p.descripcion}")
                    embeddings.append(emb)
                    self.id_map.append(p.id)
                except Exception as emb_err:
                    logging.error(f"[FAISSRetriever] Fallo al crear embedding para producto {p.id} - {p.nombre}: {str(emb_err)}")

            if not embeddings:
                logging.error("[FAISSRetriever] Ningún embedding generado. Index no construido.")
                self.index = None
                self.id_map = []
                return

            arr = np.array(embeddings).astype('float32')
            self.index = faiss.IndexFlatL2(arr.shape[1])
            self.index.add(arr)
            logging.info(f"[FAISSRetriever] Índice FAISS reconstruido: {len(self.id_map)} productos indexados.")
        except Exception as e:
            logging.error(f"[FAISSRetriever] Error al construir el índice FAISS: {str(e)}")
            self.index = None
            self.id_map = []

    async def search(self, query: str, top_k: int = 5) -> List[int]:
        """
        Busca los productos más relevantes para el query.
        """
        try:
            if not self.index or not self.id_map:
                await self.build_index()
                if not self.index or not self.id_map:
                    logging.warning("[FAISSRetriever] Índice vacío al buscar. No hay productos para buscar.")
                    return []

            emb = np.array([await self._get_embedding_with_retries(query)]).astype('float32')
            D, I = self.index.search(emb, top_k)
            # Devuelve IDs válidos (cuidado con resultados fuera de rango)
            return [self.id_map[i] for i in I[0] if 0 <= i < len(self.id_map)]
        except Exception as e:
            logging.error(f"[FAISSRetriever] Error en búsqueda semántica FAISS: {str(e)}")
            return []

    async def sync_with_db(self):
        """
        Forzar reconstrucción del índice FAISS.
        """
        await self.build_index()

    async def _get_embedding_with_retries(self, text: str, reintentos: int = 3) -> Any:
        delay = 1
        for intento in range(1, reintentos + 1):
            try:
                return await get_embedding(text)
            except Exception as e:
                logging.error(f"[FAISSRetriever] Error al generar embedding (intento {intento}): {str(e)}")
                if intento == reintentos:
                    raise
                await asyncio.sleep(delay)
                delay *= 2

