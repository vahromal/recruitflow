"""Auth & users API tests."""
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, RECRUITER_EMAIL, RECRUITER_PASSWORD


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_wrong_password(client, admin_user):
    r = client.post(
        "/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": "wrong-password"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_token(client, admin_user):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    r = client.get("/api/auth/me", headers=client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"


def test_login_rate_limit(client, admin_user):
    for _ in range(5):
        client.post(
            "/api/auth/login",
            data={"username": ADMIN_EMAIL, "password": "bad"},
        )
    r = client.post(
        "/api/auth/login",
        data={"username": ADMIN_EMAIL, "password": "bad"},
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_admin_creates_recruiter_and_recruiter_cannot_manage_users(
    client, admin_user, recruiter_user
):
    admin_h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = client.post(
        "/api/users",
        json={
            "email": "new@example.com",
            "full_name": "New Recruiter",
            "password": "StrongPass123",
            "role": "recruiter",
        },
        headers=admin_h,
    )
    assert r.status_code == 201, r.text

    rec_h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    r = client.get("/api/users", headers=rec_h)
    assert r.status_code == 403


def test_duplicate_user_email_rejected(client, admin_user):
    admin_h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    payload = {
        "email": "dup@example.com",
        "full_name": "Dup",
        "password": "StrongPass123",
        "role": "recruiter",
    }
    assert client.post("/api/users", json=payload, headers=admin_h).status_code == 201
    r = client.post("/api/users", json=payload, headers=admin_h)
    assert r.status_code == 409


def test_strong_password_enforced(client, admin_user):
    admin_h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = client.post(
        "/api/users",
        json={"email": "weak@example.com", "full_name": "Weak", "password": "123", "role": "recruiter"},
        headers=admin_h,
    )
    assert r.status_code == 422
