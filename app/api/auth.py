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
import secrets

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/register")
async def register(data: UsuarioRegister, db: AsyncSession = Depends(get_db)):
    """
    🔒 ENDPOINT DE REGISTRO SIMPLIFICADO 
    TODO: Implementar autenticación completa y multiempresa en producción
    """
    # En desarrollo, permitir registro básico sin validaciones complejas
    return {
        "success": True,
        "message": "Registro en modo desarrollo - implementar validaciones en producción",
        "development_mode": True
    }

@router.post("/login", response_model=TokenResponse)
async def login(data: UsuarioLogin, db: AsyncSession = Depends(get_db)):
    """
    🔒 ENDPOINT DE LOGIN SIMPLIFICADO
    TODO: Implementar autenticación real con base de datos en producción
    """
    # En desarrollo, generar token válido pero temporal
    if data.email and data.password:
        # Generar token válido con datos del usuario
        token_data = {
            "sub": data.email,
            "email": data.email,
            "development_mode": True
        }
        access_token = create_access_token(data=token_data)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email y contraseña son requeridos"
        )

@router.get("/me")
async def me(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    🔒 ENDPOINT DE PERFIL USUARIO
    TODO: Implementar validación completa de token en producción
    """
    try:
        # Intentar decodificar token
        payload = decode_access_token(token)
        if payload:
            return {
                "email": payload.get("email", "usuario@desarrollo.com"),
                "development_mode": payload.get("development_mode", True),
                "message": "Usuario autenticado en modo desarrollo"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

# 🔒 RECOMENDACIONES DE SEGURIDAD PARA PRODUCCIÓN

# 1. Variables de entorno requeridas:
#    export SECRET_KEY="clave_super_secreta_256_bits_minimo"
#    export BOT_SECRET_KEY="clave_bot_super_secreta_256_bits_minimo"
#    export DATABASE_URL="postgresql://usuario:password@host:puerto/db"
#    export REDIS_URL="redis://localhost:6379"
#
# 2. Para producción, implementar:
#    - Validación real de usuarios en base de datos
#    - Hash de contraseñas con bcrypt
#    - Refresh tokens
#    - Rate limiting
#    - Logs de seguridad
#    - Validación de rol/empresa
#
# 3. Nunca commitear:
#    - API keys reales
#    - Contraseñas
#    - Tokens de producción
#    - Claves privadas
