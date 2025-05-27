from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.producto import Producto
from app.schemas.producto import ProductoCreate, ProductoOut
from typing import List
import pandas as pd
import io
import logging
from app.services.retrieval.retriever_factory import get_retriever

router = APIRouter(prefix="/productos", tags=["productos"])

@router.post("/", response_model=ProductoOut)
async def create_producto(producto: ProductoCreate, db: AsyncSession = Depends(get_db)):
    db_producto = Producto(**producto.dict())
    db.add(db_producto)
    await db.commit()
    await db.refresh(db_producto)
    return db_producto

@router.get("/", response_model=List[ProductoOut])
async def list_productos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Producto))
    productos = result.scalars().all()
    return productos

@router.post("/reemplazar_csv", summary="Reemplaza el inventario de productos a partir de un CSV")
async def reemplazar_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Reemplaza el inventario de productos usando un archivo CSV.
    - Si el nombre existe, actualiza stock y precio.
    - Si el nombre NO existe, lo crea.
    - Si el nombre está en DB y NO viene en el CSV, su stock se actualiza a 0.
    - No afecta el histórico de ventas.
    - El CSV debe tener columnas: nombre, descripcion, precio, stock
    """
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        # Validar columnas mínimas requeridas
        required_cols = {"nombre", "descripcion", "precio", "stock"}
        if not required_cols.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"El CSV debe tener las columnas: {', '.join(required_cols)}")

        # 1. Obtener todos los productos actuales en la DB
        result = await db.execute(select(Producto))
        productos_db = result.scalars().all()
        nombres_db = {p.nombre: p for p in productos_db}

        nombres_csv = set(df["nombre"])

        # 2. Actualizar/crear productos desde el CSV
        for _, row in df.iterrows():
            nombre = row["nombre"]
            if nombre in nombres_db:
                # Actualiza stock y precio
                producto = nombres_db[nombre]
                producto.descripcion = row["descripcion"]
                producto.precio = float(row["precio"])
                producto.stock = int(row["stock"])
                producto.activo = producto.stock > 0
            else:
                # Crea nuevo producto
                producto = Producto(
                    nombre=row["nombre"],
                    descripcion=row["descripcion"],
                    precio=float(row["precio"]),
                    stock=int(row["stock"]),
                    activo=int(row["stock"]) > 0
                )
                db.add(producto)

        # 3. Poner stock=0 a los productos que no vienen en el CSV
        nombres_no_csv = set(nombres_db.keys()) - nombres_csv
        for nombre in nombres_no_csv:
            producto = nombres_db[nombre]
            producto.stock = 0
            producto.activo = False

        await db.commit()

        # 4. Reconstruir el índice FAISS
        retriever = get_retriever(db)
        await retriever.sync_with_db()

        return {"message": "Inventario reemplazado correctamente."}
    except Exception as e:
        logging.error(f"Error en /productos/reemplazar_csv: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al reemplazar el inventario desde el CSV")
