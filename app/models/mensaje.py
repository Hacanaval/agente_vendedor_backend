from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

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
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    empresa = relationship("Empresa", backref="mensajes")
    cliente_final = relationship("ClienteFinal", backref="mensajes")
    usuario = relationship("Usuario", backref="mensajes") 