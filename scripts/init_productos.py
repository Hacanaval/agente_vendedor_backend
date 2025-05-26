import asyncio
import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.producto import Producto
from sqlalchemy.future import select

PRODUCTOS_EJEMPLO = [
    {
        "nombre": "Casco de Seguridad Industrial",
        "descripcion": "Casco de seguridad industrial con barboquejo, resistente a impactos, color blanco",
        "precio": 35000.0,
        "stock": 25,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Guantes de Nitrilo",
        "descripcion": "Guantes de nitrilo desechables, resistentes a químicos, caja x100 unidades",
        "precio": 45000.0,
        "stock": 15,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Botas de Seguridad",
        "descripcion": "Botas de seguridad con puntera de acero, antideslizantes, talla 39-44",
        "precio": 120000.0,
        "stock": 30,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Extintor ABC 10 libras",
        "descripcion": "Extintor multipropósito ABC de 10 libras, incluye soporte de pared",
        "precio": 85000.0,
        "stock": 12,
        "categoria": "Protección Contra Incendios"
    },
    {
        "nombre": "Respirador N95",
        "descripcion": "Respirador desechable N95, protección contra partículas, caja x20 unidades",
        "precio": 25000.0,
        "stock": 40,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Chaleco Reflectivo",
        "descripcion": "Chaleco reflectivo de alta visibilidad, talla única, color naranja",
        "precio": 18000.0,
        "stock": 35,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Gafas de Seguridad",
        "descripcion": "Gafas de seguridad transparentes, protección UV, antiempañantes",
        "precio": 15000.0,
        "stock": 50,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Detector de Humo",
        "descripcion": "Detector de humo fotoeléctrico, batería de 9V incluida, certificado",
        "precio": 65000.0,
        "stock": 20,
        "categoria": "Protección Contra Incendios"
    },
    {
        "nombre": "Arnés de Seguridad",
        "descripcion": "Arnés de seguridad para trabajo en alturas, certificado ANSI",
        "precio": 150000.0,
        "stock": 8,
        "categoria": "Protección Personal"
    },
    {
        "nombre": "Señalización de Emergencia",
        "descripcion": "Kit de señalización de emergencia fotoluminiscente, 10 señales",
        "precio": 75000.0,
        "stock": 18,
        "categoria": "Señalización"
    }
]

async def inicializar_productos():
    """
    Inicializa productos de ejemplo en la base de datos si no existen.
    """
    print("🚀 Iniciando inserción de productos de ejemplo...")
    
    async with SessionLocal() as db:
        try:
            # Verificar si ya existen productos
            result = await db.execute(select(Producto))
            productos_existentes = result.scalars().all()
            
            if productos_existentes:
                print(f"✅ Ya existen {len(productos_existentes)} productos en la base de datos.")
                print("Productos existentes:")
                for p in productos_existentes:
                    print(f"  - {p.nombre} (${p.precio:,.0f}) - Stock: {p.stock}")
                return
            
            # Insertar productos de ejemplo
            productos_insertados = 0
            for producto_data in PRODUCTOS_EJEMPLO:
                producto = Producto(**producto_data)
                db.add(producto)
                productos_insertados += 1
            
            await db.commit()
            print(f"✅ Se insertaron {productos_insertados} productos de ejemplo exitosamente.")
            
            # Mostrar productos insertados
            print("\nProductos insertados:")
            for producto_data in PRODUCTOS_EJEMPLO:
                print(f"  - {producto_data['nombre']} (${producto_data['precio']:,.0f}) - Stock: {producto_data['stock']}")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error al insertar productos: {str(e)}")
            raise

async def main():
    """
    Función principal del script.
    """
    try:
        await inicializar_productos()
        print("\n🎉 Script completado exitosamente.")
    except Exception as e:
        print(f"\n💥 Error en el script: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 