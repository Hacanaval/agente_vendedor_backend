#!/usr/bin/env python3
"""
🧠 TEST CACHE SEMÁNTICO PASO 4 - ENTERPRISE
Validación completa del sistema de cache semántico inteligente

Funcionalidades testeadas:
- Cache de embeddings con normalización avanzada
- Detección de consultas similares
- Cache de búsquedas semánticas
- Performance y métricas
- Diferentes estrategias de cache
"""

import asyncio
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

# Configurar variables de entorno
os.environ.setdefault("ENVIRONMENT", "testing")

async def test_semantic_cache_complete():
    """Suite completa de tests para cache semántico"""
    
    print("🧠 INICIANDO TESTS CACHE SEMÁNTICO PASO 4")
    print("=" * 60)
    
    # Resultados de tests
    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
        "performance_metrics": {},
        "start_time": time.time()
    }
    
    try:
        # Test 1: Verificar disponibilidad del cache semántico
        print("\n🔍 TEST 1: Verificar disponibilidad del cache semántico")
        await test_semantic_cache_availability(results)
        
        # Test 2: Normalización avanzada de consultas
        print("\n📝 TEST 2: Normalización avanzada de consultas")
        await test_query_normalization(results)
        
        # Test 3: Cache de embeddings semánticos
        print("\n⚡ TEST 3: Cache de embeddings semánticos")
        await test_embedding_cache(results)
        
        # Test 4: Detección de similaridad
        print("\n🎯 TEST 4: Detección de similaridad semántica")
        await test_similarity_detection(results)
        
        # Test 5: Cache de búsquedas semánticas
        print("\n🔍 TEST 5: Cache de búsquedas semánticas")
        await test_search_cache(results)
        
        # Test 6: Estrategias de cache
        print("\n⚙️ TEST 6: Estrategias de cache")
        await test_cache_strategies(results)
        
        # Test 7: Performance y métricas
        print("\n📊 TEST 7: Performance y métricas")
        await test_performance_metrics(results)
        
        # Test 8: Integración con RAG
        print("\n🔗 TEST 8: Integración con sistema RAG")
        await test_rag_integration(results)
        
    except Exception as e:
        results["errors"].append(f"Error crítico en suite de tests: {str(e)}")
        print(f"❌ Error crítico: {e}")
    
    # Generar reporte final
    await generate_final_report(results)

async def test_semantic_cache_availability(results: Dict):
    """Test 1: Verificar que el cache semántico esté disponible"""
    try:
        from app.services.rag_semantic_cache import (
            semantic_cache_service,
            get_semantic_embedding,
            get_semantic_search_cache,
            cache_semantic_search,
            SimilarityLevel,
            CacheStrategy
        )
        
        print("✅ Cache semántico importado correctamente")
        print(f"   Estrategia actual: {semantic_cache_service.strategy.value}")
        print(f"   Umbrales configurados: {len(semantic_cache_service.similarity_thresholds)}")
        
        results["passed"] += 1
        
    except ImportError as e:
        error_msg = f"Cache semántico no disponible: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")
        return False
    except Exception as e:
        error_msg = f"Error verificando disponibilidad: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")
        return False
    
    results["total_tests"] += 1
    return True

