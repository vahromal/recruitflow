"""Central place for roles and permission rules.

Roles:
- admin: full access, manages users.
- recruiter: works with own candidates/vacancies and everything created by them.

Rule of thumb: object-level ownership checks live here so that changing the
access model in one place affects the whole app.
"""
from enum import Enum

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole


class Action(str, Enum):
    MANAGE_USERS = "manage_users"
    VIEW_ALL_DATA = "view_all_data"
    CREATE_CANDIDATE = "create_candidate"
    EXPORT_DATA = "export_data"
    DELETE_CANDIDATE = "delete_candidate"
    GDPR_EXPORT = "gdpr_export"
    GDPR_DELETE = "gdpr_delete"


# role -> set of allowed actions
ROLE_PERMISSIONS: dict[UserRole, set[Action]] = {
    UserRole.ADMIN: {
        Action.MANAGE_USERS,
        Action.VIEW_ALL_DATA,
        Action.CREATE_CANDIDATE,
        Action.EXPORT_DATA,
        Action.DELETE_CANDIDATE,
        Action.GDPR_EXPORT,
        Action.GDPR_DELETE,
    },
    UserRole.RECRUITER: {
        Action.CREATE_CANDIDATE,
        Action.EXPORT_DATA,
        Action.DELETE_CANDIDATE,  # may delete own candidates (incl. GDPR requests)
        Action.GDPR_EXPORT,
        Action.GDPR_DELETE,
    },
}


def has_permission(user: User, action: Action) -> bool:
    return action in ROLE_PERMISSIONS.get(user.role, set())


def check_permission(user: User, action: Action) -> None:
    if not has_permission(user, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Insufficient permissions"},
        )


def check_owns_or_admin(user: User, owner_id) -> None:
    """Allow if user is admin or the object belongs to the user."""
    if user.role == UserRole.ADMIN:
        return
    if user.id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Not your object"},
        )


# --- FastAPI dependencies ---

def get_current_user(db: Session = Depends(get_db)) -> User | None:
    """Placeholder; real implementation lives in app/api/deps.py (JWT auth)."""
    raise NotImplementedError
