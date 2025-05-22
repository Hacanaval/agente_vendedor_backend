from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductoCreate(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    stock: int
    categoria: Optional[str] = None
    activo: Optional[bool] = True

class ProductoOut(BaseModel):
    id: int
    nombre: str
    descripcion: str
    precio: float
    stock: int
    categoria: Optional[str]
    activo: bool
    empresa_id: int
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True  # Para Pydantic v2