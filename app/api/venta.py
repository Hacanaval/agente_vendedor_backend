from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.venta import Venta
from app.models.producto import Producto
from app.schemas.venta import VentaCreate, VentaOut, VentaCreateSimple
from app.services.logs import registrar_log
from typing import List, Optional
import logging
from app.models.mensaje import Mensaje
from pydantic import BaseModel

router = APIRouter(
    prefix="/venta",
    tags=["venta"]
)

class VentaUpdate(BaseModel):
    estado: Optional[str] = None
    cliente_cedula: Optional[str] = None
    detalle: Optional[dict] = None

@router.post("/", response_model=dict)
async def crear_venta(
    data: VentaCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ CORREGIDO: Crea ventas múltiples con validación robusta (compatible con frontend)
    """
    try:
        ventas_creadas = []
        total_general = 0
        
        # Validar que todos los productos existan y tengan stock
        for item in data.productos:
            result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
            producto = result.scalar_one_or_none()
            
            if not producto:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Producto con ID {item.producto_id} no encontrado"
                )
            
            if producto.stock < item.cantidad:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuficiente para {producto.nombre}. Stock disponible: {producto.stock}, solicitado: {item.cantidad}"
                )
        
        # Crear ventas individuales para cada producto
        for item in data.productos:
            result = await db.execute(select(Producto).where(Producto.id == item.producto_id))
            producto = result.scalar_one_or_none()
            
            # Calcular total del item
            total_item = producto.precio * item.cantidad
            
            # Crear venta individual
            venta = Venta(
                producto_id=producto.id,
                cantidad=item.cantidad,
                total=total_item,
                chat_id=data.chat_id,
                estado="completada",
                cliente_cedula=data.cliente_cedula,
                detalle={
                    "producto_nombre": producto.nombre,
                    "precio_unitario": producto.precio,
                    "datos_cliente": {
                        "nombre_completo": data.cliente_nombre,
                        "telefono": data.cliente_telefono,
                        "cedula": data.cliente_cedula
                    } if data.cliente_nombre else None
                }
            )
            
            # Descontar stock
            producto.stock -= item.cantidad
            
            db.add(venta)
            await db.flush()
            await db.refresh(venta)
            
            total_general += total_item
            
            ventas_creadas.append({
                "venta_id": venta.id,
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "cantidad": item.cantidad,
                "precio_unitario": producto.precio,
                "total": total_item
            })
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Venta creada exitosamente. {len(ventas_creadas)} productos vendidos.",
            "ventas_creadas": ventas_creadas,
            "total_general": total_general,
            "chat_id": data.chat_id,
            "cliente": {
                "cedula": data.cliente_cedula,
                "nombre": data.cliente_nombre,
                "telefono": data.cliente_telefono
            } if data.cliente_cedula else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error al crear venta: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al crear la venta: {str(e)}"
        )

# ✅ Endpoint legacy para compatibilidad 
@router.post("/simple", response_model=VentaOut)
async def crear_venta_simple(
    data: VentaCreateSimple,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una venta simple: valida stock, descuenta producto y registra la venta.
    (Endpoint legacy para compatibilidad)
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

        # 3. Crear y registrar la venta
        venta = Venta(
            producto_id=producto.id,
            cantidad=data.cantidad,
            total=producto.precio * data.cantidad,
            chat_id=data.chat_id,
            estado="completado",
            detalle={
                "producto_nombre": producto.nombre,
                "precio_unitario": producto.precio
            }
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
        logging.error(f"Error al crear venta simple: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear la venta")

@router.get("/", response_model=List[VentaOut])
async def listar_ventas(db: AsyncSession = Depends(get_db)):
    """Lista todas las ventas"""
    result = await db.execute(select(Venta).order_by(Venta.fecha.desc()))
    return result.scalars().all()

@router.get("/{venta_id}", response_model=VentaOut)
async def obtener_venta(
    venta_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una venta específica por ID"""
    result = await db.execute(select(Venta).where(Venta.id == venta_id))
    venta = result.scalar_one_or_none()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta

@router.put("/{venta_id}", response_model=VentaOut)
async def actualizar_venta(
    venta_id: int,
    data: VentaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza una venta existente"""
    try:
        result = await db.execute(select(Venta).where(Venta.id == venta_id))
        venta = result.scalar_one_or_none()
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        # Actualizar campos permitidos
        if data.estado is not None:
            venta.estado = data.estado
        if data.cliente_cedula is not None:
            venta.cliente_cedula = data.cliente_cedula
        if data.detalle is not None:
            venta.detalle = data.detalle
            
        await db.commit()
        await db.refresh(venta)
        return venta
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error al actualizar venta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al actualizar la venta")

@router.get("/historial/{chat_id}", response_model=List[dict])
async def historial_ventas_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    """Historial de ventas de un chat específico"""
    result = await db.execute(
        select(Venta).where(Venta.chat_id == chat_id).order_by(Venta.fecha.desc())
    )
    ventas = result.scalars().all()
    return [
        {
            "id": v.id,
            "chat_id": v.chat_id,
            "producto_id": v.producto_id,
            "cantidad": v.cantidad,
            "total": v.total,
            "estado": v.estado,
            "fecha": v.fecha.isoformat() if v.fecha else None,
            "cliente_cedula": v.cliente_cedula,
            "detalle": v.detalle
        }
        for v in ventas
    ]

@router.put("/estado/{chat_id}")
async def cambiar_estado_venta(
    chat_id: str,
    estado: str,
    db: AsyncSession = Depends(get_db)
):
    """Cambia el estado de todas las ventas de un chat"""
    try:
        result = await db.execute(select(Venta).where(Venta.chat_id == chat_id))
        ventas = result.scalars().all()
        
        if not ventas:
            raise HTTPException(status_code=404, detail="No se encontraron ventas para este chat")
        
        for venta in ventas:
            venta.estado = estado
            
        await db.commit()
        
        return {
            "message": f"Estado actualizado a '{estado}' para {len(ventas)} ventas",
            "chat_id": chat_id,
            "estado": estado,
            "ventas_actualizadas": len(ventas)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error al cambiar estado de ventas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al cambiar estado")
