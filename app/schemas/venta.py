from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

# ✅ Schema para producto individual en venta
class ProductoVenta(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: float

# ✅ Schema mejorado para crear ventas (compatible con frontend)
class VentaCreate(BaseModel):
    chat_id: str
    productos: List[ProductoVenta]
    total: float
    cliente_cedula: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    
    @validator('productos')
    def validar_productos(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Debe incluir al menos un producto')
        return v
    
    @validator('total')
    def validar_total(cls, v):
        if v <= 0:
            raise ValueError('El total debe ser mayor a 0')
        return v

# ✅ Schema legacy para compatibilidad con código existente
class VentaCreateSimple(BaseModel):
    producto_id: int
    cantidad: int
    chat_id: Optional[str] = None
    # TODO: Reagregar empresa_id y usuario_id en modo multiempresa

class VentaOut(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    total: float
    chat_id: Optional[str]
    fecha: Optional[datetime]
    # TODO: Reagregar empresa_id y usuario_id en modo multiempresa

    class Config:
        from_attributes = True
