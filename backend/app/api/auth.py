"""Auth endpoints: login (rate-limited) and current user profile."""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import Token
from app.core.security import create_access_token, verify_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory login attempt limiter (per IP+email). Resets on restart.
_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str) -> None:
    now = time.monotonic()
    window = settings.login_rate_limit_seconds
    _attempts[key] = [t for t in _attempts[key] if now - t < window]
    if len(_attempts[key]) >= settings.login_rate_limit_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many login attempts. Try again later.",
            },
        )


def _record_failure(key: str) -> None:
    _attempts[key].append(time.monotonic())


@router.post("/login", response_model=Token, tags=["auth"])
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    key = f"{form.username.lower()}"
    _check_rate_limit(key)
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        _record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "inactive", "message": "Account is deactivated"},
        )
    _attempts.pop(key, None)
    token = create_access_token(str(user.id))
    return Token(access_token=token, token_type="bearer")


@router.get("/me", tags=["auth"])
def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
    }
