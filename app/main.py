from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime

# Importar el sistema de excepciones
from app.core.exceptions import register_exception_handlers
from app.models.responses import HealthResponse, StatusEnum

# Importa los routers
from app.api.auth import router as auth_router
from app.api.producto import router as producto_router
from app.api.venta import router as venta_router
from app.api.logs import router as logs_router
from app.api.chat import router as chat_router
from app.api.pedidos import router as pedidos_router
from app.api.admin import router as admin_router
from app.api.clientes import router as clientes_router
from app.api.exportar import router as exportar_router
from app.api.chat_control import router as chat_control_router
from app.api.websockets import router as websockets_router
from app.api.files import router as files_router

# Importa la función para crear tablas
from app.core.database import create_tables

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instancia FastAPI
app = FastAPI(
    title="Agente Vendedor SaaS Backend",
    description="API backend para chatbot vendedor multiempresa, RAG y memoria",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Variable global para almacenar tiempo de inicio
app_start_time = datetime.now()

# Registrar manejadores de excepciones
register_exception_handlers(app)

# Evento de inicio para crear tablas
@app.on_event("startup")
async def startup_event():
    """Inicialización del servidor"""
    global app_start_time
    app_start_time = datetime.now()
    logger.info("Iniciando servidor...")
    
    try:
        await create_tables()
        logger.info("Tablas de base de datos creadas/verificadas")
        
        # Inicializar estado por defecto del sistema AI (siempre ON)
        from app.core.database import get_db
        from app.services.chat_control_service import ChatControlService
        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            await ChatControlService.ensure_default_global_state(db)
            logger.info("Estado por defecto del sistema AI inicializado")
        finally:
            await db.close()
        
        logger.info("Servidor iniciado exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la inicialización: {str(e)}", exc_info=True)
        raise

# Middleware CORS (habilita acceso desde frontend local u otros dominios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia en producción a dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers (orden importante si hay conflictos de rutas)
app.include_router(auth_router)
app.include_router(producto_router)
app.include_router(venta_router)
app.include_router(logs_router)
app.include_router(chat_router)
app.include_router(pedidos_router)
app.include_router(admin_router)
app.include_router(clientes_router)
app.include_router(exportar_router)
app.include_router(chat_control_router)
app.include_router(websockets_router)
app.include_router(files_router)

# Health check mejorado
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check con información detallada del sistema"""
    try:
        # Calcular uptime
        uptime_delta = datetime.now() - app_start_time
        uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds%3600)//60}m"
        
        # Verificar estado de la base de datos
        database_status = "connected"
        try:
            from app.core.database import get_db
            db_gen = get_db()
            db = await db_gen.__anext__()
            await db.close()
        except Exception:
            database_status = "disconnected"
        
        # Verificar dependencias principales
        dependencies = {}
        
        # Verificar Google Gemini
        try:
            import google.generativeai as genai
            dependencies["google_gemini"] = "available"
        except ImportError:
            dependencies["google_gemini"] = "not_available"
        
        # Verificar FAISS
        try:
            import faiss
            dependencies["faiss"] = "available"
        except ImportError:
            dependencies["faiss"] = "not_available"
        
        return HealthResponse(
            service_name="Agente Vendedor API",
            version="1.0.0",
            uptime=uptime_str,
            database_status=database_status,
            dependencies=dependencies,
            status=StatusEnum.SUCCESS if database_status == "connected" else StatusEnum.WARNING,
            message="Servicio funcionando correctamente" if database_status == "connected" else "Servicio con advertencias"
        )
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return HealthResponse(
            status=StatusEnum.ERROR,
            message=f"Error en health check: {str(e)}",
            database_status="unknown",
            dependencies={}
        )

# Raíz simplificada
@app.get("/")
async def root():
    """Endpoint raíz del API"""
    return JSONResponse(content={
        "service": "Agente Vendedor API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "health": "/health"
    })

# Endpoint de información del sistema
@app.get("/info")
async def system_info():
    """Información básica del sistema"""
    return JSONResponse(content={
        "name": "Agente Vendedor SaaS Backend",
        "version": "1.0.0",
        "description": "API backend para chatbot vendedor multiempresa, RAG y memoria",
        "features": [
            "Chat con IA",
            "Sistema RAG",
            "Gestión de productos",
            "Gestión de ventas",
            "Gestión de clientes",
            "Memoria conversacional",
            "Exportación de datos"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "chat": "/chat/texto",
            "productos": "/productos/",
            "ventas": "/ventas/",
            "clientes": "/clientes/"
        }
    })
