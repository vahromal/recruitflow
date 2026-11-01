"""Activities: comments, tasks/reminders, event feed."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import check_owns_or_admin
from app.models.recruiting import Activity, ActivityType, Candidate, TaskStatus
from app.models.user import User
from app.schemas.recruiting import ActivityOut, CommentCreate, TaskCreate, TaskUpdate

router = APIRouter(tags=["activities"])


def _get_candidate(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Candidate not found"})
    return candidate


@router.get("/candidates/{candidate_id}/activities", response_model=list[ActivityOut])
def list_activities(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[Activity]:
    candidate = _get_candidate(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    stmt = select(Activity).where(Activity.candidate_id == candidate_id)
    if type:
        stmt = stmt.where(Activity.type == ActivityType(type))
    return list(
        db.scalars(
            stmt.order_by(Activity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )


@router.post("/candidates/{candidate_id}/comments", response_model=ActivityOut, status_code=201)
def add_comment(
    candidate_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Activity:
    candidate = _get_candidate(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    activity = Activity(
        candidate_id=candidate_id,
        type=ActivityType.COMMENT,
        body=payload.body,
        author_id=user.id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.post("/candidates/{candidate_id}/tasks", response_model=ActivityOut, status_code=201)
def create_task(
    candidate_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Activity:
    candidate = _get_candidate(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    activity = Activity(
        candidate_id=candidate_id,
        type=ActivityType.TASK,
        body=payload.body,
        due_at=payload.due_at,
        task_status=TaskStatus.OPEN,
        author_id=user.id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.patch("/tasks/{task_id}", response_model=ActivityOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Activity:
    task = db.get(Activity, task_id)
    if task is None or task.type != ActivityType.TASK:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Task not found"})
    candidate = db.get(Candidate, task.candidate_id)
    check_owns_or_admin(user, candidate.owner_id if candidate else None)
    data = payload.model_dump(exclude_unset=True)
    if "task_status" in data and data["task_status"] is not None:
        data["task_status"] = TaskStatus(data["task_status"])
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/today", response_model=list[ActivityOut])
def tasks_today(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Activity]:
    """Open tasks due today or overdue, visible to the user."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Activity)
        .join(Candidate, Activity.candidate_id == Candidate.id)
        .where(
            Activity.type == ActivityType.TASK,
            Activity.task_status == TaskStatus.OPEN,
            Activity.due_at.is_not(None),
            Activity.due_at <= now,
        )
    )
    if user.role.value != "admin":
        stmt = stmt.where(Candidate.owner_id == user.id)
    return list(db.scalars(stmt.order_by(Activity.due_at).limit(100)).all())


@router.get("/feed", response_model=list[ActivityOut])
def event_feed(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> list[Activity]:
    """Latest events (comments + tasks) across visible candidates."""
    stmt = select(Activity).join(Candidate, Activity.candidate_id == Candidate.id)
    if user.role.value != "admin":
        stmt = stmt.where(Candidate.owner_id == user.id)
    return list(
        db.scalars(
            stmt.order_by(Activity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
