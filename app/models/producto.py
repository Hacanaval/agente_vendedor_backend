from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.base_class import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(String(1000), nullable=True)
    precio = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    categoria = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_actualizacion = Column(DateTime, server_default=func.now(), nullable=True)

    # Preparado para multiempresa:
    # empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    # empresa = relationship("Empresa", back_populates="productos")

    def __repr__(self):
        return (
            f"<Producto(id={self.id}, nombre={self.nombre}, precio={self.precio}, "
            f"stock={self.stock}, categoria={self.categoria}, activo={self.activo})>"
        )
