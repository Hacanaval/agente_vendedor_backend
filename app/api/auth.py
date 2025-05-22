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

# Dependency para obtener usuario autenticado
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # *** SOLUCIÓN CLAVE: cerrar la transacción de lectura ***
    await db.commit()

    return user

@router.post("/register", response_model=TokenResponse)
async def register(data: UsuarioRegister, db: AsyncSession = Depends(get_db)):
    if data.empresa_id:
        empresa = await db.get(Empresa, data.empresa_id)
        if not empresa:
            raise HTTPException(status_code=400, detail="Empresa no encontrada")
        rol = "vendedor"
    elif data.empresa:
        empresa = Empresa(
            nombre=data.empresa.nombre,
            email=data.empresa.email,
            telefono=data.empresa.telefono,
            logo_url=data.empresa.logo_url
        )
        db.add(empresa)
        await db.flush()
        rol = "admin"
    else:
        raise HTTPException(status_code=400, detail="Datos de empresa requeridos")
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    usuario = Usuario(
        empresa_id=empresa.id,
        nombre=data.nombre,
        email=data.email,
        telefono=data.telefono,
        rol=rol,
        password_hash=hash_password(data.password),
        activo=True
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    token = create_access_token({
        "user_id": usuario.id,
        "empresa_id": usuario.empresa_id,
        "rol": usuario.rol,
        "email": usuario.email
    })
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
async def login(data: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({
        "user_id": usuario.id,
        "empresa_id": usuario.empresa_id,
        "rol": usuario.rol,
        "email": usuario.email
    })
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UsuarioOut)
async def me(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Si por algún motivo tu función de /me hace queries adicionales, podría requerir commit, pero aquí no debería.
    # await db.commit()  # Usualmente innecesario aquí, pero puedes dejarlo si tienes queries de lectura
    return current_user

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
