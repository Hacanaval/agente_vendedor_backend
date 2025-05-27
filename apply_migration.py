#!/usr/bin/env python3
"""
Script para aplicar migración de campo correo a clientes
"""
import sqlite3
import os

def apply_migration():
    # Verificar si existe la base de datos
    db_path = 'app.db'
    if not os.path.exists(db_path):
        print('❌ Base de datos no encontrada. Ejecutando app para crearla...')
        return False

    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Verificar si la columna correo ya existe
        cursor.execute("PRAGMA table_info(clientes)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'correo' in columns:
            print('✅ La columna correo ya existe en la tabla clientes')
            return True
        else:
            # Agregar la columna correo
            cursor.execute('ALTER TABLE clientes ADD COLUMN correo VARCHAR(200)')
            
            # Crear índice (SQLite no soporta CREATE INDEX IF NOT EXISTS directamente)
            try:
                cursor.execute('CREATE INDEX idx_clientes_correo ON clientes(correo)')
                print('✅ Columna correo agregada con éxito e índice creado')
            except sqlite3.OperationalError as e:
                if 'already exists' in str(e):
                    print('✅ Columna correo agregada, índice ya existía')
                else:
                    print(f'⚠️ Columna agregada pero error creando índice: {e}')
            
            conn.commit()
            print('🔄 Migración completada')
            return True
            
    except Exception as e:
        print(f'❌ Error en migración: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration() 