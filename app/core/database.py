import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Importa la Base desde el nuevo archivo
from .base_class import Base  # MODIFICADO

# Carga variables de entorno
load_dotenv()

# Importa modelos (asegúrate de importar TODOS tus modelos aquí)
# Estos modelos deben heredar de la Base importada arriba
from app.models.producto import Producto
# from app.models.pedido import Pedido # ELIMINADO - Modelo no existe
from app.models.cliente import Cliente
from app.models.venta import Venta
from app.models.mensaje import Mensaje
from app.models.chat_control import ChatControl

# URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")

# Crear el engine asíncrono
engine = create_async_engine(
    DATABASE_URL, 
    echo=os.getenv("SQLALCHEMY_ECHO", "False") == "True",  # Controla logs SQL por entorno
    future=True
)

# Crea el SessionLocal para inyección de dependencias
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Ya no se define Base aquí, se importa
# Base = declarative_base() # ELIMINADO

# Función para crear tablas (llamar al inicio de la app)
async def create_tables():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Opcional: borrar tablas existentes
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

# Dependencia para FastAPI (inyección de sesión)
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
