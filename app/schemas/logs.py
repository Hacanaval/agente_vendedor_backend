from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LogOut(BaseModel):
    id: int
    modelo: str
    accion: str
    detalle: dict
    fecha: datetime
    # TODO: Reagregar empresa_id y usuario_id en modo multiempresa

    class Config:
        orm_mode = True 