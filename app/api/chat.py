from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.usuario import Usuario
from app.models.empresa import Empresa
from typing import Dict, Any, Optional
from app.services.rag import consultar_rag
from pydantic import BaseModel, Field
import logging
from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000)
    tipo: Optional[str] = Field(default=None, pattern="^(inventario|contexto|venta)$")
    tono: str = Field(default="formal", pattern="^(formal|informal|amigable|profesional)$")
    instrucciones: str = Field(default="", max_length=500)
    llm: str = Field(default="openai", pattern="^(openai|gemini|cohere|local)$")

@router.post("/", response_model=Dict[str, Any])
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint de chat tipo RAG: responde consultas de inventario, venta o contexto según tipo.
    Si 'tipo' no viene, se clasifica automáticamente usando LLM.
    
    - tipo: "inventario" (consulta productos), "contexto" (consulta info empresa) o "venta" (consulta info venta)
    - tono: "formal", "informal", "amigable", "profesional"
    - instrucciones: instrucciones adicionales para el LLM
    - llm: modelo de lenguaje a usar (por ahora solo "openai")
    """
    try:
        # Obtener info de la empresa
        empresa = await db.get(Empresa, current_user.empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        # Clasificación automática si no viene tipo
        tipo = req.tipo
        if not tipo:
            tipo = await clasificar_tipo_mensaje_llm(req.mensaje)

        # Consultar RAG
        respuesta = await consultar_rag(
            mensaje=req.mensaje,
            tipo=tipo,
            empresa_id=current_user.empresa_id,
            db=db,
            nombre_agente=current_user.nombre,
            nombre_empresa=empresa.nombre,
            tono=req.tono,
            instrucciones=req.instrucciones,
            usuario_id=current_user.id,
            llm=req.llm
        )
        
        return respuesta

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error en endpoint chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al procesar la consulta"
        )
