from typing import Any, Dict, Optional
from app.services.llm_client import generar_respuesta
from app.services.retrieval.retriever_factory import get_retriever
from app.models.producto import Producto
from sqlalchemy.future import select
from app.services.prompts import prompt_ventas, prompt_empresa
from app.services.contextos import CONTEXTO_EMPRESA_SEXTINVALLE
from app.services.logs import registrar_log
import logging

async def consultar_rag(
    mensaje: str,
    tipo: str,
    db,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Sextinvalle",  # <-- Unificado
    tono: str = "formal",
    instrucciones: str = "",
    usuario_id: int = None,
    llm: str = "openai",
    **kwargs
) -> dict:
    """
    Pipeline RAG: retrieval, generación y respuesta.
    """
    try:
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
                    instrucciones=instrucciones + "\nIMPORTANTE: Si no hay productos en el inventario, responde claramente que no tenemos productos disponibles para esa consulta. No inventes ni sugieras productos fuera del inventario."
                )
            else:
                system_prompt, user_prompt = prompt_ventas(
                    contexto=contexto,
                    mensaje=mensaje,
                    nombre_agente=nombre_agente,
                    nombre_empresa=nombre_empresa,
                    tono=tono,
                    instrucciones=instrucciones
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
                instrucciones=instrucciones
            )
        else:
            logging.warning(f"[consultar_rag] Tipo de consulta no soportado: {tipo}")
            return {
                "respuesta": "Lo siento, no entendí tu pregunta. ¿Puedes reformularla o ser más específico?",
                "contexto": "",
                "prompt": {}
            }

        # Log completo de prompts enviados al LLM
        logging.info(f"[consultar_rag] PROMPT SYSTEM:\n{system_prompt}")
        logging.info(f"[consultar_rag] PROMPT USER:\n{user_prompt}")

        logging.info(f"[consultar_rag] Antes de llamada al LLM (generar_respuesta)")
        respuesta = await generar_respuesta(
            prompt=user_prompt,
            llm=llm,
            system_prompt=system_prompt,
            **kwargs
        )
        logging.info(f"[consultar_rag] Respuesta LLM: {respuesta}")

        return {
            "respuesta": respuesta,
            "contexto": contexto,
            "prompt": {
                "system": system_prompt,
                "user": user_prompt
            }
        }
    except Exception as e:
        logging.error(f"[consultar_rag] Error en consulta RAG: {str(e)}")
        return {
            "respuesta": "Tuvimos un problema procesando tu pregunta. Por favor, intenta de nuevo o pregunta algo diferente.",
            "contexto": "",
            "prompt": {}
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
