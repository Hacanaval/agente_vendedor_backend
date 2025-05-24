from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VentaCreate(BaseModel):
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
        orm_mode = True
