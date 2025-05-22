from pydantic import BaseModel

class VentaCreate(BaseModel):
    producto_id: int
    cantidad: int

class VentaOut(BaseModel):
    id: int
    empresa_id: int
    producto_id: int
    usuario_id: int
    cantidad: int
    total: float

    class Config:
        orm_mode = True
