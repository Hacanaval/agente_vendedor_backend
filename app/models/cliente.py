from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from app.core.base_class import Base
from datetime import datetime

class Cliente(Base):
    """
    Modelo de Cliente para gestión de información y historial de compras.
    
    Usa la cédula como identificador principal único.
    Almacena información completa del cliente y se relaciona con las ventas.
    """
    __tablename__ = "clientes"
    
    # Cédula como ID principal
    cedula = Column(String(20), primary_key=True, index=True, comment="Cédula del cliente (ID principal)")
    
    # Información personal
    nombre_completo = Column(String(200), nullable=False, comment="Nombre completo del cliente")
    telefono = Column(String(20), nullable=False, index=True, comment="Teléfono de contacto")
    correo = Column(String(200), nullable=True, index=True, comment="Correo electrónico del cliente")
    
    # Información de dirección
    direccion = Column(Text, nullable=False, comment="Dirección completa de entrega")
    barrio = Column(String(100), nullable=False, comment="Barrio de residencia")
    indicaciones_adicionales = Column(Text, nullable=True, comment="Indicaciones adicionales para entrega")
    
    # Metadatos del cliente
    fecha_registro = Column(DateTime, default=datetime.now, comment="Fecha de primer registro")
    fecha_ultima_compra = Column(DateTime, nullable=True, comment="Fecha de la última compra")
    total_compras = Column(Integer, default=0, comment="Número total de compras realizadas")
    valor_total_compras = Column(Integer, default=0, comment="Valor total acumulado de todas las compras")
    
    # Estado del cliente
    activo = Column(Boolean, default=True, comment="Cliente activo en el sistema")
    
    # Información adicional
    notas = Column(Text, nullable=True, comment="Notas adicionales sobre el cliente")
    
    # Relaciones
    ventas = relationship("Venta", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cliente(cedula='{self.cedula}', nombre='{self.nombre_completo}', compras={self.total_compras})>"
    
    def to_dict(self):
        """Convierte el cliente a diccionario para APIs"""
        return {
            "cedula": self.cedula,
            "nombre_completo": self.nombre_completo,
            "telefono": self.telefono,
            "correo": self.correo,
            "direccion": self.direccion,
            "barrio": self.barrio,
            "indicaciones_adicionales": self.indicaciones_adicionales,
            "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None,
            "fecha_ultima_compra": self.fecha_ultima_compra.isoformat() if self.fecha_ultima_compra else None,
            "total_compras": self.total_compras,
            "valor_total_compras": self.valor_total_compras,
            "activo": self.activo,
            "notas": self.notas
        }
    
    @classmethod
    def from_datos_pedido(cls, datos_cliente: dict, cedula: str):
        """Crea un cliente a partir de los datos recolectados en un pedido"""
        return cls(
            cedula=cedula,
            nombre_completo=datos_cliente.get("nombre_completo", ""),
            telefono=datos_cliente.get("telefono", ""),
            correo=datos_cliente.get("correo", ""),
            direccion=datos_cliente.get("direccion", ""),
            barrio=datos_cliente.get("barrio", ""),
            indicaciones_adicionales=datos_cliente.get("indicaciones_adicionales", ""),
            fecha_registro=datetime.now(),
            activo=True
        ) 