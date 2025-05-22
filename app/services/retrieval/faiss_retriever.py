import faiss
import numpy as np
from typing import List, Dict, Any
from app.services.retrieval.embeddings import get_embedding
from app.models.producto import Producto
from sqlalchemy.future import select

class FAISSRetriever:
    def __init__(self, empresa_id: int, db):
        self.empresa_id = empresa_id
        self.db = db
        self.index = None
        self.id_map = []  # Mapea posición en FAISS a producto_id

    async def build_index(self):
        # Cargar productos de la empresa y crear embeddings
        result = await self.db.execute(select(Producto).where(Producto.empresa_id == self.empresa_id))
        productos = result.scalars().all()
        if not productos:
            self.index = None
            self.id_map = []
            return
        embeddings = []
        self.id_map = []
        for p in productos:
            emb = await get_embedding(f"{p.nombre} {p.descripcion}")
            embeddings.append(emb)
            self.id_map.append(p.id)
        arr = np.array(embeddings).astype('float32')
        self.index = faiss.IndexFlatL2(arr.shape[1])
        self.index.add(arr)

    async def search(self, query: str, top_k: int = 5) -> List[int]:
        if not self.index:
            await self.build_index()
            if not self.index:
                return []
        emb = np.array([await get_embedding(query)]).astype('float32')
        D, I = self.index.search(emb, top_k)
        return [self.id_map[i] for i in I[0] if i < len(self.id_map)]

    async def sync_with_db(self):
        await self.build_index() 