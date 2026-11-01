"""Regression: EmailStr from pydantic rejects reserved domains (.local, .test).

That made GET /api/users answer HTTP 500 for our own demo accounts
(admin@recruitflow.local), because response serialization re-validated emails.
The app must accept any syntactically valid address, including internal ones.
"""
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, RECRUITER_EMAIL, RECRUITER_PASSWORD


def test_users_list_returns_local_domain_emails(client, admin_user, recruiter_user):
    """The exact failing call from the UI: list users containing *.local addresses."""
    h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)  # admin@test.local
    r = client.get("/api/users", headers=h)
    assert r.status_code == 200, r.text
    emails = {u["email"] for u in r.json()}
    assert ADMIN_EMAIL in emails          # ".local" used to trigger 500
    assert RECRUITER_EMAIL in emails


def test_create_and_read_user_with_local_domain(client, admin_user):
    h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = client.post(
        "/api/users",
        json={"email": "it@corp.local", "full_name": "Локальный",
              "password": "StrongPass123", "role": "recruiter"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    r = client.get("/api/users", headers=h)
    assert r.status_code == 200
    assert "it@corp.local" in {u["email"] for u in r.json()}


def test_candidate_with_local_domain_roundtrip(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    r = client.post(
        "/api/candidates",
        json={"full_name": "Локальный Кандидат", "email": "dev@company.local"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = client.get("/api/candidates", headers=h)      # list serialization
    assert r.status_code == 200, r.text
    assert "dev@company.local" in {c["email"] for c in r.json()["items"]}

    r = client.get(f"/api/candidates/{cid}", headers=h)  # detail serialization
    assert r.status_code == 200
    assert r.json()["email"] == "dev@company.local"


def test_malformed_email_still_rejected(client, admin_user):
    h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = client.post(
        "/api/users",
        json={"email": "не-почта", "full_name": "X", "password": "StrongPass123",
              "role": "recruiter"},
        headers=h,
    )
    assert r.status_code == 422
    r = client.post(
        "/api/candidates",
        json={"full_name": "X", "email": "spaces in@mail.com"},
        headers=h,
    )
    assert r.status_code == 422
