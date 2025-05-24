from pydantic import BaseModel, EmailStr, constr
from typing import Optional

class EmpresaCreate(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str
    logo_url: Optional[str] = None

class UsuarioRegister(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str
    password: constr(min_length=6)

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    telefono: str

    class Config:
        orm_mode = True 