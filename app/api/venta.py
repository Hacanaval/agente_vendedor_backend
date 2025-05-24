from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.models.venta import Venta
from app.models.producto import Producto
from app.schemas.venta import VentaCreate, VentaOut
from app.services.logs import registrar_log
from typing import List
import logging
from app.models.mensaje import Mensaje

router = APIRouter(
    prefix="/ventas",
    tags=["ventas"]
)

@router.post("/", response_model=VentaOut)
async def crear_venta(
    data: VentaCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # TODO: Volver a proteger con autenticación y multiempresa en producción
    try:
        # 1. Validar que el producto exista y pertenezca a la empresa
        result = await db.execute(select(Producto).where(
            Producto.id == data.producto_id,
            Producto.empresa_id == 1  # TODO: Volver a usar empresa_id dinámico en multiempresa
        ))
        producto = result.scalar_one_or_none()
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if producto.stock < data.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")

        # 2. Descontar stock
        producto.stock -= data.cantidad
        await db.flush()

        # 3. Registrar venta
        body = await request.json()
        chat_id = body.get("chat_id") if isinstance(body, dict) else None
        venta = Venta(
            empresa_id=1,  # TODO: Volver a usar empresa_id dinámico en multiempresa
            producto_id=producto.id,
            usuario_id=None,  # Fijo en None para modo sin usuarios
            cantidad=data.cantidad,
            total=producto.precio * data.cantidad,
            chat_id=chat_id
        )
        db.add(venta)
        await db.flush()
        await db.refresh(venta)

        # 4. Registrar log
        # TODO: Volver a registrar logs con usuario_id y empresa_id en multiempresa
        await db.commit()
        return venta
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error al crear venta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear la venta")

@router.get("/", response_model=List[VentaOut])
async def listar_ventas(db: AsyncSession = Depends(get_db)):
    # TODO: Volver a filtrar por empresa_id y proteger con autenticación en producción
    result = await db.execute(
        select(Venta)
        .where(Venta.empresa_id == 1)
    )
    ventas = result.scalars().all()
    return ventas

@router.get("/{venta_id}", response_model=VentaOut)
async def obtener_venta(
    venta_id: int,
    db: AsyncSession = Depends(get_db)
):
    # TODO: Volver a filtrar por empresa_id y proteger con autenticación en producción
    result = await db.execute(
        select(Venta)
        .where(
            Venta.id == venta_id,
            Venta.empresa_id == 1
        )
    )
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta

@router.get("/historial/{chat_id}", summary="Historial de ventas de un chat", response_model=List[dict])
async def historial_ventas_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    """
    Devuelve el historial de ventas asociadas a un chat_id (usuario/cliente), ordenadas por fecha descendente.
    """
    # TODO: Filtrar por empresa_id en multiempresa
    result = await db.execute(
        select(Venta).where(Venta.chat_id == chat_id).order_by(Venta.fecha.desc())
    )
    ventas = result.scalars().all()
    return [
        {
            "id": v.id,
            "chat_id": v.chat_id,
            "productos": v.productos,  # Asume que productos es un campo serializable
            "total": v.total,
            "fecha": v.fecha.isoformat()
        }
        for v in ventas
    ]

# (Opcional: agrega aquí endpoint de actualizar/eliminar venta si lo necesitas en el futuro)
