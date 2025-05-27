from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.base_class import Base

class Venta(Base):
    """
    Modelo de Venta con relación a Cliente y Producto.
    
    Registra cada venta individual con información completa del cliente,
    producto vendido y detalles de la transacción.
    """
    __tablename__ = "ventas"
    
    id = Column(Integer, primary_key=True, index=True, comment="ID único de la venta")
    producto_id = Column(Integer, nullable=False, index=True, comment="ID del producto vendido")
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Fecha y hora de la venta")
    cantidad = Column(Integer, nullable=False, comment="Cantidad vendida")
    total = Column(Float, nullable=False, comment="Valor total de la venta")
    estado = Column(String(50), nullable=True, comment="Estado de la venta (completada, pendiente, etc.)")
    detalle = Column(JSON, nullable=True, comment="Detalles adicionales de la venta")
    chat_id = Column(String, index=True, nullable=True, comment="ID del chat donde se realizó la venta")
    
    # Relación con Cliente (usando cédula como FK)
    cliente_cedula = Column(String(20), ForeignKey("clientes.cedula"), nullable=True, index=True, comment="Cédula del cliente")
    
    # Relaciones
    cliente = relationship("Cliente", back_populates="ventas")
    
    def __repr__(self):
        return f"<Venta(id={self.id}, cliente='{self.cliente_cedula}', producto_id={self.producto_id}, total={self.total})>"
    
    def to_dict(self):
        """Convierte la venta a diccionario para APIs"""
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "cantidad": self.cantidad,
            "total": self.total,
            "estado": self.estado,
            "detalle": self.detalle,
            "chat_id": self.chat_id,
            "cliente_cedula": self.cliente_cedula
        }