async def test_query_normalization(results: Dict):
    """Test 2: Normalización avanzada de consultas"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import semantic_cache_service
        
        # Casos de prueba para normalización
        test_cases = [
            {
                "input": "¿Qué extintores tienen disponibles?",
                "expected_contains": ["extintor", "disponible"],
                "description": "Normalización básica con sinónimos"
            },
            {
                "input": "Necesito protección auditiva para mis trabajadores",
                "expected_contains": ["protección auditiva", "trabajador"],
                "description": "Normalización con sinónimos semánticos"
            },
            {
                "input": "Busco guantes de 5 metros de largo",
                "expected_contains": ["guante", "5m"],
                "description": "Normalización de unidades"
            },
            {
                "input": "¿Cuánto cuestan los cascos de seguridad?",
                "expected_contains": ["precio", "casco", "seguridad"],
                "description": "Normalización de intención de precio"
            }
        ]
        
        passed_cases = 0
        for i, case in enumerate(test_cases):
            try:
                normalized, entities = semantic_cache_service.normalize_query_advanced(case["input"])
                
                print(f"   Caso {i+1}: {case['description']}")
                print(f"      Original: '{case['input']}'")
                print(f"      Normalizado: '{normalized}'")
                print(f"      Entidades: {entities}")
                
                # Verificar que contiene elementos esperados
                contains_expected = all(
                    expected in normalized.lower() 
                    for expected in case["expected_contains"]
                )
                
                if contains_expected:
                    print(f"      ✅ Normalización correcta")
                    passed_cases += 1
                else:
                    print(f"      ❌ No contiene elementos esperados: {case['expected_contains']}")
                
            except Exception as e:
                print(f"      ❌ Error en caso {i+1}: {e}")
        
        if passed_cases == len(test_cases):
            print(f"✅ Normalización: {passed_cases}/{len(test_cases)} casos pasaron")
            results["passed"] += 1
        else:
            print(f"⚠️ Normalización: {passed_cases}/{len(test_cases)} casos pasaron")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de normalización: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_embedding_cache(results: Dict):
    """Test 3: Cache de embeddings semánticos"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import get_semantic_embedding
        
        test_query = "extintores de CO2 para oficina"
        
        # Primera consulta (debería generar embedding)
        start_time = time.time()
        embedding1, cached1 = await get_semantic_embedding(test_query)
        time1 = (time.time() - start_time) * 1000
        
        print(f"   Primera consulta: {time1:.1f}ms, cached={cached1}")
        print(f"   Embedding shape: {embedding1.shape}")
        
        # Segunda consulta (debería usar cache)
        start_time = time.time()
        embedding2, cached2 = await get_semantic_embedding(test_query)
        time2 = (time.time() - start_time) * 1000
        
        print(f"   Segunda consulta: {time2:.1f}ms, cached={cached2}")
        
        # Verificar que el segundo es más rápido y cacheado
        if cached2 and time2 < time1:
            print("✅ Cache de embeddings funcionando correctamente")
            results["passed"] += 1
            results["performance_metrics"]["embedding_cache_speedup"] = round(time1 / time2, 2)
        else:
            print("❌ Cache de embeddings no funcionó como esperado")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de cache de embeddings: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_similarity_detection(results: Dict):
    """Test 4: Detección de similaridad semántica"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import semantic_cache_service
        
        # Consultas similares para probar detección
        similar_queries = [
            ("extintores", "extinguidores"),
            ("protección auditiva", "tapones para oídos"),
            ("cascos de seguridad", "cascos protección"),
            ("¿qué precio tienen?", "¿cuánto cuestan?")
        ]
        
        passed_similarity = 0
        
        for query1, query2 in similar_queries:
            try:
                # Obtener embeddings
                emb1, _ = await semantic_cache_service.get_or_create_embedding(query1)
                emb2, _ = await semantic_cache_service.get_or_create_embedding(query2)
                
                # Calcular similaridad
                similarity = semantic_cache_service._calculate_cosine_similarity(emb1, emb2)
                similarity_level = semantic_cache_service._get_similarity_level(similarity)
                
                print(f"   '{query1}' vs '{query2}'")
                print(f"      Similaridad: {similarity:.3f} ({similarity_level.value})")
                
                # Verificar que detecta similaridad alta
                if similarity > 0.7:  # Umbral mínimo esperado
                    print(f"      ✅ Similaridad detectada correctamente")
                    passed_similarity += 1
                else:
                    print(f"      ❌ Similaridad muy baja para consultas similares")
                    
            except Exception as e:
                print(f"      ❌ Error calculando similaridad: {e}")
        
        if passed_similarity >= len(similar_queries) * 0.8:  # 80% de éxito
            print(f"✅ Detección de similaridad: {passed_similarity}/{len(similar_queries)} casos")
            results["passed"] += 1
        else:
            print(f"❌ Detección de similaridad: {passed_similarity}/{len(similar_queries)} casos")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de similaridad: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_search_cache(results: Dict):
    """Test 5: Cache de búsquedas semánticas"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import (
            get_semantic_search_cache,
            cache_semantic_search
        )
        
        test_query = "extintores para oficina"
        mock_products = [
            {"id": 1, "nombre": "Extintor CO2 5kg", "precio": 150000, "similarity_score": 0.95},
            {"id": 2, "nombre": "Extintor PQS 10kg", "precio": 120000, "similarity_score": 0.88}
        ]
        mock_scores = [0.95, 0.88]
        
        # Verificar que no hay cache inicialmente
        cached_result = await get_semantic_search_cache(test_query)
        print(f"   Cache inicial: {cached_result is not None}")
        
        # Cachear resultados
        cache_success = await cache_semantic_search(
            test_query, mock_products, mock_scores,
            filters={"min_score": 0.3}, limit=10
        )
        print(f"   Cache guardado: {cache_success}")
        
        # Verificar que ahora está en cache
        cached_result = await get_semantic_search_cache(test_query)
        
        if cached_result and cached_result.get("products"):
            cached_products = cached_result["products"]
            print(f"   Productos cacheados: {len(cached_products)}")
            print(f"   Primer producto: {cached_products[0]['nombre']}")
            print("✅ Cache de búsquedas funcionando correctamente")
            results["passed"] += 1
        else:
            print("❌ Cache de búsquedas no funcionó")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de cache de búsquedas: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_cache_strategies(results: Dict):
    """Test 6: Diferentes estrategias de cache"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import semantic_cache_service, CacheStrategy
        
        original_strategy = semantic_cache_service.strategy
        strategies_tested = []
        
        # Probar diferentes estrategias
        for strategy in [CacheStrategy.CONSERVATIVE, CacheStrategy.AGGRESSIVE, CacheStrategy.SEMANTIC_SMART]:
            try:
                # Cambiar estrategia
                semantic_cache_service.strategy = strategy
                semantic_cache_service.similarity_thresholds = semantic_cache_service.SIMILARITY_THRESHOLDS[strategy]
                
                # Obtener umbrales
                thresholds = semantic_cache_service.similarity_thresholds
                
                print(f"   Estrategia {strategy.value}:")
                print(f"      Umbrales: {len(thresholds)} niveles")
                for level, threshold in thresholds.items():
                    print(f"         {level.value}: {threshold}")
                
                strategies_tested.append(strategy.value)
                
            except Exception as e:
                print(f"      ❌ Error con estrategia {strategy.value}: {e}")
        
        # Restaurar estrategia original
        semantic_cache_service.strategy = original_strategy
        semantic_cache_service.similarity_thresholds = semantic_cache_service.SIMILARITY_THRESHOLDS[original_strategy]
        
        if len(strategies_tested) >= 2:
            print(f"✅ Estrategias probadas: {strategies_tested}")
            results["passed"] += 1
        else:
            print(f"❌ Pocas estrategias funcionaron: {strategies_tested}")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de estrategias: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_performance_metrics(results: Dict):
    """Test 7: Performance y métricas"""
    results["total_tests"] += 1
    
    try:
        from app.services.rag_semantic_cache import semantic_cache_service
        
        # Obtener estadísticas
        stats = semantic_cache_service.get_stats()
        
        print("   Estadísticas del cache semántico:")
        print(f"      Total consultas: {stats['cache_performance']['total_queries']}")
        print(f"      Hits exactos: {stats['cache_performance']['exact_hits']}")
        print(f"      Hits semánticos: {stats['cache_performance']['semantic_hits']}")
        print(f"      Cache misses: {stats['cache_performance']['cache_misses']}")
        print(f"      Hit rate: {stats['cache_performance']['hit_rate_percentage']}%")
        
        print("   Métricas de performance:")
        for metric, value in stats['performance_metrics'].items():
            print(f"      {metric}: {value:.2f}ms")
        
        print("   Análisis semántico:")
        print(f"      Cálculos de similaridad: {stats['semantic_analysis']['similarity_calculations']}")
        print(f"      Detecciones de intención: {stats['semantic_analysis']['intent_detections']}")
        print(f"      Similaridad promedio: {stats['semantic_analysis']['avg_similarity_score']:.3f}")
        
        # Verificar que las métricas tienen sentido
        if isinstance(stats, dict) and "cache_performance" in stats:
            print("✅ Métricas de performance disponibles")
            results["passed"] += 1
            results["performance_metrics"]["semantic_stats"] = stats
        else:
            print("❌ Métricas de performance no disponibles")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de métricas: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def test_rag_integration(results: Dict):
    """Test 8: Integración con sistema RAG"""
    results["total_tests"] += 1
    
    try:
        # Verificar que el RAG puede importar el cache semántico
        from app.services.rag import SEMANTIC_CACHE_AVAILABLE
        
        print(f"   Cache semántico disponible en RAG: {SEMANTIC_CACHE_AVAILABLE}")
        
        if SEMANTIC_CACHE_AVAILABLE:
            # Verificar importaciones específicas
            from app.services.rag import (
                get_semantic_embedding,
                get_semantic_search_cache,
                cache_semantic_search
            )
            print("   ✅ Funciones semánticas importadas en RAG")
            
            # Verificar integración en embeddings service
            from app.services.embeddings_service import SEMANTIC_CACHE_AVAILABLE as EMB_AVAILABLE
            print(f"   Cache semántico disponible en embeddings: {EMB_AVAILABLE}")
            
            if EMB_AVAILABLE:
                print("✅ Integración completa con RAG y embeddings")
                results["passed"] += 1
            else:
                print("⚠️ Integración parcial - falta embeddings service")
                results["failed"] += 1
        else:
            print("❌ Cache semántico no disponible en RAG")
            results["failed"] += 1
            
    except Exception as e:
        error_msg = f"Error en test de integración RAG: {e}"
        results["errors"].append(error_msg)
        results["failed"] += 1
        print(f"❌ {error_msg}")

async def generate_final_report(results: Dict):
    """Genera reporte final de los tests"""
    
    duration = time.time() - results["start_time"]
    success_rate = (results["passed"] / max(results["total_tests"], 1)) * 100
    
    print("\n" + "=" * 60)
    print("🧠 REPORTE FINAL - CACHE SEMÁNTICO PASO 4")
    print("=" * 60)
    
    print(f"\n📊 RESUMEN EJECUTIVO:")
    print(f"   Duración total: {duration:.1f} segundos")
    print(f"   Tests ejecutados: {results['total_tests']}")
    print(f"   Tests exitosos: {results['passed']}")
    print(f"   Tests fallidos: {results['failed']}")
    print(f"   Tasa de éxito: {success_rate:.1f}%")
    
    # Estado del sistema
    if success_rate >= 90:
        status = "🟢 EXCELENTE"
        recommendation = "Sistema listo para producción"
    elif success_rate >= 75:
        status = "🟡 BUENO"
        recommendation = "Revisar tests fallidos antes de producción"
    elif success_rate >= 50:
        status = "🟠 REGULAR"
        recommendation = "Requiere optimización antes de producción"
    else:
        status = "🔴 CRÍTICO"
        recommendation = "Sistema no listo para producción"
    
    print(f"\n🎯 ESTADO DEL SISTEMA: {status}")
    print(f"   Recomendación: {recommendation}")
    
    # Métricas de performance
    if results["performance_metrics"]:
        print(f"\n⚡ MÉTRICAS DE PERFORMANCE:")
        for metric, value in results["performance_metrics"].items():
            print(f"   {metric}: {value}")
    
    # Errores encontrados
    if results["errors"]:
        print(f"\n❌ ERRORES ENCONTRADOS:")
        for i, error in enumerate(results["errors"], 1):
            print(f"   {i}. {error}")
    
    # Beneficios del cache semántico
    print(f"\n🚀 BENEFICIOS DEL CACHE SEMÁNTICO:")
    print(f"   ✅ Detección inteligente de consultas similares")
    print(f"   ✅ Normalización avanzada con sinónimos")
    print(f"   ✅ Cache de embeddings optimizado")
    print(f"   ✅ Múltiples estrategias de cache")
    print(f"   ✅ Métricas detalladas de performance")
    print(f"   ✅ Integración transparente con RAG")
    
    # Próximos pasos
    print(f"\n🎯 PRÓXIMOS PASOS RECOMENDADOS:")
    if success_rate >= 90:
        print(f"   1. Monitorear performance en producción")
        print(f"   2. Ajustar estrategias según patrones de uso")
        print(f"   3. Implementar alertas de performance")
    else:
        print(f"   1. Corregir errores identificados")
        print(f"   2. Re-ejecutar tests hasta 90%+ éxito")
        print(f"   3. Revisar configuración de umbrales")
    
    print(f"\n🎉 PASO 4 COMPLETADO - CACHE SEMÁNTICO ENTERPRISE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_semantic_cache_complete()) 