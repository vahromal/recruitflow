"""Seed dev data: admin + recruiter + demo vacancies/candidates/board.

Run: python -m app.seed   (ONLY for development; never in prod compose)
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.recruiting import (  # noqa: E402
    Activity,
    ActivityType,
    Candidate,
    CandidateStage,
    Stage,
    StageHistory,
    TaskStatus,
    Vacancy,
)
from app.models.user import User, UserRole  # noqa: E402


def main() -> None:
    if settings.environment == "prod":
        print("REFUSED: seed is dev-only (ENVIRONMENT=prod)")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Seed skipped: users already exist")
            return

        admin = User(
            email="admin@recruitflow.local",
            full_name="Администратор",
            hashed_password=hash_password("Admin1234!"),
            role=UserRole.ADMIN,
        )
        recruiter = User(
            email="recruiter@recruitflow.local",
            full_name="Рита Рекрутер",
            hashed_password=hash_password("Recruiter123!"),
            role=UserRole.RECRUITER,
        )
        db.add_all([admin, recruiter])
        db.flush()

        v1 = Vacancy(
            title="Middle Python Developer",
            client="ООО «Рога и Копыта»",
            description="Разработка внутренних сервисов на FastAPI",
            requirements="Python, FastAPI, PostgreSQL, Docker",
            salary_min=180000, salary_max=260000, owner_id=recruiter.id,
        )
        v2 = Vacancy(
            title="Frontend React Developer",
            client="Стартап Искра",
            description="Кабинет пользователя на React + TypeScript",
            requirements="React, TypeScript, Vite",
            salary_min=200000, salary_max=300000, owner_id=recruiter.id, status="paused",
        )
        db.add_all([v1, v2])
        db.flush()

        demo = [
            ("Иван Иванов", "ivan@example.com", "79991234567", "Москва", "Python Developer", Stage.NEW),
            ("Пётр Петров", "petr@example.com", "79991112233", "Москва", "Python Developer", Stage.SCREENING),
            ("Анна Смирнова", "anna@example.com", "79992223344", "Казань", "Python Developer", Stage.INTERVIEW_RECRUITER),
            ("Олег Олегов", "oleg@example.com", "79993334455", "Тверь", "Python Developer", Stage.OFFER),
            ("Мария Павлова", "maria@example.com", "79994445566", "Санкт-Петербург", "Python Developer", Stage.HIRED),
            ("Дарья Кузнецова", "darya@example.com", "79995556677", "Москва", "Python Developer", Stage.REJECTED),
        ]
        for name, email, phone, city, position, stage in demo:
            c = Candidate(
                full_name=name, email=email, phone=phone, city=city, position=position,
                company="Acme", expected_salary=240000, source="hh.ru",
                tags=["python"], owner_id=recruiter.id, notes="Демо-данные",
            )
            db.add(c)
            db.flush()
            card = CandidateStage(candidate_id=c.id, vacancy_id=v1.id, stage=stage)
            db.add(card)
            db.flush()
            db.add(StageHistory(
                card_id=card.id, from_stage=None, to_stage=stage.value,
                author_id=recruiter.id, comment="демо",
            ))
            if stage == Stage.REJECTED:
                card.reject_reason = "Не подошёл профиль"

        first_candidate = db.query(Candidate).first()
        db.add(Activity(
            candidate_id=first_candidate.id, type=ActivityType.COMMENT,
            body="Демо-комментарий: кандидат на связи.", author_id=recruiter.id,
        ))
        db.add(Activity(
            candidate_id=first_candidate.id, type=ActivityType.TASK,
            body="Позвонить кандидату", due_at=datetime.now(timezone.utc) - timedelta(hours=1),
            task_status=TaskStatus.OPEN, author_id=recruiter.id,
        ))

        db.commit()
        print("Seed OK:")
        print("  admin:     admin@recruitflow.local / Admin1234!")
        print("  recruiter: recruiter@recruitflow.local / Recruiter123!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
