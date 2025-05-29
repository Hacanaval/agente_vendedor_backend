#!/usr/bin/env python3
"""
Script de Prueba: Cache Manager Enterprise
Demuestra el sistema de cache multi-nivel con métricas en tiempo real
"""
import asyncio
import time
import json
import httpx
from datetime import datetime
from typing import Dict, Any

# Configuración
BASE_URL = "http://localhost:8000"
CACHE_API = f"{BASE_URL}/monitoring/cache"

class CacheTestSuite:
    """Suite de pruebas para el Cache Manager Enterprise"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.test_results = []
    
    async def run_all_tests(self):
        """Ejecuta todas las pruebas del cache"""
        print("🚀 INICIANDO PRUEBAS DEL CACHE MANAGER ENTERPRISE")
        print("=" * 60)
        
        # Pruebas básicas
        await self.test_cache_basic_operations()
        await self.test_cache_ttl_behavior()
        await self.test_cache_multi_level()
        await self.test_cache_performance()
        await self.test_cache_invalidation()
        
        # Mostrar resumen
        await self.show_final_stats()
        
        await self.client.aclose()
    
    async def test_cache_basic_operations(self):
        """Prueba operaciones básicas del cache"""
        print("\n📝 TEST 1: Operaciones Básicas del Cache")
        print("-" * 40)
        
        # Importar el cache manager para pruebas directas
        from app.core.cache_manager import cache_manager
        
        # Test 1: Set y Get básico
        await cache_manager.set("test", "key1", "valor_test_1")
        value = await cache_manager.get("test", "key1")
        
        assert value == "valor_test_1", f"Expected 'valor_test_1', got {value}"
        print("✅ Set/Get básico: PASÓ")
        
        # Test 2: Cache miss
        missing_value = await cache_manager.get("test", "key_inexistente")
        assert missing_value is None, f"Expected None, got {missing_value}"
        print("✅ Cache miss: PASÓ")
        
        # Test 3: Múltiples namespaces
        await cache_manager.set("productos", "prod1", {"id": 1, "nombre": "Producto Test"})
        await cache_manager.set("usuarios", "user1", {"id": 1, "email": "test@test.com"})
        
        prod = await cache_manager.get("productos", "prod1")
        user = await cache_manager.get("usuarios", "user1")
        
        assert prod["nombre"] == "Producto Test"
        assert user["email"] == "test@test.com"
        print("✅ Múltiples namespaces: PASÓ")
        
        self.test_results.append({"test": "basic_operations", "status": "PASSED"})
    
    async def test_cache_ttl_behavior(self):
        """Prueba el comportamiento de TTL"""
        print("\n⏰ TEST 2: Comportamiento de TTL")
        print("-" * 40)
        
        from app.core.cache_manager import cache_manager
        
        # Test con TTL corto
        await cache_manager.set("test_ttl", "short_lived", "valor_temporal", ttl_seconds=2)
        
        # Verificar que existe inmediatamente
        value = await cache_manager.get("test_ttl", "short_lived")
        assert value == "valor_temporal"
        print("✅ Valor existe inmediatamente después de set")
        
        # Esperar a que expire
        print("⏳ Esperando 3 segundos para que expire...")
        await asyncio.sleep(3)
        
        # Verificar que expiró
        expired_value = await cache_manager.get("test_ttl", "short_lived")
        assert expired_value is None
        print("✅ Valor expiró correctamente después del TTL")
        
        self.test_results.append({"test": "ttl_behavior", "status": "PASSED"})
    
    async def test_cache_multi_level(self):
        """Prueba el comportamiento multi-nivel"""
        print("\n🏗️ TEST 3: Cache Multi-Nivel")
        print("-" * 40)
        
        from app.core.cache_manager import cache_manager
        
        # Limpiar cache para empezar limpio
        await cache_manager.memory_cache.clear()
        await cache_manager.disk_cache.clear()
        
        # Almacenar en ambos niveles
        test_data = {"nivel": "multi", "timestamp": datetime.now().isoformat()}
        await cache_manager.set("multi_level", "test_key", test_data)
        
        # Verificar que está en memoria
        memory_value = await cache_manager.memory_cache.get("multi_level|test_key")
        assert memory_value is not None
        print("✅ Datos almacenados en memoria (L1)")
        
        # Verificar que está en disco
        disk_value = await cache_manager.disk_cache.get("multi_level|test_key")
        assert disk_value is not None
        print("✅ Datos almacenados en disco (L2)")
        
        # Limpiar solo memoria para probar promoción
        await cache_manager.memory_cache.clear()
        
        # Obtener datos (debería promover de disco a memoria)
        retrieved_value = await cache_manager.get("multi_level", "test_key")
        assert retrieved_value["nivel"] == "multi"
        print("✅ Promoción de L2 (disco) a L1 (memoria)")
        
        # Verificar que ahora está en memoria otra vez
        memory_value_after = await cache_manager.memory_cache.get("multi_level|test_key")
        assert memory_value_after is not None
        print("✅ Datos promovidos correctamente a memoria")
        
        self.test_results.append({"test": "multi_level", "status": "PASSED"})
    
    async def test_cache_performance(self):
        """Prueba el rendimiento del cache"""
        print("\n⚡ TEST 4: Performance del Cache")
        print("-" * 40)
        
        from app.core.cache_manager import cache_manager
        
        # Preparar datos de prueba
        test_data = {"performance": True, "data": "x" * 1000}  # 1KB aprox
        
        # Test de escritura
        start_time = time.time()
        for i in range(100):
            await cache_manager.set("performance", f"key_{i}", test_data)
        write_time = time.time() - start_time
        
        print(f"✅ 100 escrituras en {write_time:.3f}s ({write_time*10:.1f}ms promedio)")
        
        # Test de lectura (cache hit)
        start_time = time.time()
        for i in range(100):
            value = await cache_manager.get("performance", f"key_{i}")
            assert value is not None
        read_time = time.time() - start_time
        
        print(f"✅ 100 lecturas (hits) en {read_time:.3f}s ({read_time*10:.1f}ms promedio)")
        
        # Test de lectura (cache miss)
        start_time = time.time()
        for i in range(50):
            value = await cache_manager.get("performance", f"missing_key_{i}")
            assert value is None
        miss_time = time.time() - start_time
        
        print(f"✅ 50 lecturas (misses) en {miss_time:.3f}s ({miss_time*20:.1f}ms promedio)")
        
        # Verificar que el rendimiento es aceptable
        avg_write_ms = (write_time / 100) * 1000
        avg_read_ms = (read_time / 100) * 1000
        
        assert avg_write_ms < 50, f"Escritura muy lenta: {avg_write_ms:.1f}ms"
        assert avg_read_ms < 10, f"Lectura muy lenta: {avg_read_ms:.1f}ms"
        
        print(f"✅ Performance aceptable: Write {avg_write_ms:.1f}ms, Read {avg_read_ms:.1f}ms")
        
        self.test_results.append({"test": "performance", "status": "PASSED"})
    
    async def test_cache_invalidation(self):
        """Prueba la invalidación del cache"""
        print("\n🗑️ TEST 5: Invalidación del Cache")
        print("-" * 40)
        
        from app.core.cache_manager import cache_manager
        
        # Preparar datos para invalidación
        await cache_manager.set("invalidation", "item1", "valor1")
        await cache_manager.set("invalidation", "item2", "valor2")
        await cache_manager.set("other", "item3", "valor3")
        
        # Verificar que existen
        assert await cache_manager.get("invalidation", "item1") == "valor1"
        assert await cache_manager.get("invalidation", "item2") == "valor2"
        assert await cache_manager.get("other", "item3") == "valor3"
        print("✅ Datos preparados para invalidación")
        
        # Test de eliminación específica
        deleted = await cache_manager.delete("invalidation", "item1")
        assert deleted == True
        assert await cache_manager.get("invalidation", "item1") is None
        assert await cache_manager.get("invalidation", "item2") == "valor2"  # No afectado
        print("✅ Eliminación específica funciona")
        
        # Test de invalidación por patrón
        invalidated = await cache_manager.invalidate_pattern("invalidation")
        assert invalidated > 0
        assert await cache_manager.get("invalidation", "item2") is None
        assert await cache_manager.get("other", "item3") == "valor3"  # No afectado
        print("✅ Invalidación por patrón funciona")
        
        self.test_results.append({"test": "invalidation", "status": "PASSED"})
    
    async def show_final_stats(self):
        """Muestra estadísticas finales del cache"""
        print("\n📊 ESTADÍSTICAS FINALES DEL CACHE")
        print("=" * 60)
        
        try:
            response = await self.client.get(CACHE_API)
            if response.status_code == 200:
                stats = response.json()
                
                global_stats = stats["stats"]["global"]
                memory_stats = stats["stats"]["levels"]["memory"]
                disk_stats = stats["stats"]["levels"]["disk"]
                
                print(f"🎯 Hit Rate Global: {global_stats['hit_rate']:.1f}%")
                print(f"📊 Total Requests: {global_stats['total_requests']}")
                print(f"✅ Total Hits: {global_stats['total_hits']}")
                print(f"❌ Total Misses: {global_stats['total_misses']}")
                print(f"⏱️ Uptime: {global_stats['uptime_seconds']:.1f}s")
                
                print(f"\n💾 MEMORIA (L1):")
                print(f"   • Entradas: {memory_stats['size']}/{memory_stats['max_size']}")
                print(f"   • Hit Rate: {memory_stats['hit_rate']:.1f}%")
                print(f"   • Evictions: {memory_stats['evictions']}")
                print(f"   • Tamaño: {memory_stats['total_size_bytes']} bytes")
                
                print(f"\n💿 DISCO (L2):")
                print(f"   • Archivos: {disk_stats['file_count']}")
                print(f"   • Hit Rate: {disk_stats['hit_rate']:.1f}%")
                print(f"   • Tamaño: {disk_stats['total_size_mb']:.2f}MB")
                print(f"   • Compresión: {'✅' if disk_stats['compression_enabled'] else '❌'}")
                
                # Performance status
                performance = stats["performance"]
                status_emoji = {
                    "excellent": "🟢",
                    "good": "🟡", 
                    "poor": "🟠",
                    "critical": "🔴"
                }
                print(f"\n🎭 Estado: {status_emoji.get(performance['status'], '❓')} {performance['status'].upper()}")
                
                if stats["recommendations"]:
                    print(f"\n💡 RECOMENDACIONES:")
                    for rec in stats["recommendations"]:
                        print(f"   • {rec}")
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
        
        # Resumen de tests
        print(f"\n🧪 RESUMEN DE TESTS:")
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        total = len(self.test_results)
        print(f"   ✅ Pasaron: {passed}/{total}")
        
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            print(f"   {status_emoji} {result['test']}: {result['status']}")

async def main():
    """Función principal"""
    print("🗄️ CACHE MANAGER ENTERPRISE - SUITE DE PRUEBAS")
    print("=" * 60)
    print("Este script demuestra las capacidades del cache multi-nivel:")
    print("• Cache en memoria (L1) - Ultra rápido (1-5ms)")
    print("• Cache en disco (L2) - Rápido (10-50ms)")
    print("• TTL inteligente por tipo de contenido")
    print("• Promoción automática entre niveles")
    print("• Invalidación selectiva")
    print("• Métricas en tiempo real")
    
    # Verificar que el servidor esté corriendo
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print(f"❌ Servidor no disponible en {BASE_URL}")
                return
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("💡 Asegúrate de que el servidor esté corriendo:")
        print("   python -m uvicorn app.main:app --reload --port 8000")
        return
    
    # Ejecutar tests
    test_suite = CacheTestSuite()
    await test_suite.run_all_tests()
    
    print("\n🎉 PRUEBAS COMPLETADAS")
    print("=" * 60)
    print("El Cache Manager Enterprise está funcionando correctamente!")
    print(f"📊 Puedes ver métricas en tiempo real en: {CACHE_API}")

if __name__ == "__main__":
    asyncio.run(main()) 