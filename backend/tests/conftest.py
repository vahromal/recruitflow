"""Test fixtures.

- Uses a separate test database (default: recruitflow_test).
- Recreates it from scratch and applies real Alembic migrations, so tests
  always verify migrations on a clean database.
- Clears tables between tests; keeps schema.
"""
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # alembic.ini & .env live here

# --- configure test DB BEFORE importing the app ---
TEST_DB = os.environ.get("TEST_DATABASE_NAME", "recruitflow_test")
PG_USER = os.environ.get("POSTGRES_USER", "recruitflow")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "recruitflow_dev_password")
PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "POSTGRES_DB": TEST_DB,
        "POSTGRES_USER": PG_USER,
        "POSTGRES_PASSWORD": PG_PASSWORD,
        "POSTGRES_HOST": PG_HOST,
        "POSTGRES_PORT": PG_PORT,
        "STORAGE_LOCAL_PATH": "/tmp/recruitflow_test_uploads",
        "SECRET_KEY": "test-secret-key-not-for-production",
    }
)

import sqlalchemy as sa  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
settings = get_settings()

ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "AdminPass123!"
RECRUITER_EMAIL = "recruiter@test.local"
RECRUITER_PASSWORD = "RecruiterPass123!"


def _recreate_test_database() -> None:
    """Drop & create test DB, then apply migrations on the clean database."""
    server_url = (
        f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"
    )
    server_engine = sa.create_engine(server_url, isolation_level="AUTOCOMMIT")
    with server_engine.connect() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB},
        ).scalar()
        if exists:
            conn.execute(sa.text(f'DROP DATABASE "{TEST_DB}" WITH (FORCE)'))
        conn.execute(sa.text(f'CREATE DATABASE "{TEST_DB}"'))
    server_engine.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def test_database():
    _recreate_test_database()
    yield
    # test DB is dropped on the next run; nothing to clean up


@pytest.fixture(scope="session")
def engine():
    from app.core.database import engine as app_engine

    yield app_engine
    app_engine.dispose()


@pytest.fixture(autouse=True)
def reset_login_rate_limiter():
    """In-memory rate limiter must not leak between tests."""
    from app.api import auth as auth_module

    auth_module._attempts.clear()
    yield
    auth_module._attempts.clear()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    """Truncate all tables between tests (keeps schema & sequences)."""
    from app.core.database import Base

    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


def _create_user(db, email: str, password: str, full_name: str, role: str):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=UserRole(role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user():
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        yield _create_user(db, ADMIN_EMAIL, ADMIN_PASSWORD, "Admin", "admin")


@pytest.fixture
def recruiter_user():
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        yield _create_user(db, RECRUITER_EMAIL, RECRUITER_PASSWORD, "Rita Recruiter", "recruiter")


@pytest.fixture
def client():
    """HTTP client with auth helper."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        c.login = lambda email, password: c.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()["access_token"]
        c.auth_headers = lambda email, password: {
            "Authorization": f"Bearer {c.login(email, password)}"
        }
        yield c
