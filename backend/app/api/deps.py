"""Shared FastAPI dependencies: current user from JWT."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Action, check_permission
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": "Invalid or missing token"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = db.scalar(select(User).where(User.id == int(user_id)))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    check_permission(user, Action.MANAGE_USERS)
    return user


def require_recruiter_or_admin(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.RECRUITER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Recruiter or admin required"},
        )
