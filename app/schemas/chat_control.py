from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatControlBase(BaseModel):
    chat_id: Optional[str] = None
    ia_activa: bool
    tipo_control: str  # "global" o "conversacion"
    motivo_desactivacion: Optional[str] = None
    usuario_que_desactivo: Optional[str] = None

class ChatControlCreate(ChatControlBase):
    pass

class ChatControlUpdate(BaseModel):
    ia_activa: bool
    motivo_desactivacion: Optional[str] = None
    usuario_que_desactivo: Optional[str] = None

class ChatControlOut(ChatControlBase):
    id: int
    fecha_cambio: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True

# Esquemas específicos para respuestas de endpoints
class ControlGlobalResponse(BaseModel):
    sistema_ia_activo: bool
    mensaje: str
    fecha_cambio: Optional[datetime] = None
    usuario_que_desactivo: Optional[str] = None

class ControlConversacionResponse(BaseModel):
    chat_id: str
    ia_conversacion_activa: bool
    mensaje: str
    fecha_cambio: Optional[datetime] = None
    usuario_que_desactivo: Optional[str] = None

class EstadoSistemaResponse(BaseModel):
    sistema_ia_activo: bool
    conversaciones_desactivadas: int
    total_conversaciones_monitoreadas: int 