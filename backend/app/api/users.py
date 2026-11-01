"""Admin user management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.core.schemas import UserCreate, UserOut, UserUpdate
from app.core.security import hash_password
from app.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
    page: int = 1,
    page_size: int = 50,
) -> list[User]:
    rows = db.scalars(
        select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return rows


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> User:
    exists = db.scalar(select(User).where(User.email == payload.email.lower()))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate", "message": "User with this email already exists"},
        )
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole(payload.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "User not found"})
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.hashed_password = hash_password(data.pop("password"))
    if "role" in data and data["role"] is not None:
        user.role = UserRole(data["role"])
        data.pop("role")
    for field, value in data.items():
        setattr(user, field, value)
    if not user.is_active and user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail={"code": "cannot_deactivate_self", "message": "You cannot deactivate yourself"},
        )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "User not found"})
    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail={"code": "cannot_delete_self", "message": "You cannot delete yourself"},
        )
    db.delete(user)
    db.commit()
