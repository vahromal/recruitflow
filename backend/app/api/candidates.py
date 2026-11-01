"""Candidate endpoints: CRUD, search, resume upload, CSV export."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import Action, check_owns_or_admin, check_permission
from app.models.recruiting import Candidate
from app.models.user import User
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetail,
    CandidateOut,
    CandidateUpdate,
    DuplicateInfo,
)
from app.services import candidate_service as svc

router = APIRouter(prefix="/candidates", tags=["candidates"])

ALLOWED_RESUME_EXT = {".pdf", ".docx"}


def _get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Candidate not found"}
        )
    return candidate


@router.get("", response_model=dict)
def list_candidates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    city: str | None = None,
    position: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    owner_id: int | None = None,
) -> dict:
    rows, total = svc.search_candidates(
        db, user, page=page, page_size=page_size,
        q=q, city=city, position=position, source=source, tag=tag, owner_id=owner_id,
    )
    return {
        "items": [CandidateOut.model_validate(r).model_dump() for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export", response_class=PlainTextResponse)
def export_csv(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    q: str | None = None,
    tag: str | None = None,
) -> str:
    check_permission(user, Action.EXPORT_DATA)
    content = svc.export_csv(db, user, q=q, tag=tag)
    return content


@router.get("/duplicates", response_model=list[DuplicateInfo])
def check_duplicates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    email: str | None = None,
    phone: str | None = None,
) -> list[DuplicateInfo]:
    return svc.find_duplicates(db, email, phone)


@router.post("", response_model=CandidateOut, status_code=201)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Candidate:
    check_permission(user, Action.CREATE_CANDIDATE)
    return svc.create_candidate(db, payload, user)


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Candidate:
    candidate = _get_candidate_or_404(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Candidate:
    candidate = _get_candidate_or_404(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    return svc.update_candidate(db, candidate, payload)


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    candidate = _get_candidate_or_404(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    check_permission(user, Action.DELETE_CANDIDATE)
    if candidate.resume_path:
        path = Path(candidate.resume_path)
        if path.is_file() and settings.storage_backend == "local":
            path.unlink(missing_ok=True)
    db.delete(candidate)
    db.commit()


@router.post("/{candidate_id}/resume", response_model=CandidateOut)
async def upload_resume(
    candidate_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Candidate:
    candidate = _get_candidate_or_404(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_RESUME_EXT:
        raise HTTPException(
            status_code=415,
            detail={"code": "unsupported_type", "message": "Only PDF and DOCX files are allowed"},
        )
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={"code": "too_large", "message": f"Max file size {settings.max_upload_size_mb} MB"},
        )

    upload_dir = Path(settings.storage_local_path) / "resumes"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"cand_{candidate_id}_{abs(hash(file.filename))}{suffix}"
    dest = upload_dir / stored_name
    dest.write_bytes(content)

    # remove previous file
    if candidate.resume_path:
        old = Path(candidate.resume_path)
        if old.is_file():
            old.unlink(missing_ok=True)

    candidate.resume_path = str(dest)
    candidate.resume_filename = file.filename
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/{candidate_id}/resume")
def download_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse

    candidate = _get_candidate_or_404(db, candidate_id)
    check_owns_or_admin(user, candidate.owner_id)
    if not candidate.resume_path or not Path(candidate.resume_path).is_file():
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "No resume"})
    return FileResponse(
        candidate.resume_path,
        filename=candidate.resume_filename or "resume",
    )
