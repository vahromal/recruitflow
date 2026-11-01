"""Pydantic schemas for candidates."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_phone(v: str | None) -> str | None:
    """Store phones as digits only (no '+'): makes duplicate matching reliable."""
    if v is None:
        return None
    digits = "".join(ch for ch in v if ch.isdigit())
    return digits or None


class CandidateBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    expected_salary: int | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=128)
    profile_links: list[str] = Field(default_factory=list)
    telegram: str | None = Field(default=None, max_length=128)
    whatsapp: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("phone", "whatsapp", mode="before")
    @classmethod
    def _norm_phone(cls, v):
        return normalize_phone(v) if v else v


class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    expected_salary: int | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=128)
    profile_links: list[str] | None = None
    telegram: str | None = Field(default=None, max_length=128)
    whatsapp: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    tags: list[str] | None = None

    @field_validator("phone", "whatsapp", mode="before")
    @classmethod
    def _norm_phone(cls, v):
        return normalize_phone(v) if v else v


class CandidateOut(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    resume_filename: str | None = None
    created_at: datetime
    updated_at: datetime


class CandidateDetail(CandidateOut):
    stages: list["CardOut"] = Field(default_factory=list)
    activities: list["ActivityOut"] = Field(default_factory=list)


class DuplicateInfo(BaseModel):
    candidate_id: int
    full_name: str
    matched_by: str  # "email" | "phone"


# Resolve forward references (CardOut/ActivityOut live in the recruiting schemas).
from app.schemas.recruiting import ActivityOut, CardOut  # noqa: E402,F811

CandidateDetail.model_rebuild()
