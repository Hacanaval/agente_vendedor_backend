import asyncio
import httpx
import json
from datetime import datetime

# Configuración
BACKEND_URL = "http://localhost:8001"

# Casos de prueba
CASOS_PRUEBA = [
    {
        "tipo": "inventario",
        "mensaje": "¿Qué productos tienen disponibles?",
        "esperado": "lista de productos"
    },
    {
        "tipo": "venta", 
        "mensaje": "Quiero comprar 3 martillos",
        "esperado": "respuesta de venta"
    },
    {
        "tipo": "contexto",
        "mensaje": "¿Cuáles son los horarios de atención?",
        "esperado": "información de la empresa"
    },
    {
        "tipo": "inventario",
        "mensaje": "¿Cuánto cuesta el taladro?",
        "esperado": "precio del taladro"
    },
    {
        "tipo": "venta",
        "mensaje": "Me interesa comprar botas de seguridad",
        "esperado": "respuesta de venta"
    }
]

async def probar_endpoint_chat(mensaje: str, chat_id: str = "test_sistema"):
    """
    Prueba el endpoint de chat optimizado.
    """
    url = f"{BACKEND_URL}/chat/texto"
    payload = {
        "mensaje": mensaje,
        "chat_id": chat_id,
        "llm": "gemini"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

async def probar_endpoint_productos():
    """
    Prueba el endpoint de productos.
    """
    url = f"{BACKEND_URL}/productos/productos"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

async def probar_endpoint_health():
    """
    Prueba el endpoint de salud.
    """
    url = f"{BACKEND_URL}/chat/health"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

async def main():
    """
    Ejecuta todas las pruebas del sistema.
    """
    print("🚀 INICIANDO PRUEBAS COMPLETAS DEL SISTEMA OPTIMIZADO")
    print("=" * 60)
    
    # 1. Probar endpoint de salud
    print("\n1️⃣ PROBANDO ENDPOINT DE SALUD")
    health = await probar_endpoint_health()
    if "error" in health:
        print(f"❌ Error en health check: {health['error']}")
        return
    else:
        print(f"✅ Sistema saludable: {health}")
    
    # 2. Probar endpoint de productos
    print("\n2️⃣ PROBANDO ENDPOINT DE PRODUCTOS")
    productos = await probar_endpoint_productos()
    if "error" in productos:
        print(f"❌ Error en productos: {productos['error']}")
        return
    else:
        print(f"✅ Productos disponibles: {len(productos)} productos")
        for p in productos[:3]:  # Mostrar solo los primeros 3
            print(f"   - {p['nombre']}: ${p['precio']:,.0f} (Stock: {p['stock']})")
    
    # 3. Probar casos de chat
    print("\n3️⃣ PROBANDO CASOS DE CHAT")
    resultados = []
    
    for i, caso in enumerate(CASOS_PRUEBA, 1):
        print(f"\n   Caso {i}: {caso['tipo'].upper()}")
        print(f"   Mensaje: '{caso['mensaje']}'")
        
        respuesta = await probar_endpoint_chat(caso['mensaje'], f"test_caso_{i}")
        
        if "error" in respuesta:
            print(f"   ❌ Error: {respuesta['error']}")
            resultados.append(False)
        else:
            tipo_clasificado = respuesta.get('tipo_mensaje', 'desconocido')
            respuesta_texto = respuesta.get('respuesta', '')
            
            # Verificar clasificación
            clasificacion_correcta = tipo_clasificado == caso['tipo']
            
            print(f"   📝 Clasificado como: {tipo_clasificado}")
            print(f"   💬 Respuesta: {respuesta_texto[:100]}...")
            print(f"   {'✅' if clasificacion_correcta else '❌'} Clasificación {'correcta' if clasificacion_correcta else 'incorrecta'}")
            
            resultados.append(clasificacion_correcta)
    
    # 4. Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    
    casos_exitosos = sum(resultados)
    total_casos = len(resultados)
    porcentaje = (casos_exitosos / total_casos * 100) if total_casos > 0 else 0
    
    print(f"✅ Casos exitosos: {casos_exitosos}/{total_casos}")
    print(f"📈 Precisión: {porcentaje:.1f}%")
    
    if porcentaje >= 80:
        print("🎉 ¡SISTEMA FUNCIONANDO CORRECTAMENTE!")
    elif porcentaje >= 60:
        print("⚠️  Sistema funcionando con algunas mejoras necesarias")
    else:
        print("❌ Sistema requiere optimización")
    
    print(f"\n🕐 Prueba completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main()) 