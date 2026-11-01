"""Candidate service: CRUD, duplicate protection, search/filter, CSV export."""
import csv
import io
import re

from fastapi import HTTPException, status
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.recruiting import Candidate, CandidateStage, Vacancy
from app.models.user import User, UserRole
from app.schemas.candidate import CandidateCreate, CandidateUpdate, DuplicateInfo


def _norm_phone(v: str | None) -> str | None:
    if not v:
        return None
    return "".join(ch for ch in v if ch.isdigit()) or None


def find_duplicates(db: Session, email: str | None, phone: str | None,
                    exclude_id: int | None = None) -> list[DuplicateInfo]:
    result: list[DuplicateInfo] = []
    q = select(Candidate)
    if exclude_id:
        q = q.where(Candidate.id != exclude_id)
    if email:
        row = db.scalar(q.where(func.lower(Candidate.email) == email.lower()))
        if row:
            result.append(
                DuplicateInfo(candidate_id=row.id, full_name=row.full_name, matched_by="email")
            )
    if phone:
        phone_n = _norm_phone(phone)
        row = db.scalar(q.where(Candidate.phone == phone_n))
        if row and not any(d.candidate_id == row.id for d in result):
            result.append(
                DuplicateInfo(candidate_id=row.id, full_name=row.full_name, matched_by="phone")
            )
    return result


def create_candidate(db: Session, payload: CandidateCreate, user: User) -> Candidate:
    email = payload.email.lower() if payload.email else None
    phone = _norm_phone(payload.phone)
    dupes = find_duplicates(db, email, phone)
    if dupes:
        d = dupes[0]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_candidate",
                "message": f"Duplicate candidate exists (matched by {d.matched_by})",
                "details": [dupe.model_dump() for dupe in dupes],
            },
        )
    candidate = Candidate(
        **payload.model_dump(exclude={"email", "phone"}),
        email=email,
        phone=phone,
        owner_id=user.id,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update_candidate(db: Session, candidate: Candidate, payload: CandidateUpdate) -> Candidate:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        data["email"] = data["email"].lower() if data["email"] else None
    if "phone" in data:
        data["phone"] = _norm_phone(data["phone"])
    for field in ("email", "phone"):
        if field in data and data[field]:
            dupes = find_duplicates(db, data[field] if field == "email" else None,
                                    data[field] if field == "phone" else None,
                                    exclude_id=candidate.id)
            if dupes:
                d = dupes[0]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "duplicate_candidate",
                        "message": f"Duplicate candidate exists (matched by {d.matched_by})",
                        "details": [dupe.model_dump() for dupe in dupes],
                    },
                )
    for field, value in data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def _visible_q(user: User):
    """Recruiters see own candidates (+ shared via vacancies? — decided: own only)."""
    q = select(Candidate)
    if user.role != UserRole.ADMIN:
        q = q.where(Candidate.owner_id == user.id)
    return q


def search_candidates(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    city: str | None = None,
    position: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    owner_id: int | None = None,
) -> tuple[list[Candidate], int]:
    stmt = _visible_q(user)
    if owner_id is not None and user.role == UserRole.ADMIN:
        stmt = stmt.where(Candidate.owner_id == owner_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Candidate.full_name.ilike(like),
                Candidate.email.ilike(like),
                Candidate.phone.ilike(like),
                Candidate.position.ilike(like),
                Candidate.company.ilike(like),
                Candidate.city.ilike(like),
            )
        )
    if city:
        stmt = stmt.where(Candidate.city.ilike(f"%{city}%"))
    if position:
        stmt = stmt.where(Candidate.position.ilike(f"%{position}%"))
    if source:
        stmt = stmt.where(Candidate.source.ilike(f"%{source}%"))
    if tag:
        # tags are a JSON list like ["python","senior"]; search inside serialized text
        stmt = stmt.where(cast(Candidate.tags, Text).ilike(f'%"{tag.strip()}"%'))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Candidate.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def export_csv(db: Session, user: User, **filters) -> str:
    rows, _ = search_candidates(db, user, page=1, page_size=100_000, **filters)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id", "full_name", "phone", "email", "city", "position", "company",
            "expected_salary", "source", "telegram", "whatsapp", "tags", "created_at",
        ]
    )
    for c in rows:
        writer.writerow(
            [
                c.id, c.full_name, c.phone or "", c.email or "", c.city or "",
                c.position or "", c.company or "", c.expected_salary or "",
                c.source or "", c.telegram or "", c.whatsapp or "",
                ";".join(c.tags or []), c.created_at.isoformat(),
            ]
        )
    return buf.getvalue()
