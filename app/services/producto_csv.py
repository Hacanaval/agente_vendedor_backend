import pandas as pd
from typing import List, Dict
from fastapi import HTTPException

def parse_csv_productos(file) -> List[Dict]:
    try:
        df = pd.read_csv(file)
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo CSV inválido o corrupto")
    required_cols = {"nombre", "descripcion", "precio", "stock"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"El CSV debe tener las columnas: {', '.join(required_cols)}")
    productos = []
    nombres_vistos = set()
    for idx, row in df.iterrows():
        try:
            nombre = str(row["nombre"]).strip()
            descripcion = str(row["descripcion"]).strip()
            precio = float(row["precio"])
            stock = int(row["stock"])
            if not nombre or not descripcion:
                raise ValueError("Nombre y descripción no pueden estar vacíos")
            if precio <= 0 or stock <= 0:
                raise ValueError("Precio y stock deben ser mayores a cero")
            if nombre.lower() in nombres_vistos:
                raise ValueError(f"Producto duplicado en el archivo: {nombre}")
            nombres_vistos.add(nombre.lower())
            producto = {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": precio,
                "stock": stock,
            }
            productos.append(producto)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error en fila {idx+2}: {str(e)}")
    return productos 