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
    empresa_id: int,
    db,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Empresa",
    tono: str = "formal",
    instrucciones: str = "",
    usuario_id: Optional[int] = None,
    llm: str = "openai",
    **kwargs
) -> Dict[str, Any]:
    """
    Consulta RAG: recupera contexto relevante y genera respuesta usando LLM.
    
    Args:
        mensaje: Pregunta del usuario
        tipo: "inventario" o "contexto"
        empresa_id: ID de la empresa
        db: Sesión de base de datos
        nombre_agente: Nombre del agente AI
        nombre_empresa: Nombre de la empresa
        tono: Tono de la respuesta ("formal", "informal", etc)
        instrucciones: Instrucciones adicionales para el LLM
        usuario_id: ID del usuario (opcional, para logs)
        llm: LLM a usar ("openai" por defecto)
        **kwargs: Parámetros adicionales para el LLM
    
    Returns:
        Dict con respuesta, contexto y prompt usado
    """
    logging.info(f"[consultar_rag] Entrada: mensaje={mensaje}, tipo={tipo}, empresa_id={empresa_id}, llm={llm}")
    try:
        # 1. Retrieval según tipo
        logging.info(f"[consultar_rag] Antes de retrieval para tipo={tipo}")
        if tipo == "inventario":
            contexto = await retrieval_inventario(mensaje, empresa_id, db)
            logging.info(f"[consultar_rag] Contexto inventario obtenido: {contexto[:200]}...")
            system_prompt, user_prompt = prompt_ventas(
                contexto=contexto,
                mensaje=mensaje,
                nombre_agente=nombre_agente,
                nombre_empresa=nombre_empresa,
                tono=tono,
                instrucciones=instrucciones
            )
        elif tipo == "contexto":
            contexto = await retrieval_contexto_empresa(mensaje, empresa_id, db)
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
            raise ValueError(f"Tipo de consulta no soportado: {tipo}")

        logging.info(f"[consultar_rag] Antes de llamada al LLM (generar_respuesta)")
        respuesta = await generar_respuesta(
            prompt=user_prompt,
            llm=llm,
            system_prompt=system_prompt,
            **kwargs
        )
        logging.info(f"[consultar_rag] Respuesta LLM: {respuesta}")

        # 3. Registrar log si hay usuario_id
        if usuario_id:
            await registrar_log(
                db=db,
                empresa_id=empresa_id,
                usuario_id=usuario_id,
                modelo="chat",
                accion="consulta_rag",
                detalle={
                    "tipo": tipo,
                    "mensaje": mensaje,
                    "respuesta": respuesta,
                    "contexto": contexto[:500] + "..." if len(contexto) > 500 else contexto
                }
            )

        logging.info(f"[consultar_rag] Justo antes de return")
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
        raise

async def retrieval_inventario(mensaje: str, empresa_id: int, db):
    """
    Recupera productos relevantes usando búsqueda semántica.
    """
    try:
        retriever = get_retriever(empresa_id, db)
        await retriever.sync_with_db()  # Reconstruye el índice si es necesario
        ids = await retriever.search(mensaje, top_k=5)
        if not ids:
            return "No se encontraron productos relevantes."
        
        result = await db.execute(
            select(Producto).where(
                Producto.id.in_(ids),
                Producto.empresa_id == empresa_id,
                Producto.activo == True
            )
        )
        productos = result.scalars().all()
        
        if not productos:
            return "No hay productos disponibles actualmente."
            
        contexto = [
            f"{p.nombre}: {p.descripcion} (Precio: ${p.precio:,.2f}, Stock: {p.stock})"
            for p in productos
        ]
        return "\n".join(contexto)
        
    except Exception as e:
        logging.error(f"Error en retrieval_inventario: {str(e)}")
        return "Error al buscar productos. Por favor, intenta de nuevo."

async def retrieval_contexto_empresa(mensaje: str, empresa_id: int, db):
    """
    Recupera contexto de la empresa.
    Por ahora usa un contexto estático, pero se puede extender para cargar dinámicamente.
    """
    return CONTEXTO_EMPRESA_SEXTINVALLE
