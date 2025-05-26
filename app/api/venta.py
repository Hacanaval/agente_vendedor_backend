from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    db: AsyncSession = Depends(get_db),
    request: Request = None  # solo si necesitas el chat_id del body (opcional)
):
    """
    Crea una venta: valida stock, descuenta producto y registra la venta.
    """
    try:
        # 1. Validar producto y stock
        result = await db.execute(select(Producto).where(Producto.id == data.producto_id))
        producto = result.scalar_one_or_none()
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        if producto.stock < data.cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")

        # 2. Descontar stock
        producto.stock -= data.cantidad
        await db.flush()

        # 3. Obtener chat_id si es relevante (pasa por el modelo o body)
        chat_id = getattr(data, "chat_id", None)
        if not chat_id and request:
            body = await request.json()
            chat_id = body.get("chat_id")

        # 4. Crear y registrar la venta
        venta = Venta(
            producto_id=producto.id,
            cantidad=data.cantidad,
            total=producto.precio * data.cantidad,
            chat_id=chat_id
            # empresa_id=... # para multiempresa en el futuro
        )
        db.add(venta)
        await db.flush()
        await db.refresh(venta)
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
    result = await db.execute(select(Venta))
    return result.scalars().all()

@router.get("/{venta_id}", response_model=VentaOut)
async def obtener_venta(
    venta_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Venta).where(Venta.id == venta_id))
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta

@router.get("/historial/{chat_id}", summary="Historial de ventas de un chat", response_model=List[dict])
async def historial_ventas_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Venta).where(Venta.chat_id == chat_id).order_by(Venta.fecha.desc())
    )
    ventas = result.scalars().all()
    return [
        {
            "id": v.id,
            "chat_id": v.chat_id,
            "producto_id": getattr(v, "producto_id", None),
            "cantidad": getattr(v, "cantidad", None),
            "total": v.total,
            "fecha": v.fecha.isoformat()
        }
        for v in ventas
    ]
