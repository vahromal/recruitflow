"""GDPR endpoints: data export (portability) and erasure of a candidate."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Action, check_owns_or_admin, check_permission
from app.models.recruiting import Activity, Candidate, CandidateStage, StageHistory
from app.models.user import User
from app.schemas.candidate import CandidateOut

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


@router.get("/candidates/{candidate_id}/export")
def export_candidate_data(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Right to portability: everything we store about the candidate."""
    check_permission(user, Action.GDPR_EXPORT)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Candidate not found"})
    check_owns_or_admin(user, candidate.owner_id)

    activities = db.scalars(select(Activity).where(Activity.candidate_id == candidate_id)).all()
    cards = db.scalars(select(CandidateStage).where(CandidateStage.candidate_id == candidate_id)).all()
    card_ids = [c.id for c in cards]
    history = (
        db.scalars(select(StageHistory).where(StageHistory.card_id.in_(card_ids))).all()
        if card_ids
        else []
    )

    payload = {
        "candidate": CandidateOut.model_validate(candidate).model_dump(mode="json"),
        "activities": [
            {
                "type": a.type.value,
                "body": a.body,
                "due_at": a.due_at.isoformat() if a.due_at else None,
                "task_status": a.task_status.value if a.task_status else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
        "pipeline": [
            {"vacancy_id": c.vacancy_id, "stage": c.stage.value, "reject_reason": c.reject_reason}
            for c in cards
        ],
        "stage_history": [
            {
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "comment": h.comment,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ],
    }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="candidate_{candidate_id}_gdpr_export.json"'
        },
    )


@router.delete("/candidates/{candidate_id}", status_code=204)
def erase_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Right to erasure: remove candidate with all personal data."""
    check_permission(user, Action.GDPR_DELETE)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Candidate not found"})
    check_owns_or_admin(user, candidate.owner_id)
    db.delete(candidate)  # cascade removes stages/history/activities
    db.commit()
