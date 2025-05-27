from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.chat_control_service import ChatControlService
from app.schemas.chat_control import (
    ControlGlobalResponse, 
    ControlConversacionResponse, 
    EstadoSistemaResponse,
    ChatControlUpdate
)
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat-control", tags=["Control de Chatbot"])

# =====================================================
# ENDPOINTS PARA BOTÓN "Sistema IA ON/OFF" 
# =====================================================

@router.post("/sistema/toggle", response_model=ControlGlobalResponse)
async def toggle_sistema_ia(
    activar: bool = Body(..., description="True para activar, False para desactivar"),
    usuario: Optional[str] = Body(None, description="Usuario que realiza el cambio"),
    motivo: Optional[str] = Body(None, description="Motivo del cambio"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔴 BOTÓN "Sistema IA ON/OFF"
    
    Activa o desactiva la IA globalmente para TODAS las conversaciones.
    Cuando está desactivada, ningún chat recibirá respuestas automáticas.
    
    - **activar**: True = IA activa globalmente, False = IA desactivada globalmente
    - **usuario**: Nombre del usuario que realiza el cambio (opcional)
    - **motivo**: Razón del cambio (opcional)
    """
    try:
        control = await ChatControlService.toggle_ia_global(
            db=db,
            activar=activar,
            usuario=usuario,
            motivo=motivo
        )
        
        estado_texto = "activado" if activar else "desactivado"
        mensaje = f"Sistema de IA {estado_texto} globalmente"
        if usuario:
            mensaje += f" por {usuario}"
        if motivo and not activar:
            mensaje += f". Motivo: {motivo}"
        
        return ControlGlobalResponse(
            sistema_ia_activo=control.ia_activa,
            mensaje=mensaje,
            fecha_cambio=control.fecha_cambio,
            usuario_que_desactivo=control.usuario_que_desactivo
        )
        
    except Exception as e:
        logger.error(f"Error en toggle_sistema_ia: {e}")
        raise HTTPException(status_code=500, detail=f"Error al cambiar estado del sistema: {str(e)}")

@router.get("/sistema/estado", response_model=ControlGlobalResponse)
async def get_estado_sistema_ia(db: AsyncSession = Depends(get_db)):
    """
    📊 Obtiene el estado actual del sistema de IA global.
    
    Útil para sincronizar el estado del botón "Sistema IA ON/OFF" en el frontend.
    Siempre garantiza que exista un registro por defecto (ON).
    """
    try:
        # Asegurar que existe registro por defecto primero
        await ChatControlService.ensure_default_global_state(db)
        
        ia_activa = await ChatControlService.is_ia_activa_global(db)
        
        estado_texto = "activo" if ia_activa else "desactivado"
        mensaje = f"Sistema de IA está {estado_texto} globalmente"
        
        return ControlGlobalResponse(
            sistema_ia_activo=ia_activa,
            mensaje=mensaje
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener estado del sistema: {str(e)}")

# =====================================================
# ENDPOINTS PARA BOTÓN "IA Conversación"
# =====================================================

@router.post("/conversacion/{chat_id}/toggle", response_model=ControlConversacionResponse)
async def toggle_ia_conversacion(
    chat_id: str,
    activar: bool = Body(..., description="True para activar IA, False para que continúe un humano"),
    usuario: Optional[str] = Body(None, description="Usuario que realiza el cambio"),
    motivo: Optional[str] = Body(None, description="Motivo del cambio"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔵 BOTÓN "IA Conversación"
    
    Activa o desactiva la IA solo para una conversación específica.
    Cuando está desactivada, un humano puede tomar el control de esa conversación.
    
    - **chat_id**: ID de la conversación específica
    - **activar**: True = IA responde, False = Humano toma el control
    - **usuario**: Nombre del usuario que realiza el cambio (opcional)
    - **motivo**: Razón del cambio (opcional)
    """
    try:
        control = await ChatControlService.toggle_ia_conversacion(
            db=db,
            chat_id=chat_id,
            activar=activar,
            usuario=usuario,
            motivo=motivo
        )
        
        if activar:
            mensaje = f"IA reactivada para conversación {chat_id}"
        else:
            mensaje = f"IA desactivada para conversación {chat_id} - Un humano continuará"
        
        if usuario:
            mensaje += f" por {usuario}"
        if motivo and not activar:
            mensaje += f". Motivo: {motivo}"
        
        return ControlConversacionResponse(
            chat_id=chat_id,
            ia_conversacion_activa=control.ia_activa,
            mensaje=mensaje,
            fecha_cambio=control.fecha_cambio,
            usuario_que_desactivo=control.usuario_que_desactivo
        )
        
    except Exception as e:
        logger.error(f"Error en toggle_ia_conversacion para {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al cambiar estado de conversación: {str(e)}")

@router.get("/conversacion/{chat_id}/estado", response_model=ControlConversacionResponse)
async def get_estado_ia_conversacion(chat_id: str, db: AsyncSession = Depends(get_db)):
    """
    📊 Obtiene el estado actual de la IA para una conversación específica.
    
    Útil para sincronizar el estado del botón "IA Conversación" en el frontend.
    """
    try:
        ia_activa = await ChatControlService.is_ia_activa_conversacion(db, chat_id)
        
        if ia_activa:
            mensaje = f"IA está activa para conversación {chat_id}"
        else:
            mensaje = f"IA está desactivada para conversación {chat_id} - Un humano continuará"
        
        return ControlConversacionResponse(
            chat_id=chat_id,
            ia_conversacion_activa=ia_activa,
            mensaje=mensaje
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de conversación {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener estado de conversación: {str(e)}")

# =====================================================
# ENDPOINT PARA VERIFICAR SI IA DEBE RESPONDER
# =====================================================

@router.get("/debe-responder/{chat_id}")
async def verificar_debe_responder_ia(chat_id: str, db: AsyncSession = Depends(get_db)):
    """
    🤖 Verifica si la IA debe responder en una conversación específica.
    
    Considera tanto el estado global como el específico de la conversación.
    Este endpoint es usado internamente por el sistema de chat.
    """
    try:
        debe_responder, razon = await ChatControlService.debe_responder_ia(db, chat_id)
        
        return {
            "chat_id": chat_id,
            "debe_responder": debe_responder,
            "razon": razon,
            "timestamp": "2025-05-27T15:00:00"
        }
        
    except Exception as e:
        logger.error(f"Error verificando si debe responder IA para {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al verificar estado: {str(e)}")

# =====================================================
# ENDPOINT DE ESTADÍSTICAS GENERALES
# =====================================================

@router.get("/estadisticas", response_model=EstadoSistemaResponse)
async def get_estadisticas_sistema(db: AsyncSession = Depends(get_db)):
    """
    📈 Obtiene estadísticas completas del sistema de control de IA.
    
    Útil para dashboards y monitoreo general del sistema.
    """
    try:
        estadisticas = await ChatControlService.get_estado_sistema(db)
        
        return EstadoSistemaResponse(
            sistema_ia_activo=estadisticas["sistema_ia_activo"],
            conversaciones_desactivadas=estadisticas["conversaciones_desactivadas"],
            total_conversaciones_monitoreadas=estadisticas["total_conversaciones_monitoreadas"]
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del sistema: {e}")
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}") 