from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: int
    is_active: bool


class UserWithRole(UserBase):
    role_name: Optional[str] = None


class UserWithPersonas(UserWithRole):
    personas: List[dict] = []


class UserCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: int = Field(..., ge=1)
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    role_id: Optional[int] = Field(None, ge=1)


class UpdateRoleRequest(BaseModel):
    role_id: int = Field(..., ge=1)
