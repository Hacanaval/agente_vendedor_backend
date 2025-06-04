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
    ✅ ENDPOINT CORREGIDO: Reemplaza el inventario usando CSV.
    
    📋 REGLAS:
    ✅ CSV + DB: Actualizar precio, stock, descripción y categoría  
    ✅ DB pero NO CSV: Stock = 0, activo = False (chatbot no los ofrece)
    ✅ CSV pero NO DB: Crear nuevo producto
    
    📝 COLUMNAS REQUERIDAS: nombre, descripcion, precio, stock
    📝 COLUMNA OPCIONAL: categoria (si no está, se asigna "General")
    """
    try:
        # Validaciones básicas del archivo
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Debe ser un archivo CSV (.csv)")
        
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="El archivo CSV está vacío")
        
        # Parsear CSV
        df = pd.read_csv(io.BytesIO(content))
        if df.empty:
            raise HTTPException(status_code=400, detail="El CSV no contiene datos")

        # Validar columnas requeridas
        required_cols = {"nombre", "descripcion", "precio", "stock"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise HTTPException(status_code=400, detail=f"Faltan columnas: {', '.join(missing)}")

        # Verificar si hay columna categoria
        tiene_categoria = "categoria" in df.columns

        # 1. Obtener productos actuales de la DB
        result = await db.execute(select(Producto))
        productos_db = result.scalars().all()
        nombres_db = {p.nombre: p for p in productos_db}

        # Obtener nombres válidos del CSV
        nombres_csv = {str(nombre).strip() for nombre in df["nombre"] if pd.notna(nombre) and str(nombre).strip()}

        # Función para categoria por defecto
        def asignar_categoria(cat_csv=None):
            if not cat_csv or pd.isna(cat_csv) or str(cat_csv).strip() == "":
                return "General"
            return str(cat_csv).strip()

        # Contadores
        creados, actualizados, desactivados = 0, 0, 0

        # 2. ✅ PROCESAR PRODUCTOS DEL CSV
        for _, row in df.iterrows():
            nombre = str(row["nombre"]).strip()
            if not nombre:
                continue
                
            try:
                precio = float(row["precio"])
                stock = int(float(row["stock"]))
                descripcion = str(row["descripcion"]) if pd.notna(row["descripcion"]) else ""
                categoria = asignar_categoria(row.get("categoria") if tiene_categoria else None)
                
                if nombre in nombres_db:
                    # ✅ Actualizar existente
                    p = nombres_db[nombre]
                    p.descripcion = descripcion
                    p.precio = precio
                    p.stock = stock
                    p.categoria = categoria
                    p.activo = stock > 0
                    actualizados += 1
                else:
                    # ✅ Crear nuevo
                    nuevo = Producto(
                        nombre=nombre,
                        descripcion=descripcion,
                        precio=precio,
                        stock=stock,
                        categoria=categoria,
                        activo=stock > 0
                    )
                    db.add(nuevo)
                    creados += 1
            except ValueError:
                continue  # Saltar filas con datos inválidos

        # 3. ✅ DESACTIVAR PRODUCTOS NO EN CSV
        for nombre in set(nombres_db.keys()) - nombres_csv:
            p = nombres_db[nombre]
            if p.activo or p.stock > 0:
                p.stock = 0
                p.activo = False
                desactivados += 1

        await db.commit()
        
        # 4. ✅ Sincronizar FAISS (opcional, no crítico)
        sync_status = "No disponible"
        try:
            from app.services.retrieval.retriever_factory import get_retriever
            retriever = get_retriever(db)
            await retriever.sync_with_db()
            sync_status = "Exitoso"
            logging.info("✅ Índice FAISS sincronizado")
        except ImportError:
            sync_status = "Módulo no disponible"
            logging.warning("⚠️ Módulo retriever no disponible")
        except Exception as e:
            sync_status = f"Error no crítico: {str(e)[:50]}"
            logging.warning(f"⚠️ Error sincronizando retriever (no crítico): {e}")

        return {
            "success": True,
            "message": "✅ Inventario actualizado correctamente",
            "estadisticas": {
                "productos_creados": creados,
                "productos_actualizados": actualizados,
                "productos_desactivados": desactivados,
                "sync_faiss": sync_status
            }
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error en reemplazar_csv: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando CSV: {str(e)[:100]}")
