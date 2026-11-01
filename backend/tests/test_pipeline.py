"""Vacancies, kanban pipeline, activities, dashboard tests."""
from datetime import datetime, timedelta, timezone

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, RECRUITER_EMAIL, RECRUITER_PASSWORD

VACANCY = {
    "title": "Middle Python Developer",
    "client": "ООО Рога",
    "description": "Разработка внутренних сервисов",
    "requirements": "Python, FastAPI, PostgreSQL",
    "salary_min": 180000,
    "salary_max": 260000,
}

CANDIDATE = {
    "full_name": "Сергей Смирнов",
    "email": "sergey@example.com",
    "phone": "+79995554433",
    "position": "Python Dev",
}


def _setup(client):
    h = client.auth_headers(RECRUITER_EMAIL, RECRUITER_PASSWORD)
    vacancy = client.post("/api/vacancies", json=VACANCY, headers=h).json()
    candidate = client.post("/api/candidates", json=CANDIDATE, headers=h).json()
    return h, vacancy, candidate


def test_vacancy_crud(client, recruiter_user):
    h, v, _ = _setup(client)
    assert v["status"] == "open"

    r = client.patch(f"/api/vacancies/{v['id']}", json={"status": "paused"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "paused"

    r = client.get("/api/vacancies?status=paused", headers=h)
    assert r.json()["total"] == 1

    assert client.delete(f"/api/vacancies/{v['id']}", headers=h).status_code == 204
    assert client.get(f"/api/vacancies/{v['id']}", headers=h).status_code == 404


def test_invalid_status_rejected(client, recruiter_user):
    h, v, _ = _setup(client)
    r = client.patch(f"/api/vacancies/{v['id']}", json={"status": "weird"}, headers=h)
    assert r.status_code == 422


def test_board_and_stage_moves(client, recruiter_user):
    h, v, c = _setup(client)
    r = client.post(
        f"/api/vacancies/{v['id']}/cards",
        json={"candidate_id": c["id"], "vacancy_id": v["id"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["stage"] == "new"

    # duplicate card rejected
    r = client.post(
        f"/api/vacancies/{v['id']}/cards",
        json={"candidate_id": c["id"], "vacancy_id": v["id"]},
        headers=h,
    )
    assert r.status_code == 409

    # move to screening
    r = client.post(
        f"/api/cards/{card['id']}/move",
        json={"stage": "screening", "comment": "Позвонили"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["stage"] == "screening"

    # reject requires reason
    r = client.post(f"/api/cards/{card['id']}/move", json={"stage": "rejected"}, headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "reject_reason_required"

    # reject with reason
    r = client.post(
        f"/api/cards/{card['id']}/move",
        json={"stage": "rejected", "reject_reason": "Мало опыта"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["reject_reason"] == "Мало опыта"

    # history contains all moves
    r = client.get(f"/api/cards/{card['id']}", headers=h)
    history = r.json()["history"]
    assert [x["to_stage"] for x in history] == ["new", "screening", "rejected"]
    assert all(x["author_id"] for x in history)

    # unknown stage rejected
    r = client.post(f"/api/cards/{card['id']}/move", json={"stage": "nope"}, headers=h)
    assert r.status_code == 422


def test_board_columns(client, recruiter_user):
    h, v, c = _setup(client)
    client.post(
        f"/api/vacancies/{v['id']}/cards",
        json={"candidate_id": c["id"], "vacancy_id": v["id"]},
        headers=h,
    )
    r = client.get(f"/api/vacancies/{v['id']}/board", headers=h)
    assert r.status_code == 200
    board = r.json()["stages"]
    assert set(board) == {
        "new", "screening", "interview_recruiter", "interview_client",
        "test_task", "offer", "hired", "rejected",
    }
    assert len(board["new"]) == 1


def test_comments_and_tasks(client, recruiter_user):
    h, _, c = _setup(client)
    cid = c["id"]

    r = client.post(f"/api/candidates/{cid}/comments", json={"body": "Позвонил, заинтересован"}, headers=h)
    assert r.status_code == 201
    assert r.json()["type"] == "comment"

    due = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = client.post(
        f"/api/candidates/{cid}/tasks",
        json={"body": "Созвон в 18:00", "due_at": due},
        headers=h,
    )
    assert r.status_code == 201
    task = r.json()
    assert task["task_status"] == "open"

    # task appears in /tasks/today (due <= now? it's +2h, so NOT today yet)
    # create an overdue task
    overdue = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    client.post(
        f"/api/candidates/{cid}/tasks",
        json={"body": "Просроченная", "due_at": overdue},
        headers=h,
    )
    r = client.get("/api/tasks/today", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["body"] == "Просроченная"

    # complete the task
    r = client.patch(f"/api/tasks/{task['id']}", json={"task_status": "done"}, headers=h)
    assert r.status_code == 200
    assert r.json()["task_status"] == "done"

    # feed
    r = client.get("/api/feed", headers=h)
    assert len(r.json()) >= 3

    # activities list by type
    r = client.get(f"/api/candidates/{cid}/activities?type=comment", headers=h)
    assert len(r.json()) == 1


def test_dashboard(client, recruiter_user, admin_user):
    h, v, c = _setup(client)
    client.post(
        f"/api/vacancies/{v['id']}/cards",
        json={"candidate_id": c["id"], "vacancy_id": v["id"]},
        headers=h,
    )
    overdue = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    client.post(
        f"/api/candidates/{c['id']}/tasks",
        json={"body": "Задача на сегодня", "due_at": overdue},
        headers=h,
    )

    r = client.get("/api/dashboard", headers=h)
    assert r.status_code == 200
    body = r.json()
    stage_counts = {x["stage"]: x["count"] for x in body["stages"]}
    assert stage_counts["new"] == 1
    assert body["open_vacancies"] == 1
    assert body["tasks_today"] == 1
    assert body["total_candidates"] == 1
    assert len(body["recruiter_stats"]) == 1
    assert body["recruiter_stats"][0]["candidates"] == 1

    # admin sees everything
    adm = client.get("/api/dashboard", headers=client.auth_headers(ADMIN_EMAIL, ADMIN_PASSWORD))
    assert adm.json()["total_candidates"] == 1
    assert len(adm.json()["recruiter_stats"]) == 2  # admin + recruiter


def test_end_to_end_flow(client, recruiter_user):
    """Full scenario: login -> vacancy -> candidate -> kanban -> comment -> task -> dashboard -> CSV."""
    h, v, c = _setup(client)
    card = client.post(
        f"/api/vacancies/{v['id']}/cards",
        json={"candidate_id": c["id"], "vacancy_id": v["id"]},
        headers=h,
    ).json()
    for stage in ["screening", "interview_recruiter", "offer", "hired"]:
        r = client.post(f"/api/cards/{card['id']}/move", json={"stage": stage}, headers=h)
        assert r.status_code == 200, r.text
    client.post(f"/api/candidates/{c['id']}/comments", json={"body": "Оффер отправлен"}, headers=h)
    board = client.get(f"/api/vacancies/{v['id']}/board", headers=h).json()["stages"]
    assert len(board["hired"]) == 1
    dash = client.get("/api/dashboard", headers=h).json()
    assert {x["stage"]: x["count"] for x in dash["stages"]}["hired"] == 1
    csv_text = client.get("/api/candidates/export", headers=h).text
    assert "Сергей Смирнов" in csv_text
