"""
Sistema de Base de Datos Enterprise
Configuración optimizada para alta concurrencia y escalabilidad
"""
import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from dotenv import load_dotenv

# Importa la Base desde el nuevo archivo
from .base_class import Base

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

logger = logging.getLogger(__name__)

# ===============================
# CONFIGURACIÓN ENTERPRISE
# ===============================

# Configuración del Pool de Conexiones para diferentes entornos
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Configuración PRODUCCIÓN - Máximo rendimiento
    POOL_SIZE = 20              # Conexiones base en el pool
    MAX_OVERFLOW = 30           # Conexiones adicionales bajo demanda
    POOL_TIMEOUT = 30           # Timeout para obtener conexión (segundos)
    POOL_RECYCLE = 3600         # Reciclar conexiones cada hora
    POOL_PRE_PING = True        # Verificar conexiones antes de usar
    ECHO_SQL = False            # No logs SQL en producción
elif ENVIRONMENT == "testing":
    # Configuración TESTING - Optimizada para tests
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 10
    POOL_RECYCLE = 1800
    POOL_PRE_PING = True
    ECHO_SQL = False
else:
    # Configuración DESARROLLO - Balanceada
    POOL_SIZE = 10
    MAX_OVERFLOW = 20
    POOL_TIMEOUT = 20
    POOL_RECYCLE = 1800
    POOL_PRE_PING = True
    ECHO_SQL = os.getenv("SQLALCHEMY_ECHO", "False") == "True"

# URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")

# ===============================
# ENGINE CONFIGURATION
# ===============================

def create_database_engine():
    """
    Crea el engine de base de datos con configuración optimizada
    """
    engine_kwargs = {
        "echo": ECHO_SQL,
        "future": True,
        "pool_pre_ping": POOL_PRE_PING,
        "pool_recycle": POOL_RECYCLE,
    }
    
    # Configuración específica por tipo de BD
    if DATABASE_URL.startswith("sqlite"):
        # SQLite: Configuración especial para desarrollo/testing
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": POOL_TIMEOUT,
                "isolation_level": None  # Autocommit mode
            }
        })
        logger.info(f"🗄️ Configurando SQLite con StaticPool")
        
    elif DATABASE_URL.startswith("postgresql"):
        # PostgreSQL: Configuración enterprise
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "connect_args": {
                "server_settings": {
                    "application_name": "agente_vendedor_api",
                    "jit": "off"  # Optimización para queries rápidas
                }
            }
        })
        logger.info(f"🐘 Configurando PostgreSQL con pool: {POOL_SIZE}+{MAX_OVERFLOW} conexiones")
        
    else:
        # Otras BD: Configuración por defecto
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT
        })
        logger.info(f"🔧 Configurando BD genérica con pool: {POOL_SIZE}+{MAX_OVERFLOW} conexiones")
    
    return create_async_engine(DATABASE_URL, **engine_kwargs)

# Crear el engine global
engine = create_database_engine()

# ===============================
# SESSION CONFIGURATION
# ===============================

# Crear el SessionLocal con configuración optimizada
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,      # Flush automático para mejor performance
    autocommit=False
)

# ===============================
# DATABASE OPERATIONS
# ===============================

async def create_tables():
    """
    Crea las tablas de la base de datos
    """
    try:
        logger.info("🏗️ Creando/verificando tablas de la base de datos...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tablas creadas/verificadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        raise
    finally:
        # No hacer dispose aquí para mantener el pool activo
        pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia para FastAPI - Inyección de sesión con manejo de errores robusto
    """
    session = None
    try:
        session = SessionLocal()
        yield session
        await session.commit()  # Commit explícito para mejor control
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(f"Error en sesión de BD: {e}")
        raise
    finally:
        if session:
            await session.close()

# ===============================
# HEALTH CHECK & MONITORING
# ===============================

async def check_database_health() -> dict:
    """
    Verifica la salud de la base de datos y el pool de conexiones
    """
    try:
        async with SessionLocal() as session:
            # Query simple para verificar conectividad
            result = await session.execute("SELECT 1")
            result.fetchone()
            
            # Información del pool
            pool_info = {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "invalid": engine.pool.invalid()
            }
            
            return {
                "status": "healthy",
                "database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
                "environment": ENVIRONMENT,
                "pool_info": pool_info,
                "total_connections": pool_info["checked_in"] + pool_info["checked_out"]
            }
            
    except Exception as e:
        logger.error(f"Health check de BD falló: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "environment": ENVIRONMENT
        }

async def get_connection_stats() -> dict:
    """
    Obtiene estadísticas detalladas del pool de conexiones
    """
    try:
        pool = engine.pool
        return {
            "pool_size_configured": POOL_SIZE,
            "max_overflow_configured": MAX_OVERFLOW,
            "pool_timeout_configured": POOL_TIMEOUT,
            "pool_recycle_configured": POOL_RECYCLE,
            "current_pool_size": pool.size(),
            "connections_checked_in": pool.checkedin(),
            "connections_checked_out": pool.checkedout(),
            "connections_overflow": pool.overflow(),
            "connections_invalid": pool.invalid(),
            "total_active_connections": pool.checkedout() + pool.overflow()
        }
    except Exception as e:
        logger.error(f"Error obteniendo stats de conexiones: {e}")
        return {"error": str(e)}

# ===============================
# GRACEFUL SHUTDOWN
# ===============================

async def close_database():
    """
    Cierra el engine de base de datos de forma elegante
    """
    try:
        logger.info("🔄 Cerrando conexiones de base de datos...")
        await engine.dispose()
        logger.info("✅ Base de datos cerrada correctamente")
    except Exception as e:
        logger.error(f"❌ Error cerrando base de datos: {e}")

# ===============================
# LOGGING CONFIGURATION
# ===============================

# Log de configuración al importar
logger.info(f"🏗️ Base de datos configurada:")
logger.info(f"   • Entorno: {ENVIRONMENT}")
logger.info(f"   • Pool size: {POOL_SIZE} + {MAX_OVERFLOW} overflow")
logger.info(f"   • Timeout: {POOL_TIMEOUT}s")
logger.info(f"   • Recycle: {POOL_RECYCLE}s")
logger.info(f"   • Pre-ping: {POOL_PRE_PING}")
logger.info(f"   • Echo SQL: {ECHO_SQL}")
