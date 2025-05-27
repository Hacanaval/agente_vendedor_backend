#!/usr/bin/env python3
"""
Script para migrar la base de datos y crear las tablas de clientes
"""

import asyncio
from app.core.database import engine
from sqlalchemy import text

async def migrate_clientes():
    """Ejecuta la migración para crear tablas de clientes"""
    try:
        async with engine.begin() as conn:
            print("🔧 Iniciando migración de clientes...")
            
            # Crear tabla de clientes
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS clientes (
                    cedula VARCHAR(20) PRIMARY KEY,
                    nombre_completo VARCHAR(200) NOT NULL,
                    telefono VARCHAR(20) NOT NULL,
                    direccion TEXT NOT NULL,
                    barrio VARCHAR(100) NOT NULL,
                    indicaciones_adicionales TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_ultima_compra TIMESTAMP,
                    total_compras INTEGER DEFAULT 0,
                    valor_total_compras INTEGER DEFAULT 0,
                    activo BOOLEAN DEFAULT TRUE,
                    notas TEXT
                )
            '''))
            print("✅ Tabla 'clientes' creada")
            
            # Agregar columna cliente_cedula a venta si no existe
            await conn.execute(text('''
                ALTER TABLE venta ADD COLUMN IF NOT EXISTS cliente_cedula VARCHAR(20)
            '''))
            print("✅ Columna 'cliente_cedula' agregada a tabla 'venta'")
            
            # Crear índices
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre_completo)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_fecha_ultima_compra ON clientes(fecha_ultima_compra)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_valor_total ON clientes(valor_total_compras)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_activo ON clientes(activo)",
                "CREATE INDEX IF NOT EXISTS idx_venta_cliente_cedula ON venta(cliente_cedula)"
            ]
            
            for indice in indices:
                await conn.execute(text(indice))
            
            print("✅ Índices creados")
            
            # Agregar comentarios (opcional, algunos DBs no lo soportan)
            try:
                comentarios = [
                    "COMMENT ON TABLE clientes IS 'Tabla de clientes con información completa y estadísticas de compras'",
                    "COMMENT ON COLUMN clientes.cedula IS 'Cédula del cliente (ID principal único)'",
                    "COMMENT ON COLUMN venta.cliente_cedula IS 'Cédula del cliente que realizó la compra'"
                ]
                
                for comentario in comentarios:
                    await conn.execute(text(comentario))
                
                print("✅ Comentarios agregados")
            except Exception as e:
                print(f"⚠️ No se pudieron agregar comentarios (normal en algunas DBs): {e}")
            
            print("🎉 Migración de clientes completada exitosamente")
            
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_clientes()) 