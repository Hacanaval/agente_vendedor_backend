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
    """
    ✅ CORREGIDO: Crea un nuevo producto con manejo inteligente de duplicados
    """
    try:
        # ✅ CORREGIDO: Usar model_dump() para Pydantic v2 en lugar de dict()
        producto_data = producto.model_dump()
        
        # Verificar si ya existe un producto con ese nombre
        result = await db.execute(
            select(Producto).where(Producto.nombre == producto.nombre)
        )
        existing_producto = result.scalar_one_or_none()
        
        if existing_producto:
            # ✅ OPCIÓN A: Actualizar producto existente (RECOMENDADO PARA TESTING)
            existing_producto.descripcion = producto_data["descripcion"]
            existing_producto.precio = float(producto_data["precio"])
            existing_producto.stock = int(producto_data["stock"])
            existing_producto.categoria = producto_data["categoria"]
            existing_producto.activo = True
            
            await db.commit()
            await db.refresh(existing_producto)
            
            logging.info(f"Producto actualizado: {existing_producto.nombre}")
            return existing_producto
            
            # ✅ OPCIÓN B: Generar nombre único (comentado - descomentar si prefieres)
            # import time
            # producto_data["nombre"] = f"{producto.nombre} ({int(time.time())})"
        
        # Crear nuevo producto si no existe
        db_producto = Producto(
            nombre=producto_data["nombre"],
            descripcion=producto_data["descripcion"],
            precio=float(producto_data["precio"]),  # Asegurar que sea float
            stock=int(producto_data["stock"]),      # Asegurar que sea int
            categoria=producto_data["categoria"],
            activo=True  # Por defecto activo
        )
        
        db.add(db_producto)
        await db.commit()
        await db.refresh(db_producto)
        
        logging.info(f"Producto creado: {db_producto.nombre}")
        return db_producto
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error creando producto: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al crear el producto: {str(e)}"
        )

@router.get("/", response_model=List[ProductoOut])
async def list_productos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Producto))
    productos = result.scalars().all()
    return productos

@router.get("/{producto_id}", response_model=ProductoOut)
async def obtener_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene un producto específico por ID"""
    try:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        producto = result.scalar_one_or_none()
        
        if not producto:
            raise HTTPException(
                status_code=404, 
                detail=f"Producto con ID {producto_id} no encontrado"
            )
        
        return producto
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo producto {producto_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al obtener el producto: {str(e)}"
        )

@router.post("/reemplazar_csv", summary="Reemplaza el inventario de productos a partir de un CSV")
async def reemplazar_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Reemplaza el inventario de productos usando un archivo CSV.
    
    📋 REGLAS DE ACTUALIZACIÓN:
    - Si el nombre existe, actualiza stock, precio y categoria (SIEMPRE)
    - Si el nombre NO existe, lo crea con los datos del CSV
    - Si el nombre está en DB y NO viene en el CSV, su stock se actualiza a 0
    - No afecta el histórico de ventas
    
    📝 COLUMNAS REQUERIDAS: nombre, descripcion, precio, stock
    📝 COLUMNA OPCIONAL: categoria
    
    🏷️ REGLAS DE CATEGORÍA:
    - Si CSV NO tiene columna 'categoria' → categoria = "General"
    - Si CSV tiene columna 'categoria' pero celda vacía → categoria = "General"  
    - Si CSV tiene categoria válida → usa esa categoria
    - Si producto existe y CSV tiene categoria → ACTUALIZA la categoria
    """
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        # Validar columnas mínimas requeridas
        required_cols = {"nombre", "descripcion", "precio", "stock"}
        if not required_cols.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"El CSV debe tener las columnas: {', '.join(required_cols)}")

        # Verificar si hay columna categoria
        tiene_categoria = "categoria" in df.columns

        # 1. Obtener todos los productos actuales en la DB
        result = await db.execute(select(Producto))
        productos_db = result.scalars().all()
        nombres_db = {p.nombre: p for p in productos_db}

        nombres_csv = set(df["nombre"])

        # Función para asignar categoria por defecto
        def asignar_categoria_defecto(nombre, categoria_csv=None):
            # REGLA 1: Si no hay categoria en CSV o está vacía → "General"
            if not categoria_csv or str(categoria_csv).strip() == '' or str(categoria_csv).lower() == 'nan':
                return "General"
            
            # Si hay categoria en CSV, usarla
            return str(categoria_csv).strip()

        # 2. Actualizar/crear productos desde el CSV
        for _, row in df.iterrows():
            nombre = row["nombre"]
            categoria_csv = row.get("categoria") if tiene_categoria else None
            categoria_final = asignar_categoria_defecto(nombre, categoria_csv)
            
            if nombre in nombres_db:
                # REGLA 2: Actualiza stock, precio Y categoria (si CSV tiene categoria)
                producto = nombres_db[nombre]
                producto.descripcion = row["descripcion"]
                producto.precio = float(row["precio"])
                producto.stock = int(row["stock"])
                
                # Siempre actualizar categoria (será "General" si no viene en CSV)
                producto.categoria = categoria_final
                producto.activo = producto.stock > 0
            else:
                # Crea nuevo producto con categoria final
                producto = Producto(
                    nombre=row["nombre"],
                    descripcion=row["descripcion"],
                    precio=float(row["precio"]),
                    stock=int(row["stock"]),
                    categoria=categoria_final,
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
