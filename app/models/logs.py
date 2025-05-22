from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Logs(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    modelo = Column(String(50), nullable=False)
    accion = Column(String(50), nullable=False)
    detalle = Column(JSON, nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    empresa = relationship("Empresa", backref="logs")
    usuario = relationship("Usuario", backref="logs") 