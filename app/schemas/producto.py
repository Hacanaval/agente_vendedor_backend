from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: int
    stock: int
    activo: Optional[bool] = True

class ProductoCreate(ProductoBase):
    pass

class ProductoOut(ProductoBase):
    id: int
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True