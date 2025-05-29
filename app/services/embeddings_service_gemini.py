"""
Servicio de Embeddings usando Google Gemini
Alternativa segura para evitar problemas de compatibilidad con sentence-transformers
"""
import os
import asyncio
import numpy as np
import faiss
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib
import google.generativeai as genai

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.producto import Producto

logger = logging.getLogger(__name__)

# Configuración
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

EMBEDDING_DIMENSION = 768  # Dimensión estándar de Gemini embeddings
EMBEDDINGS_CACHE_DIR = Path("embeddings_cache")
INDEX_FILE = EMBEDDINGS_CACHE_DIR / "faiss_index_gemini.bin"
METADATA_FILE = EMBEDDINGS_CACHE_DIR / "metadata_gemini.pkl"

class EmbeddingsServiceGemini:
    """
    Servicio de Embeddings usando Google Gemini
    
    Características:
    - Usa Google Gemini para generar embeddings
    - Índice FAISS para búsqueda rápida
    - Cache en disco para persistencia
    - Compatible con Python 3.13
    """
    
    def __init__(self):
        self.index: Optional[faiss.IndexFlatIP] = None
        self.product_metadata: List[Dict[str, Any]] = []
        self.is_initialized = False
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Asegura que el directorio de cache existe"""
        EMBEDDINGS_CACHE_DIR.mkdir(exist_ok=True)
    
    async def initialize(self, force_rebuild: bool = False):
        """Inicializa el servicio de embeddings"""
        try:
            logger.info("🚀 Inicializando servicio de embeddings con Gemini...")
            
            # Cargar o construir índice
            if force_rebuild or not self._index_exists():
                logger.info("📦 Construyendo nuevo índice FAISS con Gemini...")
                await self._build_index_from_db()
            else:
                logger.info("📂 Cargando índice FAISS existente...")
                await self._load_index()
            
            self.is_initialized = True
            logger.info(f"✅ Servicio inicializado - {len(self.product_metadata)} productos indexados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando embeddings: {e}")
            raise
    
    def _index_exists(self) -> bool:
        """Verifica si existe el índice FAISS"""
        return INDEX_FILE.exists() and METADATA_FILE.exists()
    
    async def _generate_embedding_gemini(self, text: str) -> np.ndarray:
        """Genera embedding usando Google Gemini"""
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            embedding = np.array(result['embedding'], dtype='float32')
            
            # Normalizar para similaridad coseno
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding con Gemini: {e}")
            # Fallback: embedding aleatorio normalizado
            embedding = np.random.rand(EMBEDDING_DIMENSION).astype('float32')
            return embedding / np.linalg.norm(embedding)
    
    async def _build_index_from_db(self):
        """Construye el índice FAISS desde la base de datos"""
        from app.core.database import get_db
        
        try:
            # Obtener productos de la BD
            db_gen = get_db()
            db = await db_gen.__anext__()
            
            try:
                result = await db.execute(
                    select(Producto).where(Producto.activo == True)
                )
                productos = result.scalars().all()
                
                if not productos:
                    logger.warning("⚠️ No hay productos activos para indexar")
                    self._create_empty_index()
                    return
                
                logger.info(f"📊 Procesando {len(productos)} productos...")
                
                # Preparar textos y metadata
                texts = []
                metadata = []
                
                for producto in productos:
                    text = self._prepare_product_text(producto)
                    texts.append(text)
                    
                    metadata.append({
                        'id': producto.id,
                        'nombre': producto.nombre,
                        'categoria': producto.categoria,
                        'descripcion': producto.descripcion or '',
                        'precio': float(producto.precio),
                        'stock': producto.stock,
                        'texto_indexado': text
                    })
                
                # Generar embeddings con Gemini (en lotes pequeños para evitar rate limits)
                logger.info("🧠 Generando embeddings con Gemini...")
                embeddings = []
                
                for i, text in enumerate(texts):
                    if i % 10 == 0:
                        logger.info(f"Procesando {i+1}/{len(texts)}...")
                    
                    embedding = await self._generate_embedding_gemini(text)
                    embeddings.append(embedding)
                    
                    # Pequeña pausa para evitar rate limits
                    await asyncio.sleep(0.1)
                
                embeddings_array = np.array(embeddings, dtype='float32')
                
                # Crear índice FAISS
                self._create_faiss_index(embeddings_array, metadata)
                
                # Guardar en disco
                await self._save_index()
                
                logger.info(f"✅ Índice construido exitosamente: {len(metadata)} productos")
                
            finally:
                await db.close()
                
        except Exception as e:
            logger.error(f"❌ Error construyendo índice: {e}")
            raise
    
    def _prepare_product_text(self, producto: Producto) -> str:
        """Prepara texto optimizado para embeddings"""
        parts = [producto.nombre]
        
        if producto.categoria:
            parts.append(producto.categoria)
        
        if producto.descripcion:
            parts.append(producto.descripcion)
        
        return " | ".join(parts)
    
    def _create_faiss_index(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Crea el índice FAISS"""
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.index.add(embeddings)
        self.product_metadata = metadata
        
        logger.info(f"📊 Índice FAISS creado: {self.index.ntotal} vectores")
    
    def _create_empty_index(self):
        """Crea un índice vacío"""
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.product_metadata = []
    
    async def _save_index(self):
        """Guarda el índice y metadata en disco"""
        try:
            # Guardar índice FAISS
            faiss.write_index(self.index, str(INDEX_FILE))
            
            # Guardar metadata
            with open(METADATA_FILE, 'wb') as f:
                pickle.dump(self.product_metadata, f)
            
            logger.info("💾 Índice guardado en disco")
            
        except Exception as e:
            logger.error(f"❌ Error guardando índice: {e}")
            raise
    
    async def _load_index(self):
        """Carga el índice desde disco"""
        try:
            # Cargar índice FAISS
            self.index = faiss.read_index(str(INDEX_FILE))
            
            # Cargar metadata
            with open(METADATA_FILE, 'rb') as f:
                self.product_metadata = pickle.load(f)
            
            logger.info(f"📂 Índice cargado: {len(self.product_metadata)} productos")
            
        except Exception as e:
            logger.error(f"❌ Error cargando índice: {e}")
            raise
    
    async def search_products(
        self, 
        query: str, 
        top_k: int = 10,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Búsqueda semántica de productos"""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.product_metadata:
            return []
        
        try:
            start_time = datetime.now()
            
            # Generar embedding de la consulta
            query_embedding = await self._generate_embedding_gemini(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Búsqueda en índice FAISS
            scores, indices = self.index.search(query_embedding, min(top_k, len(self.product_metadata)))
            
            # Preparar resultados
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or score < min_score:
                    continue
                
                product = self.product_metadata[idx].copy()
                product['similarity_score'] = float(score)
                product['search_method'] = 'semantic_gemini'
                results.append(product)
            
            # Métricas de performance
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"🔍 Búsqueda completada: {len(results)} resultados en {duration:.1f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda semántica: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio"""
        return {
            "is_initialized": self.is_initialized,
            "total_products": len(self.product_metadata),
            "embedding_model": "google/text-embedding-004",
            "embedding_dimension": EMBEDDING_DIMENSION,
            "index_type": "FAISS IndexFlatIP",
            "cache_files_exist": self._index_exists()
        }

# Instancia global
embeddings_service_gemini = EmbeddingsServiceGemini()

# Funciones de conveniencia
async def initialize_embeddings_gemini(force_rebuild: bool = False):
    """Inicializa el servicio de embeddings con Gemini"""
    return await embeddings_service_gemini.initialize(force_rebuild)

async def search_products_semantic_gemini(
    query: str, 
    top_k: int = 10, 
    min_score: float = 0.3
) -> List[Dict[str, Any]]:
    """Búsqueda semántica usando Gemini"""
    return await embeddings_service_gemini.search_products(query, top_k, min_score)

def get_embeddings_stats_gemini() -> Dict[str, Any]:
    """Obtiene estadísticas del servicio Gemini"""
    return embeddings_service_gemini.get_stats() 