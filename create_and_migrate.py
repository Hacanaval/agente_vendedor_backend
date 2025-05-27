#!/usr/bin/env python3
"""
Script para crear tablas y aplicar migración de correo directamente con SQLite
"""
import sqlite3
import os

def create_all_tables_and_migrate():
    """Crear todas las tablas e incluir el campo correo"""
    
    # Conectar a la base de datos SQLite
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        print("📋 Creando tabla clientes con campo correo...")
        
        # Crear tabla clientes con todos los campos incluido correo
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                cedula VARCHAR(20) PRIMARY KEY,
                nombre_completo VARCHAR(200) NOT NULL,
                telefono VARCHAR(20) NOT NULL,
                correo VARCHAR(200),
                direccion TEXT NOT NULL,
                barrio VARCHAR(100) NOT NULL,
                indicaciones_adicionales TEXT,
                fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_ultima_compra DATETIME,
                total_compras INTEGER DEFAULT 0,
                valor_total_compras INTEGER DEFAULT 0,
                activo BOOLEAN DEFAULT 1,
                notas TEXT
            )
        ''')
        
        # Crear índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_correo ON clientes(correo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula)')
        
        print("✅ Tabla clientes creada con éxito")
        
        # Crear tabla productos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(200) NOT NULL,
                descripcion TEXT,
                precio INTEGER NOT NULL,
                stock INTEGER DEFAULT 0,
                activo BOOLEAN DEFAULT 1,
                fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        print("✅ Tabla productos creada")
        
        # Crear tabla ventas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                total INTEGER NOT NULL,
                chat_id VARCHAR(100),
                estado VARCHAR(50) DEFAULT 'pendiente',
                cliente_cedula VARCHAR(20),
                detalle JSON,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos (id),
                FOREIGN KEY (cliente_cedula) REFERENCES clientes (cedula)
            )
        ''')
        
        print("✅ Tabla ventas creada")
        
        # Crear tabla mensajes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id VARCHAR(100) NOT NULL,
                remitente VARCHAR(50) NOT NULL,
                mensaje TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                estado_venta VARCHAR(50),
                tipo_mensaje VARCHAR(50),
                metadatos JSON
            )
        ''')
        
        print("✅ Tabla mensajes creada")
        
        # Insertar algunos productos de prueba
        productos_test = [
            ("Extintor PQS 10 libras", "Extintor de polvo químico seco de 10 libras", 45000, 50),
            ("Extintor PQS 20 libras", "Extintor de polvo químico seco de 20 libras", 65000, 30),
            ("Casco de Seguridad Amarillo", "Casco de seguridad industrial color amarillo", 25000, 100),
            ("Guantes de Nitrilo", "Guantes de protección en nitrilo", 8000, 200),
            ("Botas de Seguridad", "Botas de seguridad con punta de acero", 85000, 40),
            ("Chaleco Reflectivo", "Chaleco de alta visibilidad reflectivo", 15000, 80),
            ("Linterna LED Recargable", "Linterna LED recargable de alta potencia", 35000, 60),
        ]
        
        cursor.executemany(
            'INSERT OR IGNORE INTO productos (nombre, descripcion, precio, stock) VALUES (?, ?, ?, ?)',
            productos_test
        )
        
        print("📦 Productos de prueba insertados")
        
        # Verificar tablas creadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Tablas disponibles: {[table[0] for table in tables]}")
        
        # Verificar estructura de clientes
        cursor.execute("PRAGMA table_info(clientes)")
        columns = cursor.fetchall()
        print(f"🏗️ Columnas en clientes: {[col[1] for col in columns]}")
        
        conn.commit()
        print("🎉 Base de datos creada exitosamente con campo correo incluido")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    create_all_tables_and_migrate() 