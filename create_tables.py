import asyncio
from app.core.database import engine, Base
import app.models.empresa
import app.models.usuario
import app.models.cliente_final
import app.models.mensaje
import app.models.producto
import app.models.venta
import app.models.inventario_log
import app.models.logs

async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("¡Tablas creadas exitosamente!")

if __name__ == "__main__":
    asyncio.run(create_all_tables())