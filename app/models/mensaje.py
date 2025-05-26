from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.core.database import Base

class Mensaje(Base):
    __tablename__ = "mensaje"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    remitente = Column(String, nullable=False)  # 'usuario' o 'bot'
    mensaje = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    estado_venta = Column(String(20), nullable=True)  # 'pendiente', 'confirmada', 'cerrada', etc.
    # TODO: Reagregar empresa_id y relaciones en modo multiempresa 