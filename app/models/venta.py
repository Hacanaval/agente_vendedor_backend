from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.core.database import Base

class Venta(Base):
    __tablename__ = "venta"
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    estado = Column(String(50), nullable=True)
    detalle = Column(JSON, nullable=True)
    chat_id = Column(String, index=True, nullable=True)
    # TODO: Reagregar empresa_id y relaciones en modo multiempresa
