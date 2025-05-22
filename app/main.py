from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.api.auth import router as auth_router
from app.api.producto import router as producto_router
from app.api.venta import router as venta_router
from app.api.logs import router as logs_router
from app.api.chat import router as chat_router   # <-- Agregado

app = FastAPI()

app.include_router(auth_router)
app.include_router(producto_router)
app.include_router(venta_router)
app.include_router(logs_router)
app.include_router(chat_router)   # <-- Agregado

@app.get("/")
def root():
    return JSONResponse(content={"ok": True})
