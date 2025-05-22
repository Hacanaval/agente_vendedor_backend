from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.logs import Logs
from app.api.auth import get_current_user
from app.models.usuario import Usuario  # Ajuste para consistencia de tipo
from typing import List, Optional

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/", response_model=List[dict])
async def listar_logs(
    modelo: Optional[str] = Query(None),
    usuario_id: Optional[int] = Query(None),
    accion: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)  # Mejor usar modelo que schema
):
    query = select(Logs).where(Logs.empresa_id == current_user.empresa_id)
    if modelo:
        query = query.where(Logs.modelo == modelo)
    if usuario_id:
        query = query.where(Logs.usuario_id == usuario_id)
    if accion:
        query = query.where(Logs.accion == accion)
    # Opcional: limitar número de logs devueltos para evitar respuestas gigantes
    # query = query.limit(100)
    result = await db.execute(query.order_by(Logs.fecha.desc()))
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "empresa_id": log.empresa_id,
            "usuario_id": log.usuario_id,
            "modelo": log.modelo,
            "accion": log.accion,
            "detalle": log.detalle,
            "fecha": log.fecha
        }
        for log in logs
    ]
