"""Dashboard: stage counts, open vacancies, tasks today, recruiter stats."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.recruiting import (
    STAGE_ORDER,
    Activity,
    ActivityType,
    Candidate,
    CandidateStage,
    JobStatus,
    TaskStatus,
    Vacancy,
)
from app.models.user import User, UserRole
from app.schemas.recruiting import DashboardStageCount, RecruiterStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)

    # candidates per stage
    stage_q = select(CandidateStage.stage, func.count(CandidateStage.id)).group_by(
        CandidateStage.stage
    )
    if user.role != UserRole.ADMIN:
        stage_q = stage_q.join(Candidate, CandidateStage.candidate_id == Candidate.id).where(
            Candidate.owner_id == user.id
        )
    counts = {stage: 0 for stage in STAGE_ORDER}
    for stage, count in db.execute(stage_q):
        counts[stage] = count
    stages = [
        DashboardStageCount(stage=s.value, count=counts[s]).model_dump() for s in STAGE_ORDER
    ]

    # open vacancies
    vac_q = select(func.count(Vacancy.id)).where(Vacancy.status == JobStatus.OPEN)
    if user.role != UserRole.ADMIN:
        vac_q = vac_q.where(Vacancy.owner_id == user.id)
    open_vacancies = db.scalar(vac_q) or 0

    # tasks today (open, due <= now)
    task_q = (
        select(func.count(Activity.id))
        .join(Candidate, Activity.candidate_id == Candidate.id)
        .where(
            Activity.type == ActivityType.TASK,
            Activity.task_status == TaskStatus.OPEN,
            Activity.due_at.is_not(None),
            Activity.due_at <= now,
        )
    )
    if user.role != UserRole.ADMIN:
        task_q = task_q.where(Candidate.owner_id == user.id)
    tasks_today = db.scalar(task_q) or 0

    # total candidates
    cand_q = select(func.count(Candidate.id))
    if user.role != UserRole.ADMIN:
        cand_q = cand_q.where(Candidate.owner_id == user.id)
    total_candidates = db.scalar(cand_q) or 0

    # per-recruiter stats (admin sees all, recruiter sees self)
    users_q = select(User)
    if user.role != UserRole.ADMIN:
        users_q = users_q.where(User.id == user.id)
    users = db.scalars(users_q).all()

    stats: list[RecruiterStats] = []
    for u in users:
        cand_count = db.scalar(
            select(func.count(Candidate.id)).where(Candidate.owner_id == u.id)
        ) or 0
        hired = db.scalar(
            select(func.count(CandidateStage.id))
            .join(Candidate, CandidateStage.candidate_id == Candidate.id)
            .where(Candidate.owner_id == u.id, CandidateStage.stage == "hired")
        ) or 0
        rejected = db.scalar(
            select(func.count(CandidateStage.id))
            .join(Candidate, CandidateStage.candidate_id == Candidate.id)
            .where(Candidate.owner_id == u.id, CandidateStage.stage == "rejected")
        ) or 0
        open_vac = db.scalar(
            select(func.count(Vacancy.id)).where(
                Vacancy.owner_id == u.id, Vacancy.status == JobStatus.OPEN
            )
        ) or 0
        stats.append(
            RecruiterStats(
                user_id=u.id, full_name=u.full_name, candidates=cand_count,
                hired=hired, rejected=rejected, open_vacancies=open_vac,
            )
        )

    return {
        "stages": stages,
        "open_vacancies": open_vacancies,
        "tasks_today": tasks_today,
        "total_candidates": total_candidates,
        "recruiter_stats": [s.model_dump() for s in stats],
    }
