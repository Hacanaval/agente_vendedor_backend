from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Venta(Base):
    __tablename__ = "venta"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cantidad = Column(Integer, nullable=False)
    total = Column(Float, nullable=False)
    estado = Column(String(50), nullable=True)   # Opcional, puedes ajustar a False si siempre tiene valor
    detalle = Column(JSON, nullable=True)         # Opcional, puedes ajustar a False si siempre tiene valor
    chat_id = Column(String, index=True, nullable=True)  # Nuevo campo para asociar venta a chat/usuario
    # TODO: multiempresa y autenticación

    empresa = relationship("Empresa", backref="ventas")
    usuario = relationship("Usuario", backref="ventas")
    producto = relationship("Producto", backref="ventas")
