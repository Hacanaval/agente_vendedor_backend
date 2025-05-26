import asyncio
import os
from app.core.database import SessionLocal
from app.services.rag import consultar_rag
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
from app.services.pedidos import PedidoManager

async def test_mejoras_chatbot():
    """Prueba las mejoras implementadas en el chatbot"""
    print("🚀 Probando mejoras del chatbot\n")
    
    # Verificar API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY no está configurada")
        return
    
    async with SessionLocal() as db:
        chat_id = "test_mejoras_123"
        
        print("=== PRUEBA 1: Consulta por producto no disponible ===")
        mensaje1 = "¿Tienen extintores disponibles?"
        tipo1 = await clasificar_tipo_mensaje_llm(mensaje1)
        respuesta1 = await consultar_rag(
            mensaje=mensaje1,
            tipo=tipo1,
            db=db,
            chat_id=chat_id
        )
        print(f"Pregunta: {mensaje1}")
        print(f"Tipo: {tipo1}")
        print(f"Respuesta: {respuesta1['respuesta'][:300]}...")
        print()
        
        print("=== PRUEBA 2: Flujo de venta con productos disponibles ===")
        mensaje2 = "Quiero comprar 7 martillos"
        tipo2 = await clasificar_tipo_mensaje_llm(mensaje2)
        respuesta2 = await consultar_rag(
            mensaje=mensaje2,
            tipo=tipo2,
            db=db,
            chat_id=chat_id
        )
        print(f"Pregunta: {mensaje2}")
        print(f"Tipo: {tipo2}")
        print(f"Respuesta: {respuesta2['respuesta'][:300]}...")
        print()
        
        print("=== PRUEBA 3: Consultar pedido actual ===")
        mensaje3 = "Muéstrame mi pedido"
        tipo3 = await clasificar_tipo_mensaje_llm(mensaje3)
        respuesta3 = await consultar_rag(
            mensaje=mensaje3,
            tipo=tipo3,
            db=db,
            chat_id=chat_id
        )
        print(f"Pregunta: {mensaje3}")
        print(f"Tipo: {tipo3}")
        print(f"Respuesta: {respuesta3['respuesta'][:300]}...")
        print()
        
        print("=== PRUEBA 4: Verificar estado del pedido ===")
        estado_pedido = await PedidoManager.obtener_estado_pedido(chat_id, db)
        print(f"Estado del pedido: {estado_pedido}")
        print()
        
        print("=== PRUEBA 5: Consulta por producto disponible ===")
        mensaje5 = "¿Tienen alicates disponibles?"
        tipo5 = await clasificar_tipo_mensaje_llm(mensaje5)
        respuesta5 = await consultar_rag(
            mensaje=mensaje5,
            tipo=tipo5,
            db=db,
            chat_id=chat_id
        )
        print(f"Pregunta: {mensaje5}")
        print(f"Tipo: {tipo5}")
        print(f"Respuesta: {respuesta5['respuesta'][:300]}...")
        print()

if __name__ == "__main__":
    asyncio.run(test_mejoras_chatbot()) 