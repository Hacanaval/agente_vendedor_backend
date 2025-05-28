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
from app.api.testing_semantico import router as testing_router
from app.api.monitoring import router as monitoring_router

# Importa la función para crear tablas
from app.core.database import create_tables

# Importa el WebSocket Manager Enterprise y Rate Limiter
from app.core.websocket_manager import ws_manager
from app.core.rate_limiting import rate_limiter

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
    """Inicialización del servidor con componentes enterprise"""
    global app_start_time
    app_start_time = datetime.now()
    logger.info("🚀 Iniciando servidor con componentes enterprise...")
    
    try:
        await create_tables()
        logger.info("✅ Tablas de base de datos creadas/verificadas")
        
        # Inicializar estado por defecto del sistema AI (siempre ON)
        from app.core.database import get_db
        from app.services.chat_control_service import ChatControlService
        db_gen = get_db()
        db = await db_gen.__anext__()
        try:
            await ChatControlService.ensure_default_global_state(db)
            logger.info("✅ Estado por defecto del sistema AI inicializado")
        finally:
            await db.close()
        
        # Inicializar WebSocket Manager Enterprise
        await ws_manager.start()
        logger.info("✅ WebSocket Manager Enterprise iniciado")
        
        logger.info("🎉 Servidor iniciado exitosamente con componentes enterprise")
        
    except Exception as e:
        logger.error(f"❌ Error durante la inicialización: {str(e)}", exc_info=True)
        raise

# Evento de cierre para cleanup
@app.on_event("shutdown") 
async def shutdown_event():
    """Cierre elegante del servidor"""
    logger.info("🔄 Cerrando servidor...")
    
    try:
        # Cerrar WebSocket Manager
        await ws_manager.stop()
        logger.info("✅ WebSocket Manager cerrado")
        
        # Cerrar base de datos
        from app.core.database import close_database
        await close_database()
        logger.info("✅ Base de datos cerrada")
        
        logger.info("✅ Servidor cerrado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante el cierre: {str(e)}")

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
app.include_router(testing_router)
app.include_router(monitoring_router)

# Health check mejorado con métricas enterprise
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check con información detallada del sistema y métricas enterprise"""
    try:
        # Calcular uptime
        uptime_delta = datetime.now() - app_start_time
        uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds%3600)//60}m"
        
        # Verificar estado de la base de datos con métricas de pool
        database_status = "connected"
        database_info = {}
        try:
            from app.core.database import check_database_health, get_connection_stats
            
            # Health check básico
            db_health = await check_database_health()
            database_status = db_health.get("status", "unknown")
            
            # Estadísticas del pool de conexiones
            connection_stats = await get_connection_stats()
            database_info = {
                "health": db_health,
                "connection_pool": connection_stats
            }
            
        except Exception as e:
            database_status = "error"
            database_info = {"error": str(e)}
        
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
        
        # Verificar Sentence Transformers
        try:
            import sentence_transformers
            dependencies["sentence_transformers"] = "available"
        except ImportError:
            dependencies["sentence_transformers"] = "not_available"
        
        # Verificar Torch
        try:
            import torch
            dependencies["torch"] = "available"
        except ImportError:
            dependencies["torch"] = "not_available"
        
        # Obtener estadísticas de WebSocket Manager
        websocket_stats = ws_manager.get_connection_stats()
        
        # Obtener estadísticas de Rate Limiter
        rate_limit_stats = rate_limiter.get_stats()
        
        # Obtener estadísticas de embeddings
        try:
            from app.services.embeddings_service import get_embeddings_stats
            embeddings_stats = get_embeddings_stats()
        except Exception:
            embeddings_stats = {"status": "not_initialized"}
        
        # Determinar estado general del sistema
        overall_status = StatusEnum.SUCCESS
        status_message = "Sistema funcionando óptimamente"
        
        # Verificar alertas
        alerts = []
        
        if database_status != "healthy":
            overall_status = StatusEnum.ERROR
            status_message = "Problemas con la base de datos"
            alerts.append("Base de datos no disponible")
        
        if websocket_stats["current_connections"] > websocket_stats["limits"]["max_global"] * 0.8:
            overall_status = StatusEnum.WARNING
            status_message = "Alta carga de conexiones WebSocket"
            alerts.append("Conexiones WebSocket cerca del límite")
        
        if rate_limit_stats["block_rate"] > 10:  # Más del 10% de requests bloqueadas
            alerts.append("Alto rate de requests bloqueadas")
        
        if len(alerts) > 0 and overall_status == StatusEnum.SUCCESS:
            overall_status = StatusEnum.WARNING
            status_message = "Sistema con advertencias"
        
        return HealthResponse(
            service_name="Agente Vendedor API Enterprise",
            version="2.0.0",
            uptime=uptime_str,
            database_status=database_status,
            dependencies=dependencies,
            status=overall_status,
            message=status_message,
            # Nuevas métricas enterprise
            enterprise_metrics={
                "database": database_info,
                "websockets": websocket_stats,
                "rate_limiting": rate_limit_stats,
                "embeddings": embeddings_stats,
                "alerts": alerts,
                "performance": {
                    "uptime_seconds": uptime_delta.total_seconds(),
                    "peak_connections": websocket_stats.get("peak_connections", 0),
                    "total_requests_checked": rate_limit_stats.get("requests_checked", 0),
                    "requests_blocked": rate_limit_stats.get("requests_blocked", 0)
                }
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {str(e)}")
        return HealthResponse(
            status=StatusEnum.ERROR,
            message=f"Error en health check: {str(e)}",
            database_status="unknown",
            dependencies={},
            enterprise_metrics={"error": str(e)}
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
