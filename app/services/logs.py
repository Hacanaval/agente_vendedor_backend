from app.models.logs import Logs
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, Dict, Any

def serialize_for_log(obj: Any):
    """
    Recursivamente convierte todos los datetime a string isoformat en un dict o lista,
    para que el campo detalle sea siempre serializable como JSON.
    """
    if isinstance(obj, dict):
        return {k: serialize_for_log(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_log(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

async def registrar_log(
    db: AsyncSession,
    empresa_id: int,
    usuario_id: int,
    modelo: str,
    accion: str,
    detalle: Dict
):
    """
    Registra un log/auditoría en la tabla logs.
    Serializa cualquier datetime dentro de 'detalle' a string ISO8601.
    El commit NO se realiza aquí (debe hacerse en el flujo principal).
    """
    detalle_serializado = serialize_for_log(detalle)
    log = Logs(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        modelo=modelo,
        accion=accion,
        detalle=detalle_serializado,
        fecha=datetime.utcnow()
    )
    db.add(log)
    # No commit aquí, se hace en el flujo principal para eficiencia 
