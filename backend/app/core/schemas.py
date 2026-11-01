"""Shared Pydantic schemas."""
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

# Pydantic's EmailStr (email-validator) REJECTS special-use/reserved domains
# such as ".local", ".test" — which is exactly what self-hosted/internal
# addresses like admin@recruitflow.local look like. Rejecting them turned a
# valid user list into HTTP 500. So we validate the SHAPE only:
#   local-part @ domain . TLD  (no spaces, at least one dot in domain)
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _check_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("Некорректный email: ожидается вид name@domain.tld")
    return value


#: email validated by format only (allows internal/reserved domains)
Email = Annotated[str, AfterValidator(_check_email)]


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
    email: Email
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
    email: Email
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
