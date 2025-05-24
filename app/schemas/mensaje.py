from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MensajeOut(BaseModel):
    id: int
    chat_id: str
    remitente: str
    mensaje: str
    timestamp: datetime
    estado_venta: Optional[str] = None
    # TODO: Reagregar empresa_id y usuario_id en modo multiempresa

    class Config:
        orm_mode = True 