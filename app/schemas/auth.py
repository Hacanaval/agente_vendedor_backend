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
    empresa_id: Optional[int] = None
    empresa: Optional[EmpresaCreate] = None

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
    rol: str
    empresa_id: int

    class Config:
        orm_mode = True 