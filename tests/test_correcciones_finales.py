#!/usr/bin/env python3
"""
🎯 TEST DE CORRECCIONES FINALES - Verificación 100% Conectividad
Verifica que los 4 endpoints corregidos funcionen correctamente.
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8001"

async def test_correcciones_finales():
    """Prueba las 4 correcciones implementadas"""
    
    print("🔧 TESTING DE CORRECCIONES FINALES")
    print("=" * 50)
    
    resultados = {
        "exitosos": 0,
        "fallidos": 0,
        "total": 4
    }
    
    async with aiohttp.ClientSession() as session:
        
        # ✅ CORRECCIÓN 1: GET /productos/{id}
        print("\n📡 TEST 1: GET /productos/1")
        try:
            async with session.get(f"{BASE_URL}/productos/1") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ ÉXITO - ID: {data.get('id')}, Nombre: {data.get('nombre')}")
                    resultados["exitosos"] += 1
                else:
                    print(f"❌ FALLO - Status: {response.status}")
                    resultados["fallidos"] += 1
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            resultados["fallidos"] += 1
        
        # ✅ CORRECCIÓN 2: POST /productos/ con duplicados
        print("\n📡 TEST 2: POST /productos/ (manejo duplicados)")
        try:
            payload = {
                "nombre": "Test Producto Único",
                "descripcion": "Test corrección duplicados",
                "precio": 199.99,
                "stock": 50,
                "categoria": "Test Final"
            }
            async with session.post(f"{BASE_URL}/productos/", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ ÉXITO - Producto actualizado ID: {data.get('id')}")
                    resultados["exitosos"] += 1
                else:
                    print(f"❌ FALLO - Status: {response.status}")
                    resultados["fallidos"] += 1
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            resultados["fallidos"] += 1
        
        # ✅ CORRECCIÓN 3: GET /exportar/conversaciones-rag
        print("\n📡 TEST 3: GET /exportar/conversaciones-rag")
        try:
            async with session.get(f"{BASE_URL}/exportar/conversaciones-rag") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ ÉXITO - Total conversaciones: {data.get('total_conversaciones', 0)}")
                    resultados["exitosos"] += 1
                else:
                    print(f"❌ FALLO - Status: {response.status}")
                    resultados["fallidos"] += 1
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            resultados["fallidos"] += 1
        
        # ✅ CORRECCIÓN 4: POST /venta/ con múltiples productos
        print("\n📡 TEST 4: POST /venta/ (múltiples productos)")
        try:
            payload = {
                "chat_id": "test-correcciones-finales",
                "productos": [
                    {
                        "producto_id": 119,
                        "cantidad": 1,
                        "precio_unitario": 199.99
                    }
                ],
                "total": 199.99,
                "cliente_cedula": "12345678",
                "cliente_nombre": "Cliente Test Final",
                "cliente_telefono": "3001234567"
            }
            async with session.post(f"{BASE_URL}/venta/", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ ÉXITO - Ventas creadas: {len(data.get('ventas_creadas', []))}")
                    resultados["exitosos"] += 1
                else:
                    text = await response.text()
                    print(f"❌ FALLO - Status: {response.status}, Response: {text[:100]}")
                    resultados["fallidos"] += 1
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            resultados["fallidos"] += 1
    
    # 📊 RESULTADOS FINALES
    print("\n" + "=" * 50)
    print("📊 RESULTADOS FINALES:")
    print(f"   ✅ Exitosos: {resultados['exitosos']}")
    print(f"   ❌ Fallidos: {resultados['fallidos']}")
    print(f"   📈 Tasa de éxito: {(resultados['exitosos'] / resultados['total']) * 100:.1f}%")
    
    if resultados["exitosos"] == resultados["total"]:
        print("\n🎉 ¡TODAS LAS CORRECCIONES FUNCIONAN CORRECTAMENTE!")
        print("🏆 CONECTIVIDAD AL 100% ALCANZADA")
    else:
        print(f"\n⚠️  {resultados['fallidos']} correcciones aún tienen problemas")
    
    return resultados

if __name__ == "__main__":
    asyncio.run(test_correcciones_finales()) 