import asyncio
import sys
sys.path.append('..')
from app.core.database import SessionLocal
from app.models.producto import Producto

async def agregar_productos_similares():
    """Agregar productos similares para probar el manejo de SKUs"""
    async with SessionLocal() as db:
        productos_similares = [
            # Extintores de diferentes tamaños
            {
                "nombre": "Extintor PQS 20 libras",
                "descripcion": "Extintor de polvo químico seco de 20 libras, ideal para fuegos clase ABC de mayor magnitud",
                "precio": 180000.0,
                "stock": 15,
                "categoria": "Protección contra incendios",
                "activo": True
            },
            # Cascos de diferentes colores
            {
                "nombre": "Casco de Seguridad Amarillo",
                "descripcion": "Casco de seguridad industrial color amarillo, resistente a impactos",
                "precio": 25000.0,
                "stock": 30,
                "categoria": "Protección de cabeza",
                "activo": True
            },
            {
                "nombre": "Casco de Seguridad Azul",
                "descripcion": "Casco de seguridad industrial color azul, resistente a impactos",
                "precio": 25000.0,
                "stock": 25,
                "categoria": "Protección de cabeza",
                "activo": True
            },
            # Linternas de diferentes tipos
            {
                "nombre": "Linterna LED Recargable Pequeña",
                "descripcion": "Linterna LED recargable compacta de 200 lúmenes, ideal para uso personal",
                "precio": 45000.0,
                "stock": 20,
                "categoria": "Iluminación",
                "activo": True
            },
            {
                "nombre": "Linterna LED Recargable Grande",
                "descripcion": "Linterna LED recargable profesional de 500 lúmenes, para uso industrial",
                "precio": 85000.0,
                "stock": 12,
                "categoria": "Iluminación",
                "activo": True
            }
        ]
        
        productos_agregados = 0
        for producto_data in productos_similares:
            # Verificar si ya existe
            from sqlalchemy.future import select
            existing = await db.execute(
                select(Producto.id).where(Producto.nombre == producto_data['nombre'])
            )
            if not existing.scalar():
                producto = Producto(**producto_data)
                db.add(producto)
                productos_agregados += 1
                print(f"✅ Agregado: {producto_data['nombre']}")
            else:
                print(f"⚠️  Ya existe: {producto_data['nombre']}")
        
        await db.commit()
        print(f"\n🎉 Se agregaron {productos_agregados} productos similares para testing")

if __name__ == "__main__":
    asyncio.run(agregar_productos_similares()) 