#!/usr/bin/env python3
"""
Script para crear todas las tablas de la base de datos
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base

async def create_all_tables():
    """Crear todas las tablas definidas en los modelos"""
    try:
        # Importar todos los modelos para que estén registrados en Base
        from app.models.mensaje import Mensaje
        from app.models.producto import Producto
        from app.models.venta import Venta
        from app.models.cliente import Cliente
        
        print("📋 Creando todas las tablas...")
        
        # Crear todas las tablas
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Todas las tablas creadas exitosamente")
        
        # Verificar tablas creadas
        async with engine.begin() as conn:
            result = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = result.fetchall()
            print(f"📊 Tablas disponibles: {[table[0] for table in tables]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_all_tables())