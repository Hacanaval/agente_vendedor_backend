from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# Configuración de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de JWT
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY", "BOT_SECRET_KEY")  # Clave fija para el token del bot
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if data.get("email") == "bot@sextinvalle.com":
        # Para el bot, se genera un token fijo (sin exp) y se agrega un campo 'bot' en el payload.
        to_encode.update({"bot": True})
    else:
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        # Decodificar con SECRET_KEY (tanto para tokens normales como para el token fijo del bot)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        # Si el payload contiene el campo 'bot', se ignora la expiración (es un token fijo del bot)
        if payload.get("bot") is True:
            return payload
        # Para tokens normales, se verifica exp (se lanza JWTError si exp ha expirado)
        if "exp" in payload:
            exp = payload["exp"]
            if exp < datetime.utcnow().timestamp():
                 raise JWTError("Token expirado")
        return payload
    except JWTError:
         return None 