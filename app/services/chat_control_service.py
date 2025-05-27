from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.chat_control import ChatControl
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ChatControlService:
    """
    Servicio para gestionar el control del chatbot a nivel global y por conversación.
    """
    
    @staticmethod
    async def is_ia_activa_global(db: AsyncSession) -> bool:
        """
        Verifica si la IA está activa globalmente.
        
        Returns:
            bool: True si la IA está activa globalmente, False si está desactivada
        """
        try:
            result = await db.execute(
                select(ChatControl).where(
                    and_(
                        ChatControl.tipo_control == "global",
                        ChatControl.chat_id.is_(None)
                    )
                )
            )
            control_global = result.scalar_one_or_none()
            
            # Si no existe registro, por defecto la IA está activa
            if control_global is None:
                return True
            
            return control_global.ia_activa
        except Exception as e:
            logger.error(f"Error verificando estado global de IA: {e}")
            return True  # Por defecto activa en caso de error

    @staticmethod
    async def is_ia_activa_conversacion(db: AsyncSession, chat_id: str) -> bool:
        """
        Verifica si la IA está activa para una conversación específica.
        
        Args:
            chat_id: ID de la conversación
            
        Returns:
            bool: True si la IA está activa para esa conversación
        """
        try:
            result = await db.execute(
                select(ChatControl).where(
                    and_(
                        ChatControl.tipo_control == "conversacion",
                        ChatControl.chat_id == chat_id
                    )
                )
            )
            control_conversacion = result.scalar_one_or_none()
            
            # Si no existe registro específico, por defecto la IA está activa
            if control_conversacion is None:
                return True
            
            return control_conversacion.ia_activa
        except Exception as e:
            logger.error(f"Error verificando estado de IA para conversación {chat_id}: {e}")
            return True  # Por defecto activa en caso de error

    @staticmethod
    async def debe_responder_ia(db: AsyncSession, chat_id: str) -> Tuple[bool, str]:
        """
        Determina si la IA debe responder en una conversación específica.
        Considera tanto el estado global como el específico de la conversación.
        
        Args:
            chat_id: ID de la conversación
            
        Returns:
            Tuple[bool, str]: (debe_responder, razon_si_no)
        """
        # Verificar estado global primero
        ia_global_activa = await ChatControlService.is_ia_activa_global(db)
        if not ia_global_activa:
            return False, "IA desactivada globalmente por un administrador"
        
        # Verificar estado específico de la conversación
        ia_conversacion_activa = await ChatControlService.is_ia_activa_conversacion(db, chat_id)
        if not ia_conversacion_activa:
            return False, "IA desactivada para esta conversación - un humano continuará"
        
        return True, "IA activa"

    @staticmethod
    async def toggle_ia_global(
        db: AsyncSession, 
        activar: bool, 
        usuario: Optional[str] = None, 
        motivo: Optional[str] = None
    ) -> ChatControl:
        """
        Activa o desactiva la IA globalmente.
        
        Args:
            activar: True para activar, False para desactivar
            usuario: Usuario que realiza el cambio
            motivo: Motivo del cambio
            
        Returns:
            ChatControl: Registro actualizado o creado
        """
        try:
            # Buscar control global existente
            result = await db.execute(
                select(ChatControl).where(
                    and_(
                        ChatControl.tipo_control == "global",
                        ChatControl.chat_id.is_(None)
                    )
                )
            )
            control_global = result.scalar_one_or_none()
            
            if control_global:
                # Actualizar existente
                control_global.ia_activa = activar
                control_global.motivo_desactivacion = motivo if not activar else None
                control_global.usuario_que_desactivo = usuario if not activar else None
            else:
                # Crear nuevo
                control_global = ChatControl(
                    chat_id=None,
                    ia_activa=activar,
                    tipo_control="global",
                    motivo_desactivacion=motivo if not activar else None,
                    usuario_que_desactivo=usuario if not activar else None
                )
                db.add(control_global)
            
            await db.commit()
            await db.refresh(control_global)
            
            estado = "activada" if activar else "desactivada"
            logger.info(f"IA {estado} globalmente por usuario: {usuario or 'Sistema'}")
            
            return control_global
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cambiando estado global de IA: {e}")
            raise

    @staticmethod
    async def toggle_ia_conversacion(
        db: AsyncSession,
        chat_id: str,
        activar: bool,
        usuario: Optional[str] = None,
        motivo: Optional[str] = None
    ) -> ChatControl:
        """
        Activa o desactiva la IA para una conversación específica.
        
        Args:
            chat_id: ID de la conversación
            activar: True para activar, False para desactivar  
            usuario: Usuario que realiza el cambio
            motivo: Motivo del cambio
            
        Returns:
            ChatControl: Registro actualizado o creado
        """
        try:
            # Buscar control de conversación existente
            result = await db.execute(
                select(ChatControl).where(
                    and_(
                        ChatControl.tipo_control == "conversacion",
                        ChatControl.chat_id == chat_id
                    )
                )
            )
            control_conversacion = result.scalar_one_or_none()
            
            if control_conversacion:
                # Actualizar existente
                control_conversacion.ia_activa = activar
                control_conversacion.motivo_desactivacion = motivo if not activar else None
                control_conversacion.usuario_que_desactivo = usuario if not activar else None
            else:
                # Crear nuevo
                control_conversacion = ChatControl(
                    chat_id=chat_id,
                    ia_activa=activar,
                    tipo_control="conversacion",
                    motivo_desactivacion=motivo if not activar else None,
                    usuario_que_desactivo=usuario if not activar else None
                )
                db.add(control_conversacion)
            
            await db.commit()
            await db.refresh(control_conversacion)
            
            estado = "activada" if activar else "desactivada"
            logger.info(f"IA {estado} para conversación {chat_id} por usuario: {usuario or 'Sistema'}")
            
            return control_conversacion
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cambiando estado de IA para conversación {chat_id}: {e}")
            raise

    @staticmethod
    async def get_estado_sistema(db: AsyncSession) -> dict:
        """
        Obtiene el estado completo del sistema de IA.
        
        Returns:
            dict: Estado del sistema con estadísticas
        """
        try:
            # Estado global
            ia_global_activa = await ChatControlService.is_ia_activa_global(db)
            
            # Contar conversaciones desactivadas
            result = await db.execute(
                select(ChatControl).where(
                    and_(
                        ChatControl.tipo_control == "conversacion",
                        ChatControl.ia_activa == False
                    )
                )
            )
            conversaciones_desactivadas = len(result.scalars().all())
            
            # Total de conversaciones monitoreadas
            result = await db.execute(
                select(ChatControl).where(ChatControl.tipo_control == "conversacion")
            )
            total_conversaciones = len(result.scalars().all())
            
            return {
                "sistema_ia_activo": ia_global_activa,
                "conversaciones_desactivadas": conversaciones_desactivadas,
                "total_conversaciones_monitoreadas": total_conversaciones
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}")
            return {
                "sistema_ia_activo": True,
                "conversaciones_desactivadas": 0,
                "total_conversaciones_monitoreadas": 0
            } 