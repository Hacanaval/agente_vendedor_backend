from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ClienteFinal(Base):
    __tablename__ = "cliente_final"
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    telefono = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    identificacion = Column(String(100), nullable=True)
    fecha_nacimiento = Column(DateTime(timezone=True), nullable=True)
    notas = Column(String(500), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    empresa = relationship("Empresa", backref="clientes_finales") 