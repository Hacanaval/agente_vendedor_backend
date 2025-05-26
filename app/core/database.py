import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carga variables de entorno
load_dotenv()

# URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/dbname")

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

# Declarative base para modelos
Base = declarative_base()

# Dependencia para FastAPI (inyección de sesión)
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
