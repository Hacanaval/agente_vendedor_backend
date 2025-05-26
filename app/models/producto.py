from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Producto(Base):
    __tablename__ = "producto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(1000), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    categoria = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Preparado para multiempresa:
    # empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    # empresa = relationship("Empresa", back_populates="productos")

    def __repr__(self):
        return (
            f"<Producto(id={self.id}, nombre={self.nombre}, precio={self.precio}, "
            f"stock={self.stock}, activo={self.activo})>"
        )
