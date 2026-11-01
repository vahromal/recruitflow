"""GDPR: export and erasure of candidate personal data."""
from tests.conftest import RECRUITER_EMAIL, RECRUITER_PASSWORD

CANDIDATE = {
    "full_name": "Григорий Григорьев",
    "email": "grigory@example.com",
    "phone": "+7 999 777 66 55",
    "notes": "Персональные данные",
}


def test_gdpr_export(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    cid = client.post("/api/candidates", json=CANDIDATE, headers=h).json()["id"]
    client.post(f"/api/candidates/{cid}/comments", json={"body": "коммент"}, headers=h)

    r = client.get(f"/api/gdpr/candidates/{cid}/export", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["candidate"]["email"] == "grigory@example.com"
    assert len(data["activities"]) == 1


def test_gdpr_erase(client, recruiter_user):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    cid = client.post("/api/candidates", json=CANDIDATE, headers=h).json()["id"]

    r = client.delete(f"/api/gdpr/candidates/{cid}", headers=h)
    assert r.status_code == 204
    assert client.get(f"/api/candidates/{cid}", headers=h).status_code == 404
    assert client.get(f"/api/gdpr/candidates/{cid}/export", headers=h).status_code == 404
