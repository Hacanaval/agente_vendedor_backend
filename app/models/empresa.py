from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresa"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(1000), nullable=True)
    # TODO: Restaurar relaciones multiempresa en producción 