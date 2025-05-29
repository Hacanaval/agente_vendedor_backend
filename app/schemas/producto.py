from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProductoBase(BaseModel):
    nombre: str = Field(..., description="Nombre del producto", max_length=100)
    descripcion: str = Field(..., description="Descripción del producto", max_length=500)
    precio: float = Field(..., description="Precio del producto", gt=0)
    stock: int = Field(..., description="Cantidad en stock", ge=0)
    categoria: str = Field(..., description="Categoría del producto", max_length=50)
    activo: Optional[bool] = True

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    precio: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    categoria: Optional[str] = Field(None, max_length=50)

class ProductoOut(ProductoBase):
    id: int
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True