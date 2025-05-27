from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.base_class import Base

class ChatControl(Base):
    """
    Modelo para controlar el estado del chatbot.
    
    Permite desactivar el chatbot globalmente o por conversación específica.
    """
    __tablename__ = "chat_control"
    
    id = Column(Integer, primary_key=True, index=True, comment="ID único del control")
    chat_id = Column(String(255), nullable=True, index=True, comment="ID del chat específico (null = control global)")
    ia_activa = Column(Boolean, default=True, nullable=False, comment="Si la IA está activa para este chat/global")
    tipo_control = Column(String(50), nullable=False, comment="'global' o 'conversacion'")
    motivo_desactivacion = Column(Text, nullable=True, comment="Razón por la cual se desactivó")
    usuario_que_desactivo = Column(String(255), nullable=True, comment="Usuario que realizó el cambio")
    fecha_cambio = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Fecha del cambio")
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        tipo = "Global" if self.chat_id is None else f"Chat {self.chat_id}"
        estado = "Activa" if self.ia_activa else "Inactiva"
        return f"<ChatControl({tipo}: IA {estado})>"
    
    def to_dict(self):
        """Convierte el control a diccionario para APIs"""
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "ia_activa": self.ia_activa,
            "tipo_control": self.tipo_control,
            "motivo_desactivacion": self.motivo_desactivacion,
            "usuario_que_desactivo": self.usuario_que_desactivo,
            "fecha_cambio": self.fecha_cambio.isoformat() if self.fecha_cambio else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        } 