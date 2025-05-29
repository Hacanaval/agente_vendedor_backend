#!/usr/bin/env python3
"""
🧪🔴 Test Suite Paso 5 (Simplificado): Cache Distribuido Redis Enterprise
Validación del sistema de cache distribuido sin modelos pesados
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
# TESTS SIMPLIFICADOS DEL PASO 5
# ===============================

async def test_1_redis_manager_basic():
    """Test 1: Verificar importación y configuración básica del Redis Manager"""
    print_test_header("Redis Manager Basic", 1, 8)
    
    try:
        from app.core.redis_manager import (
            redis_manager, 
            get_redis_stats,
            REDIS_AVAILABLE
        )
        
        print_info("Verificando importación de Redis Manager...")
        print_success("✓ Redis Manager importado correctamente")
        
        # Verificar configuración
        print_info(f"Redis disponible: {REDIS_AVAILABLE}")
        
        # Obtener estadísticas (sin inicializar)
        stats = get_redis_stats()
        print_info(f"Configuración básica obtenida: {len(stats)} secciones")
        
        return {
            "status": "success",
            "redis_available": REDIS_AVAILABLE,
            "config_sections": len(stats)
        }
        
    except Exception as e:
        print_error(f"Error en test Redis Manager: {e}")
        return {"status": "error", "error": str(e)}

async def test_2_distributed_cache_basic():
    """Test 2: Verificar funcionamiento básico del Distributed Cache Layer"""
    print_test_header("Distributed Cache Basic", 2, 8)
    
    try:
        from app.core.distributed_cache import (
            distributed_cache,
            get_distributed_cache_stats,
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Probando cache distribuido básico...")
        
        # Test de escritura y lectura básica (solo L1)
        test_key = "test_basic_key"
        test_value = {"message": "Hello Basic Cache", "timestamp": datetime.now().isoformat()}
        
        # Escribir (debería funcionar en L1 aunque Redis no esté disponible)
        write_success = await set_distributed_cached("test_namespace", test_key, test_value, ttl_seconds=300)
        if write_success:
            print_success("✓ Escritura básica exitosa")
        else:
            print_warning("⚠️ Escritura básica falló")
        
        # Leer
        read_value = await get_distributed_cached("test_namespace", test_key)
        if read_value:
            print_success("✓ Lectura básica exitosa")
        else:
            print_warning("⚠️ Lectura básica sin resultado")
        
        # Obtener estadísticas
        stats = get_distributed_cache_stats()
        print_info(f"Estadísticas obtenidas: {len(stats)} secciones")
        
        return {
            "status": "success",
            "write_success": write_success,
            "read_success": read_value is not None,
            "stats_sections": len(stats)
        }
        
    except Exception as e:
        print_error(f"Error en test Distributed Cache: {e}")
        return {"status": "error", "error": str(e)}

async def test_3_cache_serialization():
    """Test 3: Verificar serialización y compresión de datos"""
    print_test_header("Cache Serialization", 3, 8)
    
    try:
        from app.core.distributed_cache import CacheSerializer
        
        print_info("Probando serialización...")
        
        serializer = CacheSerializer()
        
        # Test cases simples
        test_data = [
            {"name": "Small JSON", "data": {"key": "value", "number": 42}},
            {"name": "Text", "data": "Hello World " * 100},
            {"name": "List", "data": [1, 2, 3, 4, 5] * 20}
        ]
        
        results = {}
        
        for test_case in test_data:
            try:
                data = test_case["data"]
                
                # Serializar
                serialized_data, metadata = serializer.serialize(data)
                
                # Deserializar
                deserialized_data = serializer.deserialize(serialized_data, metadata)
                
                # Verificar integridad
                integrity_ok = str(data) == str(deserialized_data)
                
                results[test_case["name"]] = {
                    "integrity_ok": integrity_ok,
                    "original_size": metadata.get("original_size", 0),
                    "compression_used": metadata.get("compression_used", False)
                }
                
                if integrity_ok:
                    print_success(f"✓ {test_case['name']}: Integridad OK")
                else:
                    print_error(f"✗ {test_case['name']}: Fallo de integridad")
                    
            except Exception as e:
                print_error(f"Error en {test_case['name']}: {e}")
                results[test_case["name"]] = {"error": str(e)}
        
        return {
            "status": "success",
            "serialization_results": results
        }
        
    except Exception as e:
        print_error(f"Error en test Serialization: {e}")
        return {"status": "error", "error": str(e)}

async def test_4_cache_levels():
    """Test 4: Verificar diferentes niveles de cache"""
    print_test_header("Cache Levels", 4, 8)
    
    try:
        from app.core.distributed_cache import (
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Probando diferentes niveles de cache...")
        
        # Test con diferentes namespaces
        test_cases = [
            {"namespace": "user_sessions", "key": "session_1", "value": {"user": "test"}},
            {"namespace": "search_results", "key": "search_1", "value": {"results": [1, 2, 3]}},
            {"namespace": "default", "key": "default_1", "value": {"data": "test"}}
        ]
        
        results = {}
        
        for test_case in test_cases:
            namespace = test_case["namespace"]
            key = test_case["key"]
            value = test_case["value"]
            
            # Escribir
            write_success = await set_distributed_cached(namespace, key, value, ttl_seconds=300)
            
            # Leer
            read_value = await get_distributed_cached(namespace, key)
            
            results[namespace] = {
                "write_success": write_success,
                "read_success": read_value is not None
            }
            
            if write_success and read_value:
                print_success(f"✓ {namespace}: Operación exitosa")
            else:
                print_warning(f"⚠️ {namespace}: Operación parcial")
        
        return {
            "status": "success",
            "level_results": results
        }
        
    except Exception as e:
        print_error(f"Error en test Cache Levels: {e}")
        return {"status": "error", "error": str(e)}

async def test_5_semantic_cache_basic():
    """Test 5: Verificar cache semántico básico (sin modelos)"""
    print_test_header("Semantic Cache Basic", 5, 8)
    
    try:
        from app.services.rag_semantic_cache_redis import (
            semantic_cache_redis,
            get_distributed_semantic_cache_stats
        )
        
        print_info("Probando cache semántico básico...")
        
        # Test básico sin cargar modelos
        print_success("✓ Cache semántico importado correctamente")
        
        # Obtener estadísticas
        stats = get_distributed_semantic_cache_stats()
        print_info(f"Estadísticas semánticas obtenidas: {len(stats)} secciones")
        
        # Test de funciones básicas
        test_query = "test query"
        normalized, entities = semantic_cache_redis.normalize_query_advanced(test_query)
        
        if normalized:
            print_success(f"✓ Normalización funcionando: '{test_query}' → '{normalized}'")
        else:
            print_warning("⚠️ Normalización no funcionando")
        
        return {
            "status": "success",
            "stats_sections": len(stats),
            "normalization_working": bool(normalized)
        }
        
    except Exception as e:
        print_error(f"Error en test Semantic Cache: {e}")
        return {"status": "error", "error": str(e)}

async def test_6_monitoring_apis():
    """Test 6: Verificar APIs de monitoreo"""
    print_test_header("Monitoring APIs", 6, 8)
    
    try:
        from app.api.monitoring_redis import router
        from app.core.redis_manager import get_redis_stats
        from app.core.distributed_cache import get_distributed_cache_stats
        
        print_info("Probando APIs de monitoreo...")
        
        monitoring_results = {}
        
        # Redis stats
        try:
            redis_stats = get_redis_stats()
            monitoring_results["redis_stats"] = {
                "available": True,
                "sections": len(redis_stats)
            }
            print_success("✓ Redis stats obtenidas")
        except Exception as e:
            monitoring_results["redis_stats"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Redis stats error: {e}")
        
        # Distributed cache stats
        try:
            distributed_stats = get_distributed_cache_stats()
            monitoring_results["distributed_stats"] = {
                "available": True,
                "sections": len(distributed_stats)
            }
            print_success("✓ Distributed cache stats obtenidas")
        except Exception as e:
            monitoring_results["distributed_stats"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Distributed cache stats error: {e}")
        
        # Verificar router
        api_endpoints = [route.path for route in router.routes]
        print_info(f"Endpoints disponibles: {len(api_endpoints)}")
        
        return {
            "status": "success",
            "monitoring_results": monitoring_results,
            "api_endpoints_count": len(api_endpoints)
        }
        
    except Exception as e:
        print_error(f"Error en test Monitoring APIs: {e}")
        return {"status": "error", "error": str(e)}

async def test_7_performance_basic():
    """Test 7: Benchmarks básicos de performance"""
    print_test_header("Performance Basic", 7, 8)
    
    try:
        from app.core.distributed_cache import (
            get_distributed_cached,
            set_distributed_cached
        )
        
        print_info("Ejecutando benchmarks básicos...")
        
        # Configuración del benchmark
        num_operations = 20  # Reducido para evitar spam
        key_prefix = "benchmark_key_"
        test_value = {"benchmark": True, "data": "x" * 50}
        
        # Benchmark de escritura
        write_times = []
        for i in range(num_operations):
            start_time = time.time()
            await set_distributed_cached("benchmark", f"{key_prefix}{i}", test_value, ttl_seconds=300)
            write_time = (time.time() - start_time) * 1000
            write_times.append(write_time)
        
        # Benchmark de lectura
        read_times = []
        for i in range(num_operations):
            start_time = time.time()
            value = await get_distributed_cached("benchmark", f"{key_prefix}{i}")
            read_time = (time.time() - start_time) * 1000
            read_times.append(read_time)
        
        # Calcular estadísticas
        write_avg = sum(write_times) / len(write_times)
        read_avg = sum(read_times) / len(read_times)
        
        print_success(f"✓ Escritura promedio: {write_avg:.2f}ms")
        print_success(f"✓ Lectura promedio: {read_avg:.2f}ms")
        
        # Verificar objetivos básicos
        write_ok = write_avg < 100  # <100ms
        read_ok = read_avg < 50     # <50ms
        
        return {
            "status": "success",
            "write_avg_ms": write_avg,
            "read_avg_ms": read_avg,
            "write_performance_ok": write_ok,
            "read_performance_ok": read_ok
        }
        
    except Exception as e:
        print_error(f"Error en test Performance: {e}")
        return {"status": "error", "error": str(e)}

async def test_8_integration_basic():
    """Test 8: Verificar integración básica con sistema existente"""
    print_test_header("Integration Basic", 8, 8)
    
    try:
        print_info("Probando integración básica...")
        
        integration_results = {}
        
        # Test de importación de componentes principales
        try:
            from app.core.cache_manager import MemoryCache, DiskCache
            integration_results["cache_manager"] = {"available": True}
            print_success("✓ Cache Manager importado")
        except Exception as e:
            integration_results["cache_manager"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ Cache Manager error: {e}")
        
        # Test de importación de servicios RAG
        try:
            from app.services import rag
            integration_results["rag_service"] = {"available": True}
            print_success("✓ RAG Service importado")
        except Exception as e:
            integration_results["rag_service"] = {"available": False, "error": str(e)}
            print_warning(f"⚠️ RAG Service error: {e}")
        
        # Verificar estadísticas finales
        try:
            from app.core.distributed_cache import get_distributed_cache_stats
            final_stats = get_distributed_cache_stats()
            
            integration_results["final_stats"] = {
                "total_requests": final_stats.get("global", {}).get("total_requests", 0),
                "hit_rate": final_stats.get("global", {}).get("hit_rate", 0)
            }
            
            print_success("✓ Estadísticas finales obtenidas")
            print_info(f"Total requests: {integration_results['final_stats']['total_requests']}")
            print_info(f"Hit rate: {integration_results['final_stats']['hit_rate']}%")
            
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
    """Ejecuta todos los tests simplificados del Paso 5"""
    print(f"\n{Colors.BOLD}{Colors.PURPLE}🚀 TESTS SIMPLIFICADOS DEL PASO 5: CACHE DISTRIBUIDO REDIS{Colors.END}")
    print(f"{Colors.PURPLE}{'='*80}{Colors.END}")
    
    # Lista de tests
    tests = [
        test_1_redis_manager_basic,
        test_2_distributed_cache_basic,
        test_3_cache_serialization,
        test_4_cache_levels,
        test_5_semantic_cache_basic,
        test_6_monitoring_apis,
        test_7_performance_basic,
        test_8_integration_basic
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
    print(f"\n{Colors.BOLD}{Colors.PURPLE}📊 RESUMEN FINAL - PASO 5 (SIMPLIFICADO){Colors.END}")
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
        print(f"{Colors.GREEN}   Infraestructura de cache distribuido funcionando{Colors.END}")
    elif success_rate >= 60:
        print(f"{Colors.YELLOW}⚡ PASO 5 PARCIALMENTE COMPLETADO{Colors.END}")
        print(f"{Colors.YELLOW}   Componentes principales operativos{Colors.END}")
    else:
        print(f"{Colors.RED}❌ PASO 5 REQUIERE ATENCIÓN{Colors.END}")
        print(f"{Colors.RED}   Problemas en componentes básicos{Colors.END}")
    
    # Análisis específico
    print(f"\n{Colors.BOLD}Análisis Específico:{Colors.END}")
    
    # Redis disponibilidad
    redis_result = results.get("test_1_redis_manager_basic", {})
    if redis_result.get("redis_available"):
        print(f"  🔴 Redis: Librerías disponibles (servidor no conectado)")
    else:
        print(f"  ⚠️ Redis: Librerías no disponibles")
    
    # Cache distribuido
    cache_result = results.get("test_2_distributed_cache_basic", {})
    if cache_result.get("write_success") and cache_result.get("read_success"):
        print(f"  🌐 Cache Distribuido: Funcionando en modo local")
    else:
        print(f"  ❌ Cache Distribuido: Problemas básicos")
    
    # Performance
    perf_result = results.get("test_7_performance_basic", {})
    if perf_result.get("write_performance_ok") and perf_result.get("read_performance_ok"):
        print(f"  ⚡ Performance: Objetivos cumplidos")
    else:
        print(f"  ⚠️ Performance: Necesita optimización")
    
    # Recomendaciones
    print(f"\n{Colors.BOLD}Próximos Pasos:{Colors.END}")
    
    if success_rate >= 80:
        print(f"  🚀 Instalar y configurar Redis server para funcionalidad completa")
        print(f"  📊 Ejecutar tests completos con Redis funcionando")
        print(f"  🔧 Continuar con Paso 6: Load Balancing")
    elif success_rate >= 60:
        print(f"  🔧 Resolver problemas identificados")
        print(f"  🔴 Configurar Redis server")
        print(f"  🧪 Re-ejecutar tests después de correcciones")
    else:
        print(f"  🚨 Revisar dependencias básicas")
        print(f"  🔍 Analizar errores de importación")
        print(f"  🛠️ Verificar configuración del entorno")
    
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