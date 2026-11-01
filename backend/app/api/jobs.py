"""Vacancy endpoints + kanban pipeline cards (stage moves with history)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import check_owns_or_admin
from app.models.recruiting import (
    STAGE_ORDER,
    Candidate,
    CandidateStage,
    JobStatus,
    Stage,
    StageHistory,
    Vacancy,
)
from app.models.user import User, UserRole
from app.schemas.recruiting import (
    CardCreate,
    CardMove,
    CardOut,
    VacancyCreate,
    VacancyOut,
    VacancyUpdate,
)

router = APIRouter(tags=["vacancies"])


def _get_vacancy_or_404(db: Session, vacancy_id: int) -> Vacancy:
    row = db.get(Vacancy, vacancy_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Vacancy not found"})
    return row


def _visible_vacancy_q(user: User):
    q = select(Vacancy)
    if user.role != UserRole.ADMIN:
        q = q.where(Vacancy.owner_id == user.id)
    return q


# --- Vacancies ---

@router.get("/vacancies", response_model=dict)
def list_vacancies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    q: str | None = None,
) -> dict:
    stmt = _visible_vacancy_q(user)
    if status:
        stmt = stmt.where(Vacancy.status == JobStatus(status))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Vacancy.title.ilike(like) | Vacancy.client.ilike(like))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Vacancy.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [VacancyOut.model_validate(r).model_dump() for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/vacancies", response_model=VacancyOut, status_code=201)
def create_vacancy(
    payload: VacancyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Vacancy:
    vacancy = Vacancy(**payload.model_dump(), owner_id=user.id)
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.get("/vacancies/{vacancy_id}", response_model=VacancyOut)
def get_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Vacancy:
    vacancy = _get_vacancy_or_404(db, vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id)
    return vacancy


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyOut)
def update_vacancy(
    vacancy_id: int,
    payload: VacancyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Vacancy:
    vacancy = _get_vacancy_or_404(db, vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "status" and value is not None:
            value = JobStatus(value)
        setattr(vacancy, field, value)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.delete("/vacancies/{vacancy_id}", status_code=204)
def delete_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    vacancy = _get_vacancy_or_404(db, vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id)
    db.delete(vacancy)
    db.commit()


# --- Pipeline / kanban ---

@router.get("/vacancies/{vacancy_id}/board", response_model=dict)
def get_board(
    vacancy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    vacancy = _get_vacancy_or_404(db, vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id)
    cards = db.scalars(
        select(CandidateStage)
        .where(CandidateStage.vacancy_id == vacancy_id)
        .options(
            selectinload(CandidateStage.candidate),
            selectinload(CandidateStage.history),
        )
    ).all()
    board: dict[str, list] = {stage.value: [] for stage in STAGE_ORDER}
    for card in cards:
        board[card.stage.value].append(CardOut.model_validate(card).model_dump())
    return {"vacancy_id": vacancy_id, "stages": board}


@router.post("/vacancies/{vacancy_id}/cards", response_model=CardOut, status_code=201)
def add_card(
    vacancy_id: int,
    payload: CardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateStage:
    vacancy = _get_vacancy_or_404(db, vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id)
    candidate = db.get(Candidate, payload.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Candidate not found"})
    existing = db.scalar(
        select(CandidateStage).where(
            CandidateStage.candidate_id == payload.candidate_id,
            CandidateStage.vacancy_id == vacancy_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "already_on_board", "message": "Candidate already in this vacancy pipeline"},
        )
    card = CandidateStage(candidate_id=payload.candidate_id, vacancy_id=vacancy_id)
    db.add(card)
    db.flush()
    db.add(
        StageHistory(
            card_id=card.id, from_stage=None, to_stage=Stage.NEW.value,
            author_id=user.id, comment="Кандидат добавлен в воронку",
        )
    )
    db.commit()
    db.refresh(card)
    return card


@router.post("/cards/{card_id}/move", response_model=CardOut)
def move_card(
    card_id: int,
    payload: CardMove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateStage:
    card = db.scalar(
        select(CandidateStage)
        .where(CandidateStage.id == card_id)
        .options(
            selectinload(CandidateStage.candidate),
            selectinload(CandidateStage.history),
        )
    )
    if card is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Card not found"})
    vacancy = db.get(Vacancy, card.vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id if vacancy else None)

    try:
        new_stage = Stage(payload.stage)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "bad_stage", "message": f"Unknown stage '{payload.stage}'"},
        )

    if new_stage == Stage.REJECTED and not payload.reject_reason:
        raise HTTPException(
            status_code=422,
            detail={"code": "reject_reason_required", "message": "Reject reason is required"},
        )

    old_stage = card.stage
    card.stage = new_stage
    card.reject_reason = payload.reject_reason if new_stage == Stage.REJECTED else None
    db.add(
        StageHistory(
            card_id=card.id,
            from_stage=old_stage.value,
            to_stage=new_stage.value,
            comment=payload.comment or (payload.reject_reason if new_stage == Stage.REJECTED else None),
            author_id=user.id,
        )
    )
    db.commit()
    db.refresh(card)
    return card


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(
    card_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateStage:
    card = db.scalar(
        select(CandidateStage)
        .where(CandidateStage.id == card_id)
        .options(
            selectinload(CandidateStage.candidate),
            selectinload(CandidateStage.history),
        )
    )
    if card is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Card not found"})
    vacancy = db.get(Vacancy, card.vacancy_id)
    check_owns_or_admin(user, vacancy.owner_id if vacancy else None)
    return card
