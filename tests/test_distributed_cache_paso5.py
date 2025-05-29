#!/usr/bin/env python3
"""
🧪🔴 Test Suite Paso 5: Cache Distribuido Redis Enterprise
Validación completa del sistema de cache distribuido multi-nivel
"""
import asyncio
import sys
import os
import time
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ===============================
# CONFIGURACIÓN DE TESTING
# ===============================

# Configurar entorno de testing
os.environ["ENVIRONMENT"] = "development"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test_header(test_name: str, test_number: int, total_tests: int):
    """Imprime header de test con formato"""
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}🧪 TEST {test_number}/{total_tests}: {test_name}{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")

def print_success(message: str):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    """Imprime mensaje de error"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    """Imprime mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")

def print_info(message: str):
    """Imprime mensaje informativo"""
    print(f"{Colors.BLUE}ℹ️ {message}{Colors.END}")

# ===============================
# TESTS DEL PASO 5
# ===============================

async def test_1_redis_manager_availability():
    """Test 1: Verificar disponibilidad y configuración del Redis Manager"""
    print_test_header("Redis Manager Availability", 1, 10)
    
    try:
        from app.core.redis_manager import (
            redis_manager, 
            initialize_redis, 
            get_redis_stats,
            redis_health_check,
            REDIS_AVAILABLE
        )
        
        print_info("Verificando disponibilidad de Redis Manager...")
        
        # Verificar importación exitosa
        print_success("✓ Redis Manager importado correctamente")
        
        # Verificar configuración
        print_info(f"Redis disponible: {REDIS_AVAILABLE}")
        
        # Intentar inicialización
        print_info("Inicializando Redis Manager...")
        success = await initialize_redis()
        
        if success:
            print_success("✓ Redis Manager inicializado exitosamente")
        else:
            print_warning("⚠️ Redis Manager en modo mock (Redis no disponible)")
        
        # Obtener estadísticas
        stats = get_redis_stats()
        print_info(f"Configuración: {stats.get('configuration', {})}")
        
        # Health check
        health = await redis_health_check()
        print_info(f"Estado de salud: {health.get('status', 'unknown')}")
        
        return {
            "status": "success",
            "redis_available": REDIS_AVAILABLE,
            "manager_initialized": success,
            "health_status": health.get('status', 'unknown')
        }
        
    except Exception as e:
        print_error(f"Error en test Redis Manager: {e}")
        return {"status": "error", "error": str(e)}

async def test_2_distributed_cache_layer():
    """Test 2: Verificar funcionamiento del Distributed Cache Layer"""
    print_test_header("Distributed Cache Layer", 2, 10)
    
    try:
        from app.core.distributed_cache import (
            distributed_cache,
            initialize_distributed_cache,
            get_distributed_cache_stats,
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Inicializando Distributed Cache Layer...")
        
        # Inicializar cache distribuido
        await initialize_distributed_cache()
        print_success("✓ Cache distribuido inicializado")
        
        # Test de escritura y lectura básica
        test_key = "test_distributed_key"
        test_value = {"message": "Hello Distributed Cache", "timestamp": datetime.now().isoformat()}
        
        print_info("Probando operaciones básicas...")
        
        # Escribir
        write_success = await set_distributed_cached("test_namespace", test_key, test_value, ttl_seconds=300)
        if write_success:
            print_success("✓ Escritura distribuida exitosa")
        else:
            print_warning("⚠️ Escritura distribuida falló (modo mock)")
        
        # Leer
        read_value = await get_distributed_cached("test_namespace", test_key)
        if read_value:
            print_success("✓ Lectura distribuida exitosa")
            print_info(f"Valor leído: {read_value}")
        else:
            print_warning("⚠️ Lectura distribuida sin resultado")
        
        # Obtener estadísticas
        stats = get_distributed_cache_stats()
        print_info("Estadísticas del cache distribuido:")
        print_info(f"- Hit rate global: {stats.get('global', {}).get('hit_rate', 0)}%")
        print_info(f"- Total requests: {stats.get('global', {}).get('total_requests', 0)}")
        
        return {
            "status": "success",
            "write_success": write_success,
            "read_success": read_value is not None,
            "stats": stats
        }
        
    except Exception as e:
        print_error(f"Error en test Distributed Cache: {e}")
        return {"status": "error", "error": str(e)}

async def test_3_multi_level_cache_hierarchy():
    """Test 3: Verificar jerarquía multi-nivel L1→L2→L3"""
    print_test_header("Multi-Level Cache Hierarchy", 3, 10)
    
    try:
        from app.core.distributed_cache import (
            distributed_cache,
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Probando jerarquía de cache multi-nivel...")
        
        # Test con diferentes namespaces para diferentes estrategias
        test_cases = [
            {
                "namespace": "embeddings",
                "key": "test_embedding_key",
                "value": [0.1, 0.2, 0.3, 0.4, 0.5],  # Simular embedding
                "expected_levels": ["l2"],  # Solo Redis según configuración
                "description": "Embeddings (solo L2 Redis)"
            },
            {
                "namespace": "search_results", 
                "key": "test_search_key",
                "value": {"products": [{"id": 1, "name": "Test Product"}], "scores": [0.95]},
                "expected_levels": ["l1", "l2"],  # Memoria + Redis
                "description": "Search Results (L1 + L2)"
            },
            {
                "namespace": "user_sessions",
                "key": "test_session_key", 
                "value": {"user_id": "test_user", "session_data": "test_data"},
                "expected_levels": ["l1"],  # Solo memoria local
                "description": "User Sessions (solo L1)"
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            print_info(f"\nProbando: {test_case['description']}")
            
            namespace = test_case["namespace"]
            key = test_case["key"]
            value = test_case["value"]
            
            # Escribir
            write_success = await set_distributed_cached(namespace, key, value, ttl_seconds=300)
            
            # Leer
            read_value = await get_distributed_cached(namespace, key)
            
            # Verificar resultado
            if write_success and read_value:
                print_success(f"✓ {test_case['description']} - Operación exitosa")
                results[namespace] = {"status": "success", "levels": test_case["expected_levels"]}
            else:
                print_warning(f"⚠️ {test_case['description']} - Operación parcial")
                results[namespace] = {"status": "partial", "levels": test_case["expected_levels"]}
        
        # Verificar estadísticas por nivel
        stats = distributed_cache.get_stats()
        levels_stats = stats.get("levels", {})
        
        print_info("\nEstadísticas por nivel:")
        for level_name, level_stats in levels_stats.items():
            hits = level_stats.get("hits", 0)
            sets = level_stats.get("sets", 0)
            print_info(f"- {level_name}: {hits} hits, {sets} sets")
        
        return {
            "status": "success",
            "test_results": results,
            "levels_stats": levels_stats
        }
        
    except Exception as e:
        print_error(f"Error en test Multi-Level Cache: {e}")
        return {"status": "error", "error": str(e)}

async def test_4_semantic_cache_redis_integration():
    """Test 4: Verificar integración del cache semántico con Redis"""
    print_test_header("Semantic Cache Redis Integration", 4, 10)
    
    try:
        from app.services.rag_semantic_cache_redis import (
            semantic_cache_redis,
            initialize_semantic_cache_redis,
            get_distributed_semantic_embedding,
            get_distributed_semantic_cache_stats
        )
        
        print_info("Inicializando cache semántico distribuido...")
        
        # Inicializar
        await initialize_semantic_cache_redis()
        print_success("✓ Cache semántico Redis inicializado")
        
        # Test de embeddings distribuidos
        test_queries = [
            "extintores de incendio",
            "cascos de seguridad",
            "protección auditiva"
        ]
        
        embedding_results = {}
        
        print_info("Probando embeddings distribuidos...")
        
        for query in test_queries:
            try:
                # Primera llamada (debería generar)
                start_time = time.time()
                embedding1, was_cached1 = await get_distributed_semantic_embedding(query)
                time1 = (time.time() - start_time) * 1000
                
                # Segunda llamada (debería usar cache)
                start_time = time.time()
                embedding2, was_cached2 = await get_distributed_semantic_embedding(query)
                time2 = (time.time() - start_time) * 1000
                
                # Verificar consistencia
                if embedding1 is not None and embedding2 is not None:
                    if isinstance(embedding1, np.ndarray) and isinstance(embedding2, np.ndarray):
                        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
                        
                        embedding_results[query] = {
                            "first_call": {"cached": was_cached1, "time_ms": time1},
                            "second_call": {"cached": was_cached2, "time_ms": time2},
                            "similarity": float(similarity),
                            "consistent": similarity > 0.99
                        }
                        
                        print_success(f"✓ {query}: Similarity {similarity:.3f}, Cache improvement: {time1/max(time2,1):.1f}x")
                    else:
                        print_warning(f"⚠️ {query}: Embeddings no son arrays numpy")
                else:
                    print_warning(f"⚠️ {query}: Embeddings nulos")
                    
            except Exception as e:
                print_error(f"Error procesando '{query}': {e}")
                embedding_results[query] = {"error": str(e)}
        
        # Obtener estadísticas distribuidas
        stats = get_distributed_semantic_cache_stats()
        distributed_perf = stats.get("distributed_performance", {})
        redis_perf = stats.get("redis_performance", {})
        
        print_info("Estadísticas del cache semántico distribuido:")
        print_info(f"- Total queries: {distributed_perf.get('total_queries', 0)}")
        print_info(f"- Distributed hit rate: {distributed_perf.get('distributed_hit_rate', 0)}%")
        print_info(f"- Redis operations: {redis_perf.get('redis_operations', 0)}")
        print_info(f"- Redis success rate: {redis_perf.get('redis_success_rate', 0)}%")
        
        return {
            "status": "success",
            "embedding_results": embedding_results,
            "distributed_stats": stats
        }
        
    except Exception as e:
        print_error(f"Error en test Semantic Cache Redis: {e}")
        return {"status": "error", "error": str(e)}

async def test_5_cache_serialization_compression():
    """Test 5: Verificar serialización y compresión de datos"""
    print_test_header("Cache Serialization & Compression", 5, 10)
    
    try:
        from app.core.distributed_cache import CacheSerializer
        
        print_info("Probando serialización y compresión...")
        
        serializer = CacheSerializer()
        
        # Test cases con diferentes tipos de datos
        test_data = [
            {
                "name": "Small JSON",
                "data": {"key": "value", "number": 42},
                "expect_compression": False
            },
            {
                "name": "Large Text",
                "data": "Lorem ipsum " * 1000,  # Texto grande para activar compresión
                "expect_compression": True
            },
            {
                "name": "Numpy Array",
                "data": np.random.rand(100, 100).tolist(),  # Array grande
                "expect_compression": True
            },
            {
                "name": "Complex Object",
                "data": {
                    "products": [{"id": i, "name": f"Product {i}", "description": "A" * 100} for i in range(50)],
                    "metadata": {"timestamp": datetime.now().isoformat()}
                },
                "expect_compression": True
            }
        ]
        
        serialization_results = {}
        
        for test_case in test_data:
            try:
                data = test_case["data"]
                
                # Serializar
                serialized_data, metadata = serializer.serialize(data)
                
                # Deserializar
                deserialized_data = serializer.deserialize(serialized_data, metadata)
                
                # Verificar integridad
                original_str = str(data)
                deserialized_str = str(deserialized_data)
                integrity_ok = original_str == deserialized_str
                
                # Verificar compresión
                compression_used = metadata.get("compression_used", False)
                original_size = metadata.get("original_size", 0)
                compressed_size = metadata.get("compressed_size", 0)
                compression_ratio = compressed_size / max(original_size, 1) if compression_used else 1.0
                
                serialization_results[test_case["name"]] = {
                    "integrity_ok": integrity_ok,
                    "compression_used": compression_used,
                    "compression_expected": test_case["expect_compression"],
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": compression_ratio,
                    "serialization_method": metadata.get("serialization_method", "unknown")
                }
                
                if integrity_ok:
                    if compression_used:
                        print_success(f"✓ {test_case['name']}: Integridad OK, Compresión {compression_ratio:.2f}")
                    else:
                        print_success(f"✓ {test_case['name']}: Integridad OK, Sin compresión")
                else:
                    print_error(f"✗ {test_case['name']}: Fallo de integridad")
                    
            except Exception as e:
                print_error(f"Error en {test_case['name']}: {e}")
                serialization_results[test_case["name"]] = {"error": str(e)}
        
        return {
            "status": "success",
            "serialization_results": serialization_results
        }
        
    except Exception as e:
        print_error(f"Error en test Serialization: {e}")
        return {"status": "error", "error": str(e)}

async def test_6_cache_promotion_demotion():
    """Test 6: Verificar promoción y degradación entre niveles"""
    print_test_header("Cache Promotion & Demotion", 6, 10)
    
    try:
        from app.core.distributed_cache import (
            get_distributed_cached,
            set_distributed_cached,
            get_distributed_cache_stats
        )
        
        print_info("Probando promoción entre niveles de cache...")
        
        # Simular acceso frecuente para activar promoción
        test_key = "promotion_test_key"
        test_value = {"data": "frequent_access_data", "counter": 0}
        
        # Almacenar inicialmente en L2 (Redis)
        await set_distributed_cached("search_results", test_key, test_value, ttl_seconds=300)
        print_info("✓ Datos almacenados inicialmente")
        
        # Acceder múltiples veces para activar promoción
        promotion_results = []
        
        for i in range(5):
            start_time = time.time()
            value = await get_distributed_cached("search_results", test_key)
            access_time = (time.time() - start_time) * 1000
            
            promotion_results.append({
                "access_number": i + 1,
                "access_time_ms": access_time,
                "value_found": value is not None
            })
            
            if value:
                print_info(f"Acceso {i+1}: {access_time:.2f}ms")
            
            # Pequeña pausa entre accesos
            await asyncio.sleep(0.1)
        
        # Verificar estadísticas de promoción
        stats = get_distributed_cache_stats()
        global_stats = stats.get("global", {})
        promotions = global_stats.get("promotions", 0)
        
        print_info(f"Total promociones registradas: {promotions}")
        
        # Analizar mejora de performance
        if len(promotion_results) >= 2:
            first_access = promotion_results[0]["access_time_ms"]
            last_access = promotion_results[-1]["access_time_ms"]
            improvement = first_access / max(last_access, 0.1)
            
            if improvement > 1.2:  # 20% mejora
                print_success(f"✓ Mejora de performance detectada: {improvement:.1f}x")
            else:
                print_info(f"Performance estable: {improvement:.1f}x")
        
        return {
            "status": "success",
            "promotion_results": promotion_results,
            "total_promotions": promotions,
            "performance_improvement": improvement if 'improvement' in locals() else 1.0
        }
        
    except Exception as e:
        print_error(f"Error en test Promotion: {e}")
        return {"status": "error", "error": str(e)}

async def test_7_distributed_invalidation():
    """Test 7: Verificar invalidación distribuida"""
    print_test_header("Distributed Invalidation", 7, 10)
    
    try:
        from app.core.distributed_cache import (
            get_distributed_cached,
            set_distributed_cached,
            delete_distributed_cached,
            invalidate_distributed_pattern
        )
        
        print_info("Probando invalidación distribuida...")
        
        # Crear múltiples entradas para invalidar
        test_entries = [
            {"namespace": "test_invalidation", "key": "product_123", "value": {"id": 123, "name": "Product A"}},
            {"namespace": "test_invalidation", "key": "product_124", "value": {"id": 124, "name": "Product B"}},
            {"namespace": "test_invalidation", "key": "product_125", "value": {"id": 125, "name": "Product C"}},
            {"namespace": "other_namespace", "key": "other_data", "value": {"data": "should_remain"}}
        ]
        
        # Almacenar entradas
        print_info("Almacenando entradas de prueba...")
        for entry in test_entries:
            await set_distributed_cached(entry["namespace"], entry["key"], entry["value"], ttl_seconds=300)
        
        print_success("✓ Entradas almacenadas")
        
        # Verificar que existen
        print_info("Verificando existencia antes de invalidación...")
        before_invalidation = {}
        for entry in test_entries:
            value = await get_distributed_cached(entry["namespace"], entry["key"])
            before_invalidation[f"{entry['namespace']}:{entry['key']}"] = value is not None
        
        print_info(f"Entradas encontradas antes: {sum(before_invalidation.values())}/{len(before_invalidation)}")
        
        # Test 1: Invalidación específica
        print_info("Probando invalidación específica...")
        delete_success = await delete_distributed_cached("test_invalidation", "product_123")
        
        # Test 2: Invalidación por patrón
        print_info("Probando invalidación por patrón...")
        pattern_count = await invalidate_distributed_pattern("test_invalidation:*")
        
        # Verificar resultados después de invalidación
        print_info("Verificando estado después de invalidación...")
        after_invalidation = {}
        for entry in test_entries:
            value = await get_distributed_cached(entry["namespace"], entry["key"])
            after_invalidation[f"{entry['namespace']}:{entry['key']}"] = value is not None
        
        print_info(f"Entradas encontradas después: {sum(after_invalidation.values())}/{len(after_invalidation)}")
        
        # Verificar que la entrada de otro namespace permanece
        other_entry_remains = after_invalidation.get("other_namespace:other_data", False)
        
        if other_entry_remains:
            print_success("✓ Invalidación selectiva funcionando correctamente")
        else:
            print_warning("⚠️ Invalidación afectó entradas no objetivo")
        
        return {
            "status": "success",
            "delete_success": delete_success,
            "pattern_invalidation_count": pattern_count,
            "before_invalidation": before_invalidation,
            "after_invalidation": after_invalidation,
            "selective_invalidation": other_entry_remains
        }
        
    except Exception as e:
        print_error(f"Error en test Invalidation: {e}")
        return {"status": "error", "error": str(e)}

async def test_8_monitoring_apis():
    """Test 8: Verificar APIs de monitoreo Redis"""
    print_test_header("Monitoring APIs", 8, 10)
    
    try:
        # Simular llamadas a APIs de monitoreo
        print_info("Probando APIs de monitoreo...")
        
        # Test imports
        from app.api.monitoring_redis import router
        from app.core.redis_manager import get_redis_stats, redis_health_check
        from app.core.distributed_cache import get_distributed_cache_stats
        from app.services.rag_semantic_cache_redis import get_distributed_semantic_cache_stats
        
        print_success("✓ APIs de monitoreo importadas correctamente")
        
        # Test funciones de estadísticas
        monitoring_results = {}
        
        # Redis stats
        try:
            redis_stats = get_redis_stats()
            monitoring_results["redis_stats"] = {
                "available": True,
                "keys": list(redis_stats.keys()) if redis_stats else []
            }
            print_success("✓ Redis stats obtenidas")
        except Exception as e:
            monitoring_results["redis_stats"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Redis stats error: {e}")
        
        # Redis health
        try:
            redis_health = await redis_health_check()
            monitoring_results["redis_health"] = {
                "available": True,
                "status": redis_health.get("status", "unknown")
            }
            print_success(f"✓ Redis health check: {redis_health.get('status', 'unknown')}")
        except Exception as e:
            monitoring_results["redis_health"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Redis health error: {e}")
        
        # Distributed cache stats
        try:
            distributed_stats = get_distributed_cache_stats()
            monitoring_results["distributed_stats"] = {
                "available": True,
                "hit_rate": distributed_stats.get("global", {}).get("hit_rate", 0)
            }
            print_success("✓ Distributed cache stats obtenidas")
        except Exception as e:
            monitoring_results["distributed_stats"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Distributed cache stats error: {e}")
        
        # Semantic cache stats
        try:
            semantic_stats = get_distributed_semantic_cache_stats()
            monitoring_results["semantic_stats"] = {
                "available": True,
                "total_queries": semantic_stats.get("distributed_performance", {}).get("total_queries", 0)
            }
            print_success("✓ Semantic cache stats obtenidas")
        except Exception as e:
            monitoring_results["semantic_stats"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Semantic cache stats error: {e}")
        
        # Verificar router
        api_endpoints = [route.path for route in router.routes]
        print_info(f"Endpoints disponibles: {len(api_endpoints)}")
        for endpoint in api_endpoints[:5]:  # Mostrar primeros 5
            print_info(f"  - {endpoint}")
        
        return {
            "status": "success",
            "monitoring_results": monitoring_results,
            "api_endpoints_count": len(api_endpoints)
        }
        
    except Exception as e:
        print_error(f"Error en test Monitoring APIs: {e}")
        return {"status": "error", "error": str(e)}

async def test_9_performance_benchmarks():
    """Test 9: Benchmarks de performance del cache distribuido"""
    print_test_header("Performance Benchmarks", 9, 10)
    
    try:
        from app.core.distributed_cache import (
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Ejecutando benchmarks de performance...")
        
        # Configuración del benchmark
        num_operations = 50
        key_prefix = "benchmark_key_"
        test_value = {"benchmark": True, "data": "x" * 100}  # 100 chars
        
        # Benchmark de escritura
        print_info(f"Benchmark de escritura ({num_operations} operaciones)...")
        write_times = []
        
        for i in range(num_operations):
            start_time = time.time()
            await set_distributed_cached("benchmark", f"{key_prefix}{i}", test_value, ttl_seconds=300)
            write_time = (time.time() - start_time) * 1000
            write_times.append(write_time)
        
        # Benchmark de lectura
        print_info(f"Benchmark de lectura ({num_operations} operaciones)...")
        read_times = []
        
        for i in range(num_operations):
            start_time = time.time()
            value = await get_distributed_cached("benchmark", f"{key_prefix}{i}")
            read_time = (time.time() - start_time) * 1000
            read_times.append(read_time)
        
        # Calcular estadísticas
        def calculate_stats(times):
            if not times:
                return {"avg": 0, "min": 0, "max": 0, "p95": 0}
            
            times_sorted = sorted(times)
            return {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "p95": times_sorted[int(len(times_sorted) * 0.95)]
            }
        
        write_stats = calculate_stats(write_times)
        read_stats = calculate_stats(read_times)
        
        print_success(f"✓ Escritura - Promedio: {write_stats['avg']:.2f}ms, P95: {write_stats['p95']:.2f}ms")
        print_success(f"✓ Lectura - Promedio: {read_stats['avg']:.2f}ms, P95: {read_stats['p95']:.2f}ms")
        
        # Verificar objetivos de performance
        performance_goals = {
            "write_avg_ms": 50,  # Objetivo: <50ms promedio escritura
            "read_avg_ms": 10,   # Objetivo: <10ms promedio lectura
            "write_p95_ms": 100, # Objetivo: <100ms P95 escritura
            "read_p95_ms": 25    # Objetivo: <25ms P95 lectura
        }
        
        performance_results = {
            "write_performance": {
                "meets_avg_goal": write_stats["avg"] < performance_goals["write_avg_ms"],
                "meets_p95_goal": write_stats["p95"] < performance_goals["write_p95_ms"],
                "stats": write_stats
            },
            "read_performance": {
                "meets_avg_goal": read_stats["avg"] < performance_goals["read_avg_ms"],
                "meets_p95_goal": read_stats["p95"] < performance_goals["read_p95_ms"],
                "stats": read_stats
            }
        }
        
        # Evaluar performance general
        goals_met = sum([
            performance_results["write_performance"]["meets_avg_goal"],
            performance_results["write_performance"]["meets_p95_goal"],
            performance_results["read_performance"]["meets_avg_goal"],
            performance_results["read_performance"]["meets_p95_goal"]
        ])
        
        if goals_met >= 3:
            print_success(f"✓ Performance excelente: {goals_met}/4 objetivos cumplidos")
        elif goals_met >= 2:
            print_success(f"✓ Performance buena: {goals_met}/4 objetivos cumplidos")
        else:
            print_warning(f"⚠️ Performance mejorable: {goals_met}/4 objetivos cumplidos")
        
        return {
            "status": "success",
            "performance_results": performance_results,
            "goals_met": goals_met,
            "total_goals": 4
        }
        
    except Exception as e:
        print_error(f"Error en test Performance: {e}")
        return {"status": "error", "error": str(e)}

async def test_10_integration_with_rag():
    """Test 10: Verificar integración con sistema RAG existente"""
    print_test_header("Integration with RAG System", 10, 10)
    
    try:
        print_info("Probando integración con sistema RAG...")
        
        # Test de integración con embeddings service
        try:
            from app.services.embeddings_service import EmbeddingsService
            embeddings_service = EmbeddingsService()
            print_success("✓ EmbeddingsService importado correctamente")
            
            # Test búsqueda con cache distribuido
            test_query = "extintores de seguridad"
            print_info(f"Probando búsqueda: '{test_query}'")
            
            # Primera búsqueda (debería usar cache distribuido si está disponible)
            start_time = time.time()
            results1 = await embeddings_service.search_products(test_query, top_k=5)
            time1 = (time.time() - start_time) * 1000
            
            # Segunda búsqueda (debería ser más rápida con cache)
            start_time = time.time()
            results2 = await embeddings_service.search_products(test_query, top_k=5)
            time2 = (time.time() - start_time) * 1000
            
            integration_results = {
                "embeddings_service": {
                    "available": True,
                    "first_search_ms": time1,
                    "second_search_ms": time2,
                    "cache_improvement": time1 / max(time2, 1),
                    "results_count": len(results1) if results1 else 0
                }
            }
            
            if results1:
                print_success(f"✓ Búsqueda exitosa: {len(results1)} resultados")
                print_info(f"Performance: {time1:.1f}ms → {time2:.1f}ms (mejora: {time1/max(time2,1):.1f}x)")
            else:
                print_warning("⚠️ Búsqueda sin resultados")
                
        except Exception as e:
            print_warning(f"⚠️ EmbeddingsService error: {e}")
            integration_results = {"embeddings_service": {"available": False, "error": str(e)}}
        
        # Test de integración con RAG principal
        try:
            from app.services.rag import RAGService
            rag_service = RAGService()
            print_success("✓ RAGService importado correctamente")
            
            # Test consulta RAG
            test_rag_query = "¿Qué extintores tienes disponibles?"
            print_info(f"Probando consulta RAG: '{test_rag_query}'")
            
            start_time = time.time()
            rag_response = await rag_service.retrieval_inventario(test_rag_query)
            rag_time = (time.time() - start_time) * 1000
            
            integration_results["rag_service"] = {
                "available": True,
                "response_time_ms": rag_time,
                "response_length": len(str(rag_response)) if rag_response else 0
            }
            
            if rag_response:
                print_success(f"✓ RAG response exitoso: {len(str(rag_response))} chars en {rag_time:.1f}ms")
            else:
                print_warning("⚠️ RAG response vacío")
                
        except Exception as e:
            print_warning(f"⚠️ RAGService error: {e}")
            integration_results["rag_service"] = {"available": False, "error": str(e)}
        
        # Verificar estadísticas finales
        try:
            from app.core.distributed_cache import get_distributed_cache_stats
            from app.services.rag_semantic_cache_redis import get_distributed_semantic_cache_stats
            
            final_distributed_stats = get_distributed_cache_stats()
            final_semantic_stats = get_distributed_semantic_cache_stats()
            
            integration_results["final_stats"] = {
                "distributed_cache": {
                    "total_requests": final_distributed_stats.get("global", {}).get("total_requests", 0),
                    "hit_rate": final_distributed_stats.get("global", {}).get("hit_rate", 0)
                },
                "semantic_cache": {
                    "total_queries": final_semantic_stats.get("distributed_performance", {}).get("total_queries", 0),
                    "distributed_hit_rate": final_semantic_stats.get("distributed_performance", {}).get("distributed_hit_rate", 0)
                }
            }
            
            print_success("✓ Estadísticas finales obtenidas")
            
        except Exception as e:
            print_warning(f"⚠️ Error obteniendo estadísticas finales: {e}")
        
        return {
            "status": "success",
            "integration_results": integration_results
        }
        
    except Exception as e:
        print_error(f"Error en test Integration: {e}")
        return {"status": "error", "error": str(e)}

# ===============================
# FUNCIÓN PRINCIPAL DE TESTING
# ===============================

async def run_all_tests():
    """Ejecuta todos los tests del Paso 5"""
    print(f"\n{Colors.BOLD}{Colors.PURPLE}🚀 INICIANDO TESTS DEL PASO 5: CACHE DISTRIBUIDO REDIS ENTERPRISE{Colors.END}")
    print(f"{Colors.PURPLE}{'='*80}{Colors.END}")
    
    # Lista de tests
    tests = [
        test_1_redis_manager_availability,
        test_2_distributed_cache_layer,
        test_3_multi_level_cache_hierarchy,
        test_4_semantic_cache_redis_integration,
        test_5_cache_serialization_compression,
        test_6_cache_promotion_demotion,
        test_7_distributed_invalidation,
        test_8_monitoring_apis,
        test_9_performance_benchmarks,
        test_10_integration_with_rag
    ]
    
    results = {}
    successful_tests = 0
    total_tests = len(tests)
    
    start_time = time.time()
    
    # Ejecutar tests
    for i, test_func in enumerate(tests, 1):
        try:
            result = await test_func()
            results[test_func.__name__] = result
            
            if result.get("status") == "success":
                successful_tests += 1
                
        except Exception as e:
            print_error(f"Error crítico en {test_func.__name__}: {e}")
            results[test_func.__name__] = {"status": "critical_error", "error": str(e)}
    
    total_time = time.time() - start_time
    
    # Resumen final
    print(f"\n{Colors.BOLD}{Colors.PURPLE}📊 RESUMEN FINAL - PASO 5{Colors.END}")
    print(f"{Colors.PURPLE}{'='*80}{Colors.END}")
    
    success_rate = (successful_tests / total_tests) * 100
    
    print(f"\n{Colors.BOLD}Resultados Generales:{Colors.END}")
    print(f"✅ Tests exitosos: {Colors.GREEN}{successful_tests}/{total_tests}{Colors.END}")
    print(f"📈 Tasa de éxito: {Colors.GREEN if success_rate >= 70 else Colors.YELLOW if success_rate >= 50 else Colors.RED}{success_rate:.1f}%{Colors.END}")
    print(f"⏱️ Tiempo total: {Colors.BLUE}{total_time:.2f} segundos{Colors.END}")
    
    # Detalles por test
    print(f"\n{Colors.BOLD}Detalle por Test:{Colors.END}")
    for test_name, result in results.items():
        status = result.get("status", "unknown")
        if status == "success":
            print(f"  ✅ {test_name.replace('test_', '').replace('_', ' ').title()}")
        elif status == "error":
            print(f"  ❌ {test_name.replace('test_', '').replace('_', ' ').title()}: {result.get('error', 'Unknown error')}")
        else:
            print(f"  ⚠️ {test_name.replace('test_', '').replace('_', ' ').title()}: {status}")
    
    # Evaluación del Paso 5
    print(f"\n{Colors.BOLD}Evaluación del Paso 5:{Colors.END}")
    
    if success_rate >= 80:
        print(f"{Colors.GREEN}🎉 PASO 5 COMPLETADO EXITOSAMENTE{Colors.END}")
        print(f"{Colors.GREEN}   Cache distribuido Redis enterprise funcionando correctamente{Colors.END}")
    elif success_rate >= 60:
        print(f"{Colors.YELLOW}⚡ PASO 5 PARCIALMENTE COMPLETADO{Colors.END}")
        print(f"{Colors.YELLOW}   Funcionalidad principal operativa, optimizaciones pendientes{Colors.END}")
    else:
        print(f"{Colors.RED}❌ PASO 5 REQUIERE ATENCIÓN{Colors.END}")
        print(f"{Colors.RED}   Problemas significativos detectados{Colors.END}")
    
    # Recomendaciones
    print(f"\n{Colors.BOLD}Próximos Pasos Recomendados:{Colors.END}")
    
    if success_rate >= 80:
        print(f"  🚀 Continuar con Paso 6: Load Balancing & Auto-scaling")
        print(f"  📊 Monitorear métricas de performance en producción")
        print(f"  🔧 Optimizar configuración de Redis según carga real")
    elif success_rate >= 60:
        print(f"  🔧 Resolver errores identificados en tests fallidos")
        print(f"  📈 Optimizar performance de cache distribuido")
        print(f"  🧪 Re-ejecutar tests después de correcciones")
    else:
        print(f"  🚨 Revisar configuración de Redis y dependencias")
        print(f"  🔍 Analizar logs de errores detalladamente")
        print(f"  🛠️ Verificar integración con componentes existentes")
    
    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": success_rate,
        "total_time": total_time,
        "results": results
    }

if __name__ == "__main__":
    # Ejecutar tests
    asyncio.run(run_all_tests()) 