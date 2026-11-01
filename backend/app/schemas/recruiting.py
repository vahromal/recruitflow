"""Pydantic schemas for vacancies, pipeline cards and activities."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.recruiting import Stage


class VacancyBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=255)
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    status: str = Field(default="open", pattern="^(open|paused|closed)$")


class VacancyCreate(VacancyBase):
    pass


class VacancyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=255)
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern="^(open|paused|closed)$")


class VacancyOut(VacancyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


# --- Pipeline cards ---

class CardCreate(BaseModel):
    candidate_id: int
    vacancy_id: int


class CardMove(BaseModel):
    stage: str
    reject_reason: str | None = None
    comment: str | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_stage: str | None
    to_stage: str
    comment: str | None
    author_id: int | None
    created_at: datetime


class CandidateBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    position: str | None = None
    expected_salary: int | None = None
    tags: list[str] = Field(default_factory=list)


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    vacancy_id: int
    stage: str
    reject_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    candidate: CandidateBrief | None = None
    history: list[HistoryOut] = Field(default_factory=list)


# --- Activities ---

class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class TaskCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=1000)
    due_at: datetime | None = None
    task_status: str | None = Field(default=None, pattern="^(open|done)$")


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    type: str
    body: str
    due_at: datetime | None = None
    task_status: str | None = None
    author_id: int | None = None
    created_at: datetime


class DashboardStageCount(BaseModel):
    stage: str
    count: int


class RecruiterStats(BaseModel):
    user_id: int
    full_name: str
    candidates: int
    hired: int
    rejected: int
    open_vacancies: int
