from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioRegister, UsuarioLogin, TokenResponse, UsuarioOut, EmpresaCreate
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/register")
async def register(data: UsuarioRegister, db: AsyncSession = Depends(get_db)):
    # TODO: Volver a proteger este endpoint con autenticación y multiempresa en producción
    return {"msg": "Registro ficticio (sin autenticación, sin multiempresa)"}

@router.post("/login")
async def login(data: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    # TODO: Volver a proteger este endpoint con autenticación y multiempresa en producción
    return {"access_token": "token-ficticio", "token_type": "bearer"}

@router.get("/me")
async def me(db: AsyncSession = Depends(get_db)):
    # TODO: Volver a proteger este endpoint con autenticación y multiempresa en producción
    return {"msg": "Usuario ficticio (sin autenticación, sin multiempresa)"}

# --- RECOMENDACIONES EXTRA ---

# 1. Para evitar el warning de Pydantic v2 en tus schemas:
#    Cambia en tus clases de schema (por ejemplo, UsuarioOut) la config:
#
#    class Config:
#        from_attributes = True
#
#    Y elimina cualquier 'orm_mode = True' (ya no es válido en Pydantic 2.x).
#
# 2. Si sigues viendo errores de bcrypt/passlib:
#    pip uninstall bcrypt passlib
#    pip install bcrypt passlib
#    (Y asegúrate de tener la versión adecuada, bcrypt>=4 si usas Python 3.13+)
#
# 3. Reinicia el servidor con Ctrl+C y vuelve a correr uvicorn tras cambios.
#
