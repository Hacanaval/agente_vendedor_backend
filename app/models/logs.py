from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.core.database import Base

class Logs(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(50), nullable=False)
    accion = Column(String(50), nullable=False)
    detalle = Column(JSON, nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # TODO: Reagregar empresa_id y relaciones en modo multiempresa 