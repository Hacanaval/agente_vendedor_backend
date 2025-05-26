from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductoBase(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    stock: int
    categoria: Optional[str] = None
    activo: Optional[bool] = True
    # TODO: Reagregar empresa_id en modo multiempresa

class ProductoCreate(ProductoBase):
    pass

class ProductoOut(ProductoBase):
    id: int
    creado_en: Optional[datetime]
    actualizado_en: Optional[datetime]
    # TODO: Reagregar empresa_id en modo multiempresa

    class Config:
        from_attributes = True