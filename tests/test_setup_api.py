from __future__ import annotations

import base64

import pytest
from conftest import API_TIMEZONE
from fastapi.testclient import TestClient

from api.main import create_app
from config import Config
from core.db import init_db
from core.services.appointments import AppointmentsService

BASIC_AUTH = base64.b64encode(
    f"{Config.ADMIN_USER}:{Config.ADMIN_PASSWORD}".encode()
).decode("utf-8")
BASIC_HEADER = {"Authorization": f"Basic {BASIC_AUTH}"}


async def seed_setup_user(path):
    await init_db(path, sync_config=False)
    service = AppointmentsService(path)
    await service.create_user(
        {
            "id": "setup-user-1",
            "name": "Setup User",
            "email": "setup@example.com",
            "timezone": API_TIMEZONE,
        }
    )
    await service.create_rule(
        {
            "user_id": "setup-user-1",
            "weekday": 0,
            "start": "09:00",
            "end": "17:00",
            "rrule": "FREQ=WEEKLY;BYDAY=MO",
        }
    )
    await service.create_appointment_type(
        {
            "user_id": "setup-user-1",
            "name": "Consultation",
            "duration_minutes": 30,
            "advance_notice_minutes": 60,
        }
    )
    await service.create_blocked_time(
        {
            "user_id": "setup-user-1",
            "reason": "Vacation",
            "start": "2026-09-20T00:00:00-03:00",
            "end": "2026-09-27T23:59:00-03:00",
        }
    )


@pytest.fixture
def setup_api(tmp_path):
    path = tmp_path / "setup.sqlite3"
    app = create_app(path, on_startup=seed_setup_user, sync_config=False)
    with TestClient(app) as client:
        yield client


# ── Auth ──


def test_setup_rejects_without_auth(setup_api):
    assert setup_api.get("/setup/data").status_code == 401
    assert setup_api.post("/setup/users", json={}).status_code == 401


def test_setup_accepts_with_valid_auth(setup_api):
    resp = setup_api.get("/setup/data", headers=BASIC_HEADER)
    assert resp.status_code == 200


# ── GET /setup/data ──


def test_setup_data_returns_aggregate(setup_api):
    resp = setup_api.get("/setup/data", headers=BASIC_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    # Find our seeded user among any config-seeded users
    user = next((u for u in data if u["id"] == "setup-user-1"), None)
    assert user is not None, f"setup-user-1 not found in {[u['id'] for u in data]}"
    assert user["name"] == "Setup User"
    assert user["email"] == "setup@example.com"
    assert len(user["rules"]) == 1
    assert user["rules"][0]["weekday"] == 0
    assert len(user["appointment_types"]) == 1
    assert user["appointment_types"][0]["name"] == "Consultation"
    assert len(user["blocked_times"]) == 1
    assert user["blocked_times"][0]["reason"] == "Vacation"


# ── CRUD Users ──


def test_create_user(setup_api):
    resp = setup_api.post(
        "/setup/users",
        headers=BASIC_HEADER,
        json={
            "id": "new-user",
            "name": "New User",
            "email": "new@example.com",
            "timezone": API_TIMEZONE,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New User"

    # Verify in aggregate
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    ids = [u["id"] for u in agg]
    assert "new-user" in ids


def test_update_user(setup_api):
    resp = setup_api.put(
        "/setup/users/setup-user-1",
        headers=BASIC_HEADER,
        json={"name": "Updated Name", "email": "updated@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"

    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    user = next(u for u in agg if u["id"] == "setup-user-1")
    assert user["name"] == "Updated Name"


def test_delete_user(setup_api):
    resp = setup_api.delete("/setup/users/setup-user-1", headers=BASIC_HEADER)
    assert resp.status_code == 200

    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    ids = [u["id"] for u in agg]
    assert "setup-user-1" not in ids


def test_delete_nonexistent_user(setup_api):
    resp = setup_api.delete("/setup/users/nonexistent", headers=BASIC_HEADER)
    assert resp.status_code == 404


# ── CRUD Rules ──


def _find_user(data, user_id="setup-user-1"):
    return next(u for u in data if u["id"] == user_id)


def test_create_rule(setup_api):
    resp = setup_api.post(
        "/setup/rules",
        headers=BASIC_HEADER,
        json={
            "user_id": "setup-user-1",
            "weekday": 2,
            "start": "10:00",
            "end": "14:00",
            "rrule": "FREQ=WEEKLY;BYDAY=WE",
        },
    )
    assert resp.status_code == 200
    rule = resp.json()
    assert rule["weekday"] == 2
    assert rule["start"] == "10:00"

    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    user = _find_user(agg)
    assert len(user["rules"]) == 2


def test_update_rule(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    rule_id = _find_user(agg)["rules"][0]["id"]

    resp = setup_api.put(
        f"/setup/rules/{rule_id}",
        headers=BASIC_HEADER,
        json={"start": "08:00", "end": "12:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["start"] == "08:00"


def test_delete_rule(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    rule_id = _find_user(agg)["rules"][0]["id"]

    resp = setup_api.delete(f"/setup/rules/{rule_id}", headers=BASIC_HEADER)
    assert resp.status_code == 200

    agg2 = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    assert len(_find_user(agg2)["rules"]) == 0


# ── CRUD Appointment Types ──


def test_create_appointment_type(setup_api):
    resp = setup_api.post(
        "/setup/appointment-types",
        headers=BASIC_HEADER,
        json={"user_id": "setup-user-1", "name": "Follow-up", "duration_minutes": 15},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Follow-up"

    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    user = _find_user(agg)
    assert len(user["appointment_types"]) == 2


def test_update_appointment_type(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    at_id = _find_user(agg)["appointment_types"][0]["id"]

    resp = setup_api.put(
        f"/setup/appointment-types/{at_id}",
        headers=BASIC_HEADER,
        json={"duration_minutes": 45},
    )
    assert resp.status_code == 200
    assert resp.json()["duration_minutes"] == 45


def test_delete_appointment_type(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    at_id = _find_user(agg)["appointment_types"][0]["id"]

    resp = setup_api.delete(f"/setup/appointment-types/{at_id}", headers=BASIC_HEADER)
    assert resp.status_code == 200

    agg2 = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    assert len(_find_user(agg2)["appointment_types"]) == 0


# ── CRUD Blocked Times ──


def test_create_blocked_time(setup_api):
    resp = setup_api.post(
        "/setup/blocked-times",
        headers=BASIC_HEADER,
        json={
            "user_id": "setup-user-1",
            "reason": "Holiday",
            "start": "2026-12-25T00:00:00-03:00",
            "end": "2026-12-25T23:59:00-03:00",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Holiday"

    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    user = _find_user(agg)
    assert len(user["blocked_times"]) == 2


def test_update_blocked_time(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    bt_id = _find_user(agg)["blocked_times"][0]["id"]

    resp = setup_api.put(
        f"/setup/blocked-times/{bt_id}",
        headers=BASIC_HEADER,
        json={"reason": "Extended Vacation"},
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Extended Vacation"


def test_delete_blocked_time(setup_api):
    agg = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    bt_id = _find_user(agg)["blocked_times"][0]["id"]

    resp = setup_api.delete(f"/setup/blocked-times/{bt_id}", headers=BASIC_HEADER)
    assert resp.status_code == 200

    agg2 = setup_api.get("/setup/data", headers=BASIC_HEADER).json()
    assert len(_find_user(agg2)["blocked_times"]) == 0


# ── HTML page ──


def test_setup_page_returns_html(setup_api):
    resp = setup_api.get("/setup", headers=BASIC_HEADER)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Setup" in resp.text
