"""Shared Pydantic schemas."""
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Page(BaseModel):
    """Standard pagination envelope."""
    items: list
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    detail: str = "ok"


# --- Users ---
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(admin|recruiter)$")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, pattern="^(admin|recruiter)$")
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
