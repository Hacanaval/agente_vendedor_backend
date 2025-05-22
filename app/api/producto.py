from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.producto import Producto
from app.api.auth import get_current_user
from app.models.usuario import Usuario
from app.schemas.producto import ProductoCreate, ProductoOut
from typing import List
from app.services.producto_csv import parse_csv_productos
from app.services.logs import registrar_log
import logging

router = APIRouter(prefix="/productos", tags=["productos"])

MAX_CSV_SIZE_MB = 2  # Máximo 2MB por archivo
MAX_PRODUCTOS_CSV = 1000  # Máximo 1000 productos por carga

# Listar productos
@router.get("/", response_model=List[ProductoOut])
async def listar_productos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        result = await db.execute(
            select(Producto).where(Producto.empresa_id == current_user.empresa_id)
        )
        return result.scalars().all()
    except Exception as e:
        logging.error(f"Error al listar productos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al listar productos")

# Reemplazar inventario por CSV (borra todos y agrega los del CSV)
@router.post("/reemplazar_csv", response_model=List[ProductoOut])
async def reemplazar_inventario_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Validar extensión y tamaño de archivo
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")
    file.file.seek(0, 2)
    size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    if size_mb > MAX_CSV_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"El archivo CSV supera el tamaño máximo permitido de {MAX_CSV_SIZE_MB}MB")
    try:
        productos_data = parse_csv_productos(file.file)
    except Exception as e:
        logging.error(f"Error al procesar el CSV: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al procesar el CSV: {str(e)}")
    if not productos_data:
        raise HTTPException(status_code=400, detail="El archivo CSV no contiene productos válidos")
    if len(productos_data) > MAX_PRODUCTOS_CSV:
        raise HTTPException(status_code=400, detail=f"El archivo CSV contiene más de {MAX_PRODUCTOS_CSV} productos")
    try:
        async with db.begin():
            # Traer productos actuales de la empresa
            result = await db.execute(
                select(Producto).where(Producto.empresa_id == current_user.empresa_id)
            )
            productos_actuales = result.scalars().all()
            productos_actuales_dict = {p.nombre: p for p in productos_actuales}
            productos_actualizados = []
            productos_nuevos = []
            productos_stock_cero = []
            nombres_en_csv = set()
            for data in productos_data:
                nombre = data["nombre"]
                nombres_en_csv.add(nombre)
                if nombre in productos_actuales_dict:
                    producto = productos_actuales_dict[nombre]
                    producto.descripcion = data["descripcion"]
                    producto.precio = data["precio"]
                    producto.stock = data["stock"]
                    producto.activo = True
                    productos_actualizados.append(producto)
                else:
                    producto = Producto(
                        empresa_id=current_user.empresa_id,
                        nombre=data["nombre"],
                        descripcion=data["descripcion"],
                        precio=data["precio"],
                        stock=data["stock"],
                        activo=True
                    )
                    db.add(producto)
                    productos_nuevos.append(producto)
            # Los productos no incluidos en el CSV se dejan en stock 0 e inactivos
            for producto in productos_actuales:
                if producto.nombre not in nombres_en_csv:
                    producto.stock = 0
                    producto.activo = False
                    productos_stock_cero.append(producto)
            await db.flush()
            # Refrescar para logs
            todos = productos_actualizados + productos_nuevos + productos_stock_cero
            for p in todos:
                await db.refresh(p)
            productos_creados_dict = [ProductoOut.model_validate(p).model_dump() for p in productos_nuevos]
            productos_actualizados_dict = [ProductoOut.model_validate(p).model_dump() for p in productos_actualizados]
            productos_stock_cero_dict = [ProductoOut.model_validate(p).model_dump() for p in productos_stock_cero]
            await registrar_log(
                db=db,
                empresa_id=current_user.empresa_id,
                usuario_id=current_user.id,
                modelo="producto",
                accion="reemplazo_inventario",
                detalle={
                    "productos_creados": productos_creados_dict,
                    "productos_actualizados": productos_actualizados_dict,
                    "productos_stock_cero": productos_stock_cero_dict
                }
            )
        # Solo devolvemos los productos vigentes (stock > 0 y activos)
        result = await db.execute(
            select(Producto).where(
                Producto.empresa_id == current_user.empresa_id,
                Producto.stock > 0,
                Producto.activo == True
            )
        )
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error en reemplazo_csv: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en la operación de reemplazo de inventario")
