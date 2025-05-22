from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class InventarioLog(Base):
    __tablename__ = "inventario_log"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    cambio = Column(Integer, nullable=False)
    motivo = Column(String(255), nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    empresa = relationship("Empresa", backref="inventario_logs")
    producto = relationship("Producto", backref="inventario_logs")
    usuario = relationship("Usuario", backref="inventario_logs") 