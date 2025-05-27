from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

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


# Importa la función para crear tablas
from app.core.database import create_tables

# Instancia FastAPI
app = FastAPI(
    title="Agente Vendedor SaaS Backend",
    description="API backend para chatbot vendedor multiempresa, RAG y memoria",
    version="1.0.0"
)

# Evento de inicio para crear tablas
@app.on_event("startup")
async def startup_event():
    await create_tables()
    
    # Inicializar estado por defecto del sistema AI (siempre ON)
    from app.core.database import get_db
    from app.services.chat_control_service import ChatControlService
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        await ChatControlService.ensure_default_global_state(db)
    finally:
        await db.close()
    
    # Carga inicial de productos (opcional, solo si es necesario)
    # from app.services.producto_service import cargar_productos_iniciales
    # loop = asyncio.get_event_loop()
    # await loop.run_in_executor(None, cargar_productos_iniciales) # Ejecutar en hilo separado si es largo

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

# Healthcheck o raíz
@app.get("/")
async def root():
    return JSONResponse(content={"ok": True, "mensaje": "API online", "version": "1.0.0"})

# Manejo global de errores opcional (para logging centralizado)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Aquí puedes agregar logging a un sistema externo si quieres
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)}
    )
