from typing import Any, Dict, Optional
from app.services.llm_client import generar_respuesta
from app.services.retrieval.retriever_factory import get_retriever
from app.models.producto import Producto
from sqlalchemy.future import select
from app.services.prompts import prompt_ventas, prompt_empresa
from app.services.contextos import CONTEXTO_EMPRESA_SEXTINVALLE
from app.services.logs import registrar_log
import logging
from app.models.mensaje import Mensaje

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
        # Obtener historial de conversación relevante
        historial_contexto = ""
        if chat_id:
            result = await db.execute(
                select(Mensaje)
                .where(Mensaje.chat_id == chat_id)
                .order_by(Mensaje.timestamp.desc())
                .limit(5)
            )
            historial = result.scalars().all()[::-1]  # Los 5 más recientes, en orden cronológico
            historial_contexto = "\n".join([
                f"{m.remitente}: {m.mensaje}" + 
                (f" (Estado: {m.estado_venta})" if m.estado_venta else "")
                for m in historial
            ])
            logging.info(f"[consultar_rag] Historial de conversación: {historial_contexto[:200]}...")

        # 1. Retrieval según tipo
        logging.info(f"[consultar_rag] Tipo de consulta recibido: {tipo}")
        if tipo in ("inventario", "venta"):
            contexto = await retrieval_inventario(mensaje, db)
            if not contexto or contexto.strip() == "" or contexto.startswith("No se encontraron") or contexto.startswith("No hay productos"):
                logging.info("[consultar_rag] No hay productos disponibles, agregando instrucción especial al prompt")
                system_prompt, user_prompt = prompt_ventas(
                    contexto=contexto,
                    mensaje=mensaje,
                    nombre_agente=nombre_agente,
                    nombre_empresa=nombre_empresa,
                    tono=tono,
                    instrucciones=instrucciones + "\n" + 
                        "IMPORTANTE:\n" +
                        "1. Si no hay productos en el inventario, responde claramente que no tenemos productos disponibles para esa consulta.\n" +
                        "2. No inventes ni sugieras productos fuera del inventario.\n" +
                        "3. Ten en cuenta el siguiente historial de la conversación:\n" + historial_contexto
                )
            else:
                system_prompt, user_prompt = prompt_ventas(
                    contexto=contexto,
                    mensaje=mensaje,
                    nombre_agente=nombre_agente,
                    nombre_empresa=nombre_empresa,
                    tono=tono,
                    instrucciones=instrucciones + "\nTen en cuenta el siguiente historial de la conversación:\n" + historial_contexto
                )
            logging.info(f"[consultar_rag] Contexto inventario obtenido: {contexto[:200]}...")
        elif tipo == "contexto":
            contexto = await retrieval_contexto_empresa(mensaje, db)
            if not contexto or contexto.strip() == "":
                contexto = "No se encontró información relevante sobre la empresa."
            logging.info(f"[consultar_rag] Contexto empresa obtenido: {contexto[:200]}...")
            system_prompt, user_prompt = prompt_empresa(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones + "\nTen en cuenta el siguiente historial de la conversación:\n" + historial_contexto
            )

        # 2. Generar respuesta
        respuesta = await generar_respuesta(
            prompt=user_prompt,
            system_prompt=system_prompt,
            llm=llm
        )

        # 3. Determinar estado de venta si aplica
        estado_venta = None
        metadatos = None
        if tipo == "venta":
            if any(palabra in respuesta.lower() for palabra in ["¿deseas", "quieres confirmar", "te gustaría agregarlo", "confirmar pedido"]):
                estado_venta = "pendiente"
            elif any(palabra in respuesta.lower() for palabra in ["pedido registrado", "compra confirmada", "venta realizada"]):
                estado_venta = "cerrada"
            elif any(palabra in mensaje.lower() for palabra in ["cotización", "precio", "costo"]):
                estado_venta = "iniciada"

        return {
            "respuesta": respuesta,
            "estado_venta": estado_venta,
            "tipo_mensaje": tipo,
            "metadatos": metadatos
        }

    except Exception as e:
        logging.error(f"Error en consultar_rag: {str(e)}")
        return {
            "respuesta": "Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.",
            "estado_venta": None,
            "tipo_mensaje": tipo,
            "metadatos": None
        }

async def retrieval_inventario(mensaje: str, db):
    """
    Recupera productos relevantes usando búsqueda semántica.
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
        logging.error(f"Error en retrieval_inventario: {str(e)}")
        return "Error al buscar productos. Por favor, intenta de nuevo."

async def retrieval_contexto_empresa(mensaje: str, db):
    """
    Recupera contexto de la empresa.
    Por ahora usa un contexto estático, pero se puede extender para cargar dinámicamente.
    """
    return CONTEXTO_EMPRESA_SEXTINVALLE
