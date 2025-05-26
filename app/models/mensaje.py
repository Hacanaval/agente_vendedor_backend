from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Mensaje(Base):
    __tablename__ = "mensaje"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    remitente = Column(String, nullable=False)  # 'usuario', 'agente', 'bot'
    mensaje = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    estado_venta = Column(String(20), nullable=True)    # 'iniciada', 'pendiente', 'recolectando_datos', 'cerrada', 'cancelada'
    tipo_mensaje = Column(String(20), nullable=True)    # 'inventario', 'venta', 'contexto'
    metadatos = Column(JSON, nullable=True)             # Extras: productos, cantidades, datos_cliente, etc.

    # Para multiempresa: descomentar y migrar cuando estés listo
    # empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    # empresa = relationship("Empresa", back_populates="mensajes")

    def __repr__(self):
        return (
            f"<Mensaje(chat_id={self.chat_id}, remitente={self.remitente}, "
            f"mensaje='{self.mensaje[:40]}', estado_venta={self.estado_venta}, tipo_mensaje={self.tipo_mensaje})>"
        )
