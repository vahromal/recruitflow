"""Candidate, vacancy, pipeline and activity models."""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Stage(str, enum.Enum):
    NEW = "new"
    SCREENING = "screening"
    INTERVIEW_RECRUITER = "interview_recruiter"
    INTERVIEW_CLIENT = "interview_client"
    TEST_TASK = "test_task"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


STAGE_ORDER: list[Stage] = [
    Stage.NEW,
    Stage.SCREENING,
    Stage.INTERVIEW_RECRUITER,
    Stage.INTERVIEW_CLIENT,
    Stage.TEST_TASK,
    Stage.OFFER,
    Stage.HIRED,
    Stage.REJECTED,
]


class JobStatus(str, enum.Enum):
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class ActivityType(str, enum.Enum):
    COMMENT = "comment"
    TASK = "task"
    EVENT = "event"


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    DONE = "done"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[str | None] = mapped_column(String(255))  # должность
    company: Mapped[str | None] = mapped_column(String(255))  # текущая компания
    expected_salary: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str | None] = mapped_column(String(128))
    profile_links: Mapped[list | None] = mapped_column(JSON, default=list)
    telegram: Mapped[str | None] = mapped_column(String(128))
    whatsapp: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    resume_path: Mapped[str | None] = mapped_column(String(1024))
    resume_filename: Mapped[str | None] = mapped_column(String(512))

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    stages: Mapped[list["CandidateStage"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_candidates_email_lower"),
        UniqueConstraint("phone", name="uq_candidates_phone"),
    )


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    client: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.OPEN,
        nullable=False,
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    candidates: Mapped[list["CandidateStage"]] = relationship(
        back_populates="vacancy", cascade="all, delete-orphan", passive_deletes=True
    )


class CandidateStage(Base):
    """Application of a candidate to a vacancy with current stage (kanban card)."""

    __tablename__ = "candidate_stages"
    __table_args__ = (UniqueConstraint("candidate_id", "vacancy_id", name="uq_candidate_vacancy"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[Stage] = mapped_column(
        Enum(Stage, name="stage", values_callable=lambda x: [e.value for e in x]),
        default=Stage.NEW,
        nullable=False,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="stages")
    vacancy: Mapped["Vacancy"] = relationship(back_populates="candidates")
    history: Mapped[list["StageHistory"]] = relationship(
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )


class StageHistory(Base):
    __tablename__ = "stage_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_stages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_stage: Mapped[str | None] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    card: Mapped["CandidateStage"] = relationship(back_populates="history")


class Activity(Base):
    """Comments, tasks and event feed entries."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # task fields
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    task_status: Mapped[TaskStatus | None] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=lambda x: [e.value for e in x])
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="activities")
