#!/usr/bin/env python3
"""
Reporte completo del estado de todos los sistemas RAG
"""

import asyncio
import httpx
import json
from datetime import datetime

async def generar_reporte_rag():
    print("📊 REPORTE COMPLETO DEL ESTADO DE SISTEMAS RAG")
    print("="*80)
    print(f"🕐 Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    client = httpx.AsyncClient(timeout=30.0)
    
    # Contadores para el reporte
    sistemas_rag = {
        "inventario": {"funcionando": False, "pruebas": 0, "exitosas": 0},
        "ventas": {"funcionando": False, "pruebas": 0, "exitosas": 0},
        "clientes": {"funcionando": False, "pruebas": 0, "exitosas": 0},
        "memoria": {"funcionando": False, "pruebas": 0, "exitosas": 0},
        "almacenamiento": {"funcionando": False, "pruebas": 0, "exitosas": 0}
    }
    
    try:
        # 1. VERIFICAR SERVIDOR
        print("\n🔧 1. VERIFICACIÓN DEL SERVIDOR")
        print("-" * 40)
        
        response = await client.get("http://localhost:8001/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Servidor funcionando: {data.get('mensaje', 'N/A')}")
            print(f"📦 Versión: {data.get('version', 'N/A')}")
        else:
            print("❌ Servidor no responde")
            return
        
        # 2. PROBAR RAG DE INVENTARIO
        print("\n📦 2. RAG DE INVENTARIO")
        print("-" * 40)
        
        consultas_inventario = [
            "¿Qué extintores tienen disponibles?",
            "Necesito cascos de seguridad",
            "¿Cuáles son los productos más baratos?",
            "¿Tienen equipos de protección personal?"
        ]
        
        for consulta in consultas_inventario:
            sistemas_rag["inventario"]["pruebas"] += 1
            
            data = {"mensaje": consulta, "chat_id": f"test_inv_{sistemas_rag['inventario']['pruebas']}"}
            response = await client.post("http://localhost:8001/chat/texto", json=data)
            
            if response.status_code == 200:
                result = response.json()
                tipo = result.get("tipo_mensaje", "")
                
                if tipo == "inventario":
                    sistemas_rag["inventario"]["exitosas"] += 1
                    print(f"✅ {consulta} → Tipo: {tipo}")
                else:
                    print(f"⚠️ {consulta} → Tipo: {tipo} (esperado: inventario)")
            else:
                print(f"❌ {consulta} → Error {response.status_code}")
            
            await asyncio.sleep(0.5)
        
        if sistemas_rag["inventario"]["exitosas"] > 0:
            sistemas_rag["inventario"]["funcionando"] = True
        
        # 3. PROBAR RAG DE VENTAS
        print("\n💰 3. RAG DE VENTAS")
        print("-" * 40)
        
        consultas_ventas = [
            "Quiero comprar 2 extintores de 10 libras",
            "¿Cuánto cuesta un casco de seguridad?",
            "Necesito hacer un pedido de productos",
            "¿Tienen descuentos en productos?"
        ]
        
        for consulta in consultas_ventas:
            sistemas_rag["ventas"]["pruebas"] += 1
            
            data = {"mensaje": consulta, "chat_id": f"test_ven_{sistemas_rag['ventas']['pruebas']}"}
            response = await client.post("http://localhost:8001/chat/texto", json=data)
            
            if response.status_code == 200:
                result = response.json()
                tipo = result.get("tipo_mensaje", "")
                estado_venta = result.get("estado_venta", "")
                
                if tipo in ["venta", "inventario"] or estado_venta:
                    sistemas_rag["ventas"]["exitosas"] += 1
                    print(f"✅ {consulta} → Tipo: {tipo}, Estado: {estado_venta}")
                else:
                    print(f"⚠️ {consulta} → Tipo: {tipo}")
            else:
                print(f"❌ {consulta} → Error {response.status_code}")
            
            await asyncio.sleep(0.5)
        
        if sistemas_rag["ventas"]["exitosas"] > 0:
            sistemas_rag["ventas"]["funcionando"] = True
        
        # 4. PROBAR RAG DE CLIENTES
        print("\n👥 4. RAG DE CLIENTES")
        print("-" * 40)
        
        # Verificar si hay clientes
        response = await client.get("http://localhost:8001/clientes/")
        if response.status_code == 200:
            clientes_data = response.json()
            total_clientes = clientes_data.get("total", 0)
            print(f"📊 Total clientes en BD: {total_clientes}")
            
            if total_clientes > 0:
                # Obtener primer cliente para pruebas
                primer_cliente = clientes_data["clientes"][0]
                cedula_test = primer_cliente.get("cedula", "")
                
                consultas_clientes = [
                    f"Buscar cliente con cédula {cedula_test}",
                    f"Historial del cliente {cedula_test}",
                    f"¿Cuántas compras ha hecho el cliente {cedula_test}?"
                ]
                
                for consulta in consultas_clientes:
                    sistemas_rag["clientes"]["pruebas"] += 1
                    
                    data = {"mensaje": consulta, "chat_id": f"test_cli_{sistemas_rag['clientes']['pruebas']}"}
                    response = await client.post("http://localhost:8001/chat/texto", json=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        respuesta = result.get("respuesta", "")
                        metadatos = result.get("metadatos", {})
                        
                        if cedula_test in respuesta or metadatos.get("encontrado", False):
                            sistemas_rag["clientes"]["exitosas"] += 1
                            print(f"✅ {consulta} → Cliente encontrado")
                        else:
                            print(f"⚠️ {consulta} → Cliente no encontrado en respuesta")
                    else:
                        print(f"❌ {consulta} → Error {response.status_code}")
                    
                    await asyncio.sleep(0.5)
            else:
                print("⚠️ No hay clientes en la BD para probar RAG")
        
        if sistemas_rag["clientes"]["exitosas"] > 0:
            sistemas_rag["clientes"]["funcionando"] = True
        
        # 5. PROBAR MEMORIA CONVERSACIONAL
        print("\n🧠 5. MEMORIA CONVERSACIONAL")
        print("-" * 40)
        
        chat_id_memoria = "test_memoria_completa"
        
        # Conversación de prueba
        conversacion = [
            "Hola, necesito información sobre extintores",
            "¿Cuáles son los precios?",
            "¿Cuánto cuesta el más barato?"
        ]
        
        for i, mensaje in enumerate(conversacion, 1):
            sistemas_rag["memoria"]["pruebas"] += 1
            
            data = {"mensaje": mensaje, "chat_id": chat_id_memoria}
            response = await client.post("http://localhost:8001/chat/texto", json=data)
            
            if response.status_code == 200:
                result = response.json()
                respuesta = result.get("respuesta", "")
                
                # En el segundo y tercer mensaje, verificar contexto
                if i > 1 and ("extintor" in respuesta.lower() or "precio" in respuesta.lower()):
                    sistemas_rag["memoria"]["exitosas"] += 1
                    print(f"✅ Mensaje {i}: Contexto mantenido")
                elif i == 1:
                    sistemas_rag["memoria"]["exitosas"] += 1
                    print(f"✅ Mensaje {i}: Respuesta inicial")
                else:
                    print(f"⚠️ Mensaje {i}: Posible pérdida de contexto")
            else:
                print(f"❌ Mensaje {i}: Error {response.status_code}")
            
            await asyncio.sleep(1)
        
        # Verificar historial
        response = await client.get(f"http://localhost:8001/chat/historial/{chat_id_memoria}")
        if response.status_code == 200:
            try:
                historial = response.json()
                if isinstance(historial, dict) and "mensajes" in historial:
                    mensajes_guardados = len(historial["mensajes"])
                    print(f"✅ Historial guardado: {mensajes_guardados} mensajes")
                    if mensajes_guardados >= len(conversacion):
                        sistemas_rag["memoria"]["funcionando"] = True
                else:
                    print("⚠️ Formato de historial inesperado")
            except:
                print("⚠️ Error procesando historial")
        else:
            print(f"❌ Error obteniendo historial: {response.status_code}")
        
        # 6. VERIFICAR ALMACENAMIENTO
        print("\n💾 6. ALMACENAMIENTO DE DATOS")
        print("-" * 40)
        
        response = await client.get("http://localhost:8001/exportar/info")
        if response.status_code == 200:
            info = response.json()
            export_info = info.get("info_exportacion", {})
            
            total_mensajes = export_info.get("total_mensajes", 0)
            mensajes_rag = export_info.get("mensajes_con_rag", 0)
            total_clientes = export_info.get("total_clientes", 0)
            total_ventas = export_info.get("total_ventas", 0)
            
            print(f"📊 Total mensajes: {total_mensajes}")
            print(f"🤖 Mensajes con RAG: {mensajes_rag}")
            print(f"👥 Total clientes: {total_clientes}")
            print(f"💰 Total ventas: {total_ventas}")
            
            if total_mensajes > 0:
                sistemas_rag["almacenamiento"]["funcionando"] = True
                sistemas_rag["almacenamiento"]["exitosas"] = 1
            
            sistemas_rag["almacenamiento"]["pruebas"] = 1
        else:
            print(f"❌ Error obteniendo información: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
    
    finally:
        await client.aclose()
    
    # GENERAR REPORTE FINAL
    print("\n" + "="*80)
    print("📋 REPORTE FINAL DEL ESTADO DE SISTEMAS RAG")
    print("="*80)
    
    total_sistemas = len(sistemas_rag)
    sistemas_funcionando = sum(1 for sistema in sistemas_rag.values() if sistema["funcionando"])
    
    print(f"\n🎯 RESUMEN GENERAL:")
    print(f"   ✅ Sistemas funcionando: {sistemas_funcionando}/{total_sistemas}")
    print(f"   📊 Porcentaje de éxito: {(sistemas_funcionando/total_sistemas)*100:.1f}%")
    
    print(f"\n📊 DETALLES POR SISTEMA:")
    
    for nombre, datos in sistemas_rag.items():
        status = "✅ FUNCIONANDO" if datos["funcionando"] else "❌ CON PROBLEMAS"
        exito_rate = (datos["exitosas"]/datos["pruebas"]*100) if datos["pruebas"] > 0 else 0
        
        print(f"\n   🔹 {nombre.upper()}: {status}")
        print(f"      Pruebas: {datos['exitosas']}/{datos['pruebas']} ({exito_rate:.1f}%)")
    
    print(f"\n💡 RECOMENDACIONES:")
    
    if sistemas_funcionando == total_sistemas:
        print("   🎉 ¡Todos los sistemas RAG están funcionando perfectamente!")
        print("   🚀 El chatbot está completamente operativo")
        print("   ✅ Memoria conversacional activa")
        print("   ✅ Almacenamiento de datos funcionando")
        print("   ✅ Todos los tipos de consulta soportados")
    else:
        print("   ⚠️ Algunos sistemas necesitan atención:")
        
        for nombre, datos in sistemas_rag.items():
            if not datos["funcionando"]:
                if nombre == "inventario":
                    print("   - Revisar configuración del RAG de inventario")
                elif nombre == "ventas":
                    print("   - Verificar sistema de ventas y pedidos")
                elif nombre == "clientes":
                    print("   - Revisar sistema de clientes (puede necesitar más datos)")
                elif nombre == "memoria":
                    print("   - Verificar almacenamiento de conversaciones")
                elif nombre == "almacenamiento":
                    print("   - Revisar conexión a base de datos")
    
    print(f"\n🔧 SISTEMAS RAG IDENTIFICADOS:")
    print("   1. 📦 RAG de Inventario - Búsqueda de productos")
    print("   2. 💰 RAG de Ventas - Procesamiento de pedidos")
    print("   3. 👥 RAG de Clientes - Consultas de historial")
    print("   4. 🧠 Memoria Conversacional - Contexto entre mensajes")
    print("   5. 💾 Almacenamiento - Persistencia de datos")
    
    print(f"\n📈 MÉTRICAS DE RENDIMIENTO:")
    total_pruebas = sum(datos["pruebas"] for datos in sistemas_rag.values())
    total_exitosas = sum(datos["exitosas"] for datos in sistemas_rag.values())
    rendimiento_general = (total_exitosas/total_pruebas*100) if total_pruebas > 0 else 0
    
    print(f"   📊 Total de pruebas realizadas: {total_pruebas}")
    print(f"   ✅ Pruebas exitosas: {total_exitosas}")
    print(f"   🎯 Rendimiento general: {rendimiento_general:.1f}%")
    
    print("\n" + "="*80)
    print("🎯 REPORTE COMPLETADO")
    print("="*80)
    
    return sistemas_funcionando == total_sistemas

if __name__ == "__main__":
    asyncio.run(generar_reporte_rag()) 