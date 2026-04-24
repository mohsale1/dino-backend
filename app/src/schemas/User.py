from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PHONE_PATTERN = r'^\+?[0-9\s\-\(\)]{7,30}$'


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=30, pattern=PHONE_PATTERN)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_id: int
    persona_ids: Optional[List[int]] = None



class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=30, pattern=PHONE_PATTERN)
    password: Optional[str] = Field(None, min_length=8)
    role_id: Optional[int] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_type: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role_id: int
    workspace_id: Optional[int] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role: Optional[dict] = None
    persona_ids: Optional[List[int]] = None
