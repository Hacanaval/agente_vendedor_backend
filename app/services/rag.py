from typing import Any, Dict, Optional
import logging
from sqlalchemy.future import select
from app.services.llm_client import generar_respuesta
from app.services.retrieval.retriever_factory import get_retriever
from app.models.producto import Producto
from app.models.mensaje import Mensaje
from app.services.prompts import prompt_ventas, prompt_empresa
from app.services.contextos import CONTEXTO_EMPRESA_SEXTINVALLE

async def consultar_rag(
    mensaje: str,
    tipo: str,
    db,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Sextinvalle",
    tono: str = "formal",
    instrucciones: str = "",
    usuario_id: int = None,
    llm: str = "gemini",
    chat_id: str = None,
    **kwargs
) -> dict:
    """
    Pipeline RAG: retrieval, generación y respuesta.
    """
    try:
        # Memoria conversacional reciente (últimos 10 mensajes)
        historial_contexto = ""
        if chat_id:
            result = await db.execute(
                select(Mensaje)
                .where(Mensaje.chat_id == chat_id)
                .order_by(Mensaje.timestamp.desc())
                .limit(10)
            )
            historial = result.scalars().all()[::-1]  # Orden cronológico
            historial_contexto = "\n".join([
                f"{m.remitente}: {m.mensaje}" + 
                (f" (Estado: {m.estado_venta})" if m.estado_venta else "")
                for m in historial
            ])
            logging.info(f"[consultar_rag] Historial de conversación: {historial_contexto[:300]}...")

        # Retrieval según tipo de consulta
        logging.info(f"[consultar_rag] Tipo de consulta recibido: {tipo}")
        if tipo in ("inventario", "venta"):
            contexto = await retrieval_inventario(mensaje, db)
            instrucciones_extra = instrucciones + (
                "\nIMPORTANTE:\n1. Si no hay productos en el inventario, responde claramente que no tenemos productos disponibles para esa consulta.\n"
                "2. No inventes ni sugieras productos fuera del inventario.\n"
                f"3. Historial reciente de la conversación:\n{historial_contexto}\n"
            )
            system_prompt, user_prompt = prompt_ventas(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones_extra
            )
            logging.info(f"[consultar_rag] Contexto inventario obtenido: {contexto[:200]}...")
        elif tipo == "contexto":
            contexto = await retrieval_contexto_empresa(mensaje, db)
            if not contexto or contexto.strip() == "":
                contexto = "No se encontró información relevante sobre la empresa."
            instrucciones_extra = instrucciones + (
                f"\nHistorial reciente de la conversación:\n{historial_contexto}\n"
            )
            system_prompt, user_prompt = prompt_empresa(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones_extra
            )
            logging.info(f"[consultar_rag] Contexto empresa obtenido: {contexto[:200]}...")
        else:
            return {
                "respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes reformularla o ser más específico?",
                "estado_venta": None,
                "tipo_mensaje": tipo,
                "metadatos": None
            }

        # LLM (responde usando prompt)
        respuesta = await generar_respuesta(
            prompt=user_prompt,
            system_prompt=system_prompt,
            llm=llm
        )

        # Estado de venta: heurística básica
        estado_venta = None
        metadatos = None
        if tipo == "venta":
            if any(x in respuesta.lower() for x in ["¿deseas", "quieres confirmar", "te gustaría agregarlo", "confirmar pedido"]):
                estado_venta = "pendiente"
            elif any(x in respuesta.lower() for x in ["pedido registrado", "compra confirmada", "venta realizada"]):
                estado_venta = "cerrada"
            elif any(x in mensaje.lower() for x in ["cotización", "precio", "costo"]):
                estado_venta = "iniciada"

        return {
            "respuesta": respuesta,
            "estado_venta": estado_venta,
            "tipo_mensaje": tipo,
            "metadatos": metadatos
        }

    except Exception as e:
        logging.error(f"[consultar_rag] Error: {str(e)}")
        return {
            "respuesta": "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
            "estado_venta": None,
            "tipo_mensaje": tipo,
            "metadatos": None
        }

async def retrieval_inventario(mensaje: str, db):
    """
    Recupera productos relevantes usando búsqueda semántica (FAISS o Pinecone).
    Solo productos activos y con stock > 0.
    """
    try:
        retriever = get_retriever(db)
        await retriever.sync_with_db()  # Reconstruye el índice si es necesario
        ids = await retriever.search(mensaje, top_k=5)
        if not ids:
            logging.info("[retrieval_inventario] No se encontraron productos relevantes para la búsqueda")
            return "No se encontraron productos relevantes."
        
        result = await db.execute(
            select(Producto).where(
                Producto.id.in_(ids),
                Producto.activo == True,
                Producto.stock > 0
            )
        )
        productos = result.scalars().all()
        if not productos:
            logging.info("[retrieval_inventario] No hay productos disponibles con stock > 0")
            return "No hay productos disponibles actualmente."
        
        contexto = [
            f"{p.nombre}: {p.descripcion} (Precio: ${p.precio:,.2f}, Stock: {p.stock})"
            for p in productos
        ]
        contexto_str = "\n".join(contexto)
        logging.info(f"[retrieval_inventario] Contexto encontrado: {contexto_str[:200]}...")
        return contexto_str
    except Exception as e:
        logging.error(f"[retrieval_inventario] Error: {str(e)}")
        return "Error al buscar productos. Por favor, intenta de nuevo."

async def retrieval_contexto_empresa(mensaje: str, db):
    """
    Recupera contexto de la empresa.
    (Actualmente estático, pero puede mejorarse para cargar dinámicamente en el futuro).
    """
    return CONTEXTO_EMPRESA_SEXTINVALLE
