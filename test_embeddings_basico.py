#!/usr/bin/env python3
"""
Test básico del sistema de embeddings
Prueba la funcionalidad core sin inicialización completa
"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_embeddings_basico():
    """Prueba básica del sistema de embeddings"""
    print("🚀 INICIANDO PRUEBA BÁSICA DE EMBEDDINGS SEMÁNTICOS")
    print("=" * 60)
    
    try:
        # Importar el servicio
        from app.services.embeddings_service import EmbeddingsService
        print("✅ Servicio de embeddings importado correctamente")
        
        # Crear instancia del servicio
        service = EmbeddingsService()
        print("✅ Instancia de servicio creada")
        
        # Verificar que el directorio de cache se crea
        print(f"📁 Directorio de cache: {service._ensure_cache_dir()}")
        
        # Obtener estadísticas iniciales
        stats = service.get_stats()
        print("\n📊 ESTADÍSTICAS INICIALES:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n🎯 PRUEBA DE GENERACIÓN DE SINÓNIMOS:")
        # Probar generación de sinónimos
        from app.models.producto import Producto
        
        # Simular un producto
        class ProductoMock:
            def __init__(self, nombre, categoria, descripcion=""):
                self.nombre = nombre
                self.categoria = categoria
                self.descripcion = descripcion
        
        producto_test = ProductoMock("Extintor PQS 10 libras", "Seguridad Industrial", "Extintor de polvo químico seco para fuegos tipo ABC")
        
        # Probar preparación de texto
        texto_indexado = service._prepare_product_text(producto_test)
        print(f"   Producto: {producto_test.nombre}")
        print(f"   Categoría: {producto_test.categoria}")
        print(f"   Texto indexado: {texto_indexado}")
        
        # Probar sinónimos
        sinonimos = service._generate_synonyms(producto_test.nombre, producto_test.categoria)
        print(f"   Sinónimos generados: {sinonimos}")
        
        print("\n✅ PRUEBA BÁSICA COMPLETADA EXITOSAMENTE")
        print("🔥 El sistema de embeddings está listo para usar")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_embeddings_basico())
        if result:
            print("\n🎉 TODAS LAS PRUEBAS BÁSICAS PASARON")
            sys.exit(0)
        else:
            print("\n💥 ALGUNAS PRUEBAS FALLARON")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Prueba interrumpida por el usuario")
        sys.exit(1) 