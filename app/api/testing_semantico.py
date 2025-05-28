"""
API de Testing para Búsqueda Semántica
Endpoint temporal para probar y comparar búsqueda híbrida vs tradicional
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging

from app.core.database import get_db
from app.services.embeddings_service import (
    search_products_semantic, 
    get_embeddings_stats,
    initialize_embeddings
)
from app.services.rag import _busqueda_tradicional, _handle_consulta_general
from app.models.responses import StatusEnum

router = APIRouter(prefix="/testing", tags=["Testing Semántico"])
logger = logging.getLogger(__name__)

@router.get("/embeddings/stats")
async def get_stats():
    """Obtiene estadísticas del sistema de embeddings"""
    try:
        stats = get_embeddings_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embeddings/initialize")
async def initialize_embeddings_endpoint(
    force_rebuild: bool = Query(False, description="Forzar reconstrucción del índice")
):
    """Inicializa o reconstruye el índice de embeddings"""
    try:
        start_time = datetime.now()
        
        await initialize_embeddings(force_rebuild=force_rebuild)
        
        duration = (datetime.now() - start_time).total_seconds()
        stats = get_embeddings_stats()
        
        return {
            "status": "success",
            "message": "Embeddings inicializados correctamente",
            "duration_seconds": duration,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error inicializando embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/search/semantic")
async def test_search_semantic(
    q: str = Query(..., description="Consulta de búsqueda"),
    top_k: int = Query(10, description="Número máximo de resultados"),
    min_score: float = Query(0.3, description="Score mínimo de similaridad")
):
    """Prueba la búsqueda semántica pura"""
    try:
        start_time = datetime.now()
        
        results = await search_products_semantic(q, top_k)
        
        # Filtrar por score mínimo
        filtered_results = [r for r in results if r.get('similarity_score', 0) >= min_score]
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "status": "success",
            "query": q,
            "method": "semantic_only",
            "results_count": len(filtered_results),
            "duration_ms": round(duration, 2),
            "results": filtered_results,
            "performance": {
                "total_results": len(results),
                "filtered_results": len(filtered_results),
                "avg_score": sum(r.get('similarity_score', 0) for r in filtered_results) / len(filtered_results) if filtered_results else 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/traditional")
async def test_search_traditional(
    q: str = Query(..., description="Consulta de búsqueda"),
    db: AsyncSession = Depends(get_db)
):
    """Prueba la búsqueda tradicional"""
    try:
        start_time = datetime.now()
        
        results = await _busqueda_tradicional(q, db)
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "status": "success",
            "query": q,
            "method": "traditional_only",
            "results_count": len(results),
            "duration_ms": round(duration, 2),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en búsqueda tradicional: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/compare")
async def compare_search_methods(
    q: str = Query(..., description="Consulta de búsqueda"),
    top_k: int = Query(10, description="Número máximo de resultados"),
    db: AsyncSession = Depends(get_db)
):
    """Compara búsqueda semántica vs tradicional"""
    try:
        # Búsqueda semántica
        semantic_start = datetime.now()
        semantic_results = await search_products_semantic(q, top_k)
        semantic_duration = (datetime.now() - semantic_start).total_seconds() * 1000
        
        # Búsqueda tradicional
        traditional_start = datetime.now()
        traditional_results = await _busqueda_tradicional(q, db)
        traditional_duration = (datetime.now() - traditional_start).total_seconds() * 1000
        
        # Análisis de solapamiento
        semantic_ids = {r['id'] for r in semantic_results}
        traditional_ids = {r['id'] for r in traditional_results}
        overlap_ids = semantic_ids & traditional_ids
        
        # Productos únicos por método
        semantic_only = semantic_ids - traditional_ids
        traditional_only = traditional_ids - semantic_ids
        
        return {
            "status": "success",
            "query": q,
            "comparison": {
                "semantic": {
                    "count": len(semantic_results),
                    "duration_ms": round(semantic_duration, 2),
                    "avg_score": sum(r.get('similarity_score', 0) for r in semantic_results) / len(semantic_results) if semantic_results else 0,
                    "results": semantic_results
                },
                "traditional": {
                    "count": len(traditional_results),
                    "duration_ms": round(traditional_duration, 2),
                    "results": traditional_results
                },
                "overlap": {
                    "common_products": len(overlap_ids),
                    "semantic_only": len(semantic_only),
                    "traditional_only": len(traditional_only),
                    "overlap_percentage": round(len(overlap_ids) / max(len(semantic_ids), len(traditional_ids), 1) * 100, 1)
                },
                "performance": {
                    "semantic_faster": semantic_duration < traditional_duration,
                    "speed_difference_ms": round(abs(semantic_duration - traditional_duration), 2),
                    "performance_ratio": round(traditional_duration / semantic_duration, 2) if semantic_duration > 0 else "N/A"
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparando métodos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/test-cases")
async def run_test_cases(db: AsyncSession = Depends(get_db)):
    """Ejecuta casos de prueba predefinidos para evaluar efectividad"""
    
    test_cases = [
        # Casos semánticamente complejos
        {"query": "protección auditiva", "expected_contains": ["tapones"], "description": "Sinónimo semántico"},
        {"query": "equipo contra incendios", "expected_contains": ["extintor"], "description": "Contexto semántico"},
        {"query": "protección para los ojos", "expected_contains": ["gafa"], "description": "Descripción funcional"},
        {"query": "seguridad en alturas", "expected_contains": ["arnés"], "description": "Contexto de uso"},
        
        # Casos tradicionales
        {"query": "extintor", "expected_contains": ["extintor"], "description": "Búsqueda exacta"},
        {"query": "casco", "expected_contains": ["casco"], "description": "Palabra clave directa"},
        
        # Casos con números/especificaciones
        {"query": "extintor 10 libras", "expected_contains": ["10"], "description": "Especificación numérica"},
        {"query": "botiquín 20 personas", "expected_contains": ["20"], "description": "Capacidad específica"},
    ]
    
    results = []
    total_start = datetime.now()
    
    for test_case in test_cases:
        query = test_case["query"]
        
        try:
            # Probar búsqueda semántica
            semantic_results = await search_products_semantic(query, 5)
            
            # Probar búsqueda tradicional
            traditional_results = await _busqueda_tradicional(query, db)
            
            # Evaluar efectividad
            semantic_matches = any(
                any(expected.lower() in result['nombre'].lower() for expected in test_case['expected_contains'])
                for result in semantic_results
            )
            
            traditional_matches = any(
                any(expected.lower() in result['nombre'].lower() for expected in test_case['expected_contains'])
                for result in traditional_results
            )
            
            results.append({
                "query": query,
                "description": test_case["description"],
                "expected_contains": test_case["expected_contains"],
                "semantic": {
                    "found_match": semantic_matches,
                    "results_count": len(semantic_results),
                    "top_result": semantic_results[0]['nombre'] if semantic_results else None,
                    "top_score": semantic_results[0].get('similarity_score') if semantic_results else None
                },
                "traditional": {
                    "found_match": traditional_matches,
                    "results_count": len(traditional_results),
                    "top_result": traditional_results[0]['nombre'] if traditional_results else None
                },
                "winner": "semantic" if semantic_matches and not traditional_matches else 
                         "traditional" if traditional_matches and not semantic_matches else
                         "both" if semantic_matches and traditional_matches else "none"
            })
            
        except Exception as e:
            logger.error(f"Error en test case '{query}': {e}")
            results.append({
                "query": query,
                "description": test_case["description"],
                "error": str(e)
            })
    
    total_duration = (datetime.now() - total_start).total_seconds()
    
    # Calcular estadísticas
    successful_tests = [r for r in results if 'error' not in r]
    semantic_wins = len([r for r in successful_tests if r['winner'] in ['semantic', 'both']])
    traditional_wins = len([r for r in successful_tests if r['winner'] in ['traditional', 'both']])
    
    return {
        "status": "success",
        "total_tests": len(test_cases),
        "successful_tests": len(successful_tests),
        "duration_seconds": round(total_duration, 2),
        "summary": {
            "semantic_effective": semantic_wins,
            "traditional_effective": traditional_wins,
            "semantic_success_rate": round(semantic_wins / len(successful_tests) * 100, 1) if successful_tests else 0,
            "traditional_success_rate": round(traditional_wins / len(successful_tests) * 100, 1) if successful_tests else 0
        },
        "detailed_results": results,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health")
async def health_check():
    """Health check del sistema de embeddings"""
    try:
        stats = get_embeddings_stats()
        
        return {
            "status": "healthy" if stats.get('initialized', False) else "initializing",
            "embeddings_ready": stats.get('initialized', False),
            "total_products": stats.get('total_products', 0),
            "model": stats.get('model_name', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 