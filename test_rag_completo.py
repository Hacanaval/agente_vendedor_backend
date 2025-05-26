import asyncio
import os
from app.core.database import SessionLocal
from app.services.rag import consultar_rag
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm

# Mensajes de prueba
MENSAJES_PRUEBA = {
    "contexto": [
        "¿Cuáles son los horarios de atención?",
        "¿Dónde están ubicados?",
        "¿Qué servicios ofrecen?"
    ],
    "inventario": [
        "¿Tienen guantes disponibles?",
        "¿Cuánto cuesta el casco de seguridad?",
        "¿Qué productos tienen en stock?"
    ],
    "venta": [
        "Quiero comprar 5 guantes",
        "Me interesa adquirir un casco",
        "¿Puedo hacer un pedido de botas?"
    ]
}

async def test_clasificacion():
    print("=== PRUEBA 4: Verificando clasificación de mensajes ===")
    
    # Verificar API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY no está configurada")
        return
    
    print("✅ GOOGLE_API_KEY configurada correctamente")
    
    total_correctas = 0
    total_mensajes = 0
    
    for tipo_esperado, mensajes in MENSAJES_PRUEBA.items():
        print(f"\n--- Probando mensajes de tipo: {tipo_esperado} ---")
        
        for mensaje in mensajes:
            try:
                tipo_clasificado = await clasificar_tipo_mensaje_llm(mensaje)
                total_mensajes += 1
                
                if tipo_clasificado == tipo_esperado:
                    total_correctas += 1
                    print(f"✅ '{mensaje}' → {tipo_clasificado}")
                else:
                    print(f"❌ '{mensaje}' → {tipo_clasificado} (esperado: {tipo_esperado})")
                    
            except Exception as e:
                print(f"❌ Error clasificando '{mensaje}': {e}")
    
    precision = (total_correctas / total_mensajes * 100) if total_mensajes > 0 else 0
    print(f"\n📊 Precisión de clasificación: {precision:.1f}% ({total_correctas}/{total_mensajes})")

async def test_rag_contexto():
    print("\n=== PRUEBA 2: Verificando RAG de contexto ===")
    
    async with SessionLocal() as db:
        try:
            mensaje = "¿Cuáles son los horarios de atención?"
            respuesta = await consultar_rag(
                mensaje=mensaje,
                tipo="contexto",
                db=db,
                chat_id="test_chat_contexto"
            )
            
            if respuesta and "respuesta" in respuesta:
                print(f"✅ RAG de contexto funcionando")
                print(f"Pregunta: {mensaje}")
                print(f"Respuesta: {respuesta['respuesta'][:200]}...")
            else:
                print("❌ RAG de contexto no devolvió respuesta válida")
                
        except Exception as e:
            print(f"❌ Error en RAG de contexto: {e}")

async def test_rag_inventario():
    print("\n=== PRUEBA 3: Verificando RAG de inventario ===")
    
    async with SessionLocal() as db:
        try:
            mensaje = "¿Qué productos tienen disponibles?"
            respuesta = await consultar_rag(
                mensaje=mensaje,
                tipo="inventario",
                db=db,
                chat_id="test_chat_inventario"
            )
            
            if respuesta and "respuesta" in respuesta:
                print(f"✅ RAG de inventario funcionando")
                print(f"Pregunta: {mensaje}")
                print(f"Respuesta: {respuesta['respuesta'][:200]}...")
            else:
                print("❌ RAG de inventario no devolvió respuesta válida")
                
        except Exception as e:
            print(f"❌ Error en RAG de inventario: {e}")

async def main():
    print("🚀 Iniciando pruebas completas del sistema RAG y clasificación\n")
    
    await test_clasificacion()
    await test_rag_contexto()
    await test_rag_inventario()
    
    print("\n✅ Pruebas completadas")

if __name__ == "__main__":
    asyncio.run(main()) 