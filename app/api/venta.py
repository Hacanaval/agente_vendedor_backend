from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.models.venta import Venta
from app.models.producto import Producto
from app.schemas.venta import VentaCreate, VentaOut
from app.api.auth import get_current_user
from app.models.usuario import Usuario
from app.services.logs import registrar_log
from typing import List

router = APIRouter(
    prefix="/ventas",
    tags=["ventas"]
)

@router.post("/", response_model=VentaOut)
async def crear_venta(
    data: VentaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # 1. Validar que el producto exista y pertenezca a la empresa
    result = await db.execute(select(Producto).where(
        Producto.id == data.producto_id,
        Producto.empresa_id == usuario.empresa_id
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
    venta = Venta(
        empresa_id=usuario.empresa_id,
        producto_id=producto.id,
        usuario_id=usuario.id,
        cantidad=data.cantidad,
        total=producto.precio * data.cantidad
    )
    db.add(venta)
    await db.flush()
    await db.refresh(venta)

    # 4. Registrar log
    await registrar_log(
        db=db,
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        modelo="venta",
        accion="vendido",
        detalle={"venta": {
            "id": venta.id,
            "producto_id": venta.producto_id,
            "usuario_id": venta.usuario_id,
            "cantidad": venta.cantidad,
            "total": venta.total
        }}
    )
    await db.commit()
    return venta

@router.get("/", response_model=List[VentaOut])
async def listar_ventas(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(Venta)
        .where(Venta.empresa_id == usuario.empresa_id)
        .options(joinedload(Venta.producto))
    )
    ventas = result.scalars().all()
    return ventas

@router.get("/{venta_id}", response_model=VentaOut)
async def obtener_venta(
    venta_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(Venta)
        .where(
            Venta.id == venta_id,
            Venta.empresa_id == usuario.empresa_id
        )
        .options(joinedload(Venta.producto))
    )
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta

# (Opcional: agrega aquí endpoint de actualizar/eliminar venta si lo necesitas en el futuro)
