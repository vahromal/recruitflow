"""Candidate API tests: CRUD, duplicates, search, CSV export, resume upload."""
import io

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, RECRUITER_EMAIL, RECRUITER_PASSWORD


CANDIDATE = {
    "full_name": "Иван Иванов",
    "phone": "+7 999 123-45-67",
    "email": "ivan@example.com",
    "city": "Москва",
    "position": "Python Developer",
    "company": "Acme",
    "expected_salary": 250000,
    "source": "hh.ru",
    "telegram": "@ivan_dev",
    "whatsapp": "+79991234567",
    "notes": "Опыт 5 лет",
    "tags": ["python", "senior"],
}


def test_create_and_get_candidate(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    r = client.post("/api/candidates", json=CANDIDATE, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    cid = body["id"]
    # phone normalized: digits only
    assert body["phone"] == "79991234567"

    r = client.get(f"/api/candidates/{cid}", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "ivan@example.com"


def test_duplicate_email_rejected(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    assert client.post("/api/candidates", json=CANDIDATE, headers=h).status_code == 201
    dup = dict(CANDIDATE, email="IVAN@example.com", phone="+7 900 000 00 00")
    r = client.post("/api/candidates", json=dup, headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_candidate"


def test_duplicate_phone_rejected(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    assert client.post("/api/candidates", json=CANDIDATE, headers=h).status_code == 201
    dup = dict(CANDIDATE, email="other@example.com", phone="79991234567")
    r = client.post("/api/candidates", json=dup, headers=h)
    assert r.status_code == 409


def test_update_candidate(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    cid = client.post("/api/candidates", json=CANDIDATE, headers=h).json()["id"]
    r = client.patch(f"/api/candidates/{cid}", json={"city": "Казань"}, headers=h)
    assert r.status_code == 200
    assert r.json()["city"] == "Казань"


def test_search_filters(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    client.post(
        "/api/candidates",
        json=dict(CANDIDATE, full_name="Пётр Петров", email="petr@example.com",
                  phone="+79991112233", city="Тверь", tags=["java"]),
        headers=h,
    )
    client.post("/api/candidates", json=CANDIDATE, headers=h)

    r = client.get("/api/candidates?q=Пётр", headers=h)
    assert r.json()["total"] == 1

    r = client.get("/api/candidates?city=Тверь", headers=h)
    assert r.json()["total"] == 1

    r = client.get("/api/candidates?tag=python", headers=h)
    assert r.json()["total"] == 1

    r = client.get("/api/candidates?page_size=1", headers=h)
    assert len(r.json()["items"]) == 1
    assert r.json()["total"] == 2


def test_recruiter_sees_only_own(client, recruiter_user, admin_user):
    rec_h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    adm_h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    client.post("/api/candidates", json=CANDIDATE, headers=rec_h)

    # admin creates own candidate
    client.post(
        "/api/candidates",
        json=dict(CANDIDATE, full_name="Admin Cand", email="adminc@example.com",
                  phone="+79990001122"),
        headers=adm_h,
    )
    r = client.get("/api/candidates", headers=rec_h)
    assert r.json()["total"] == 1
    r = client.get("/api/candidates", headers=adm_h)
    assert r.json()["total"] == 2


def test_recruiter_cannot_edit_foreign_candidate(client, recruiter_user, admin_user):
    rec_h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    adm_h = client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD)
    cid = client.post(
        "/api/candidates",
        json=dict(CANDIDATE, email="adminown@example.com", phone="+79993334455"),
        headers=adm_h,
    ).json()["id"]
    r = client.patch(f"/api/candidates/{cid}", json={"city": "Хак"}, headers=rec_h)
    assert r.status_code == 403


def test_csv_export(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    client.post("/api/candidates", json=CANDIDATE, headers=h)
    r = client.get("/api/candidates/export", headers=h)
    assert r.status_code == 200
    text = r.text
    assert "full_name" in text.splitlines()[0]
    assert "Иван Иванов" in text


def test_resume_upload_and_download(client, recruiter_user, tmp_path):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    cid = client.post("/api/candidates", json=CANDIDATE, headers=h).json()["id"]

    r = client.post(
        f"/api/candidates/{cid}/resume",
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["resume_filename"] == "resume.pdf"

    r = client.get(f"/api/candidates/{cid}/resume", headers=h)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")

    # wrong extension rejected
    r = client.post(
        f"/api/candidates/{cid}/resume",
        files={"file": ("virus.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=h,
    )
    assert r.status_code == 415


def test_delete_candidate(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    cid = client.post("/api/candidates", json=CANDIDATE, headers=h).json()["id"]
    r = client.delete(f"/api/candidates/{cid}", headers=h)
    assert r.status_code == 204
    assert client.get(f"/api/candidates/{cid}", headers=h).status_code == 404
