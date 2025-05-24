from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Mensaje(Base):
    __tablename__ = "mensaje"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    cliente_final_id = Column(Integer, ForeignKey("cliente_final.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)
    session_id = Column(String(100), nullable=False)
    telefono = Column(String(50), nullable=False)
    message_role = Column(String(10), nullable=False)  # 'user' o 'agent'
    message = Column(String(2000), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'text', 'audio', 'image'
    media_url = Column(String(255), nullable=True)
    categoria = Column(String(100), nullable=True)
    tags = Column(String(255), nullable=True)  # separado por comas
    vector_id = Column(String(100), nullable=True)
    chat_id = Column(String, index=True, nullable=False)
    remitente = Column(String, nullable=False)  # 'usuario' o 'bot'
    timestamp = Column(DateTime, default=datetime.utcnow)
    estado_venta = Column(String(20), nullable=True)  # 'pendiente', 'confirmada', 'cerrada', etc.

    empresa = relationship("Empresa", backref="mensajes")
    cliente_final = relationship("ClienteFinal", backref="mensajes")
    usuario = relationship("Usuario", backref="mensajes") 