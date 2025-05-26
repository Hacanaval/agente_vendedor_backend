from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.core.database import Base

class InventarioLog(Base):
    __tablename__ = "inventario_log"
    id = Column(Integer, primary_key=True, index=True)
    cambio = Column(Integer, nullable=False)
    motivo = Column(String(255), nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # TODO: Reagregar empresa_id, producto_id, usuario_id y relaciones en modo multiempresa 