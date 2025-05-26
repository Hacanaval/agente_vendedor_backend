import asyncio
from app.core.database import SessionLocal
from app.models.producto import Producto
from sqlalchemy.future import select

async def test_productos():
    print("=== PRUEBA 1: Verificando productos en la DB ===")
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(Producto))
            productos = result.scalars().all()
            
            print(f"Total de productos en la DB: {len(productos)}")
            
            if productos:
                print("\nProductos encontrados:")
                for p in productos:
                    print(f"- {p.nombre} | ${p.precio} | Stock: {p.stock} | Activo: {p.activo}")
            else:
                print("❌ No hay productos en la base de datos")
                
        except Exception as e:
            print(f"❌ Error al consultar productos: {e}")

if __name__ == "__main__":
    asyncio.run(test_productos()) 