from fastapi.testclient import TestClient

from api.main import create_app
from core.appointments import AppointmentsService


USER_ID = "api-user"
TZ = "America/Argentina/Buenos_Aires"


def seed_database(path):
    service = AppointmentsService(path)
    service.db["users"].insert({
        "id": USER_ID,
        "name": "API User",
        "email": "api@example.com",
        "timezone": TZ,
    })
    for weekday in range(5):
        service.db["rules"].insert({
            "user": USER_ID,
            "weekday": weekday,
            "start": "09:00",
            "end": "17:00",
        })
    service.db["appointment_types"].insert({
        "user": USER_ID,
        "name": "Follow-up",
        "duration_minutes": 15,
    })
    service.db["appointment_types"].insert({
        "user": USER_ID,
        "name": "Initial Consultation",
        "duration_minutes": 30,
    })


def client(tmp_path):
    path = tmp_path / "api.sqlite3"
    seed_database(path)
    return TestClient(create_app(path))


def test_create_and_list_appointment(tmp_path):
    api = client(tmp_path)
    response = api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    })

    assert response.status_code == 201
    appointment = response.json()
    assert appointment["appointment_type"] == "Follow-up"
    assert appointment["end"] == "2026-08-24T10:15:00-03:00"

    response = api.get("/appointments", params={"user_id": USER_ID})
    assert response.status_code == 200
    assert response.json() == [appointment]


def test_available_slots_respect_type_and_start_filter(tmp_path):
    api = client(tmp_path)
    response = api.get("/appointments/available-slots", params={
        "user_id": USER_ID,
        "appointment_type": "follow-up",
        "nr_slots": 2,
        "from_datetime": "2026-08-24T10:00:00-03:00",
    })

    assert response.status_code == 200
    slots = response.json()
    assert len(slots) == 2
    assert slots[0] == {
        "start": "2026-08-24T10:00:00-03:00",
        "end": "2026-08-24T10:15:00-03:00",
        "appointment_type": "Follow-up",
    }
    assert slots[1]["start"] == "2026-08-24T10:15:00-03:00"


def test_available_slots_skip_booked_time_and_validate_type(tmp_path):
    api = client(tmp_path)
    api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    })

    response = api.get("/appointments/available-slots", params={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "nr_slots": 1,
        "from_datetime": "2026-08-24T10:00:00-03:00",
    })
    assert response.status_code == 200
    assert response.json()[0]["start"] == "2026-08-24T10:15:00-03:00"

    response = api.get("/appointments/available-slots", params={
        "user_id": USER_ID,
        "appointment_type": "Unknown",
    })
    assert response.status_code == 422


def test_list_filter_is_case_insensitive_and_excludes_blocks(tmp_path):
    api = client(tmp_path)
    api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    })
    service = AppointmentsService(tmp_path / "api.sqlite3")
    service.create_blocked_time({
        "user": USER_ID,
        "reason": "vacation",
        "start": "2026-08-24T12:00:00-03:00",
        "end": "2026-08-24T13:00:00-03:00",
    })

    response = api.get("/appointments", params={
        "user_id": USER_ID,
        "appointment_type": "FOLLOW-UP",
    })
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["reason"] == "booked"


def test_create_reports_conflicts_and_unknown_types(tmp_path):
    api = client(tmp_path)
    payload = {
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    }
    assert api.post("/appointments", json=payload).status_code == 201
    assert api.post("/appointments", json=payload).status_code == 409
    payload["appointment_type"] = "Unknown"
    assert api.post("/appointments", json=payload).status_code == 422


def test_get_and_delete_enforce_ownership(tmp_path):
    api = client(tmp_path)
    created = api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    }).json()

    assert api.get(f"/appointments/{created['id']}", params={"user_id": "other"}).status_code == 404
    deleted = api.delete(
        f"/appointments/{created['id']}", params={"user_id": USER_ID}
    )
    assert deleted.status_code == 200
    assert api.get(
        f"/appointments/{created['id']}", params={"user_id": USER_ID}
    ).status_code == 404


def test_reschedule_revalidates_and_keeps_original_when_conflicting(tmp_path):
    api = client(tmp_path)
    first = api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    }).json()
    api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T11:00:00-03:00",
    })

    response = api.patch(f"/appointments/{first['id']}", json={
        "user_id": USER_ID,
        "start": "2026-08-24T11:00:00-03:00",
    })
    assert response.status_code == 409
    assert api.get(
        f"/appointments/{first['id']}", params={"user_id": USER_ID}
    ).status_code == 200


def test_reschedule_moves_to_a_free_slot(tmp_path):
    api = client(tmp_path)
    first = api.post("/appointments", json={
        "user_id": USER_ID,
        "appointment_type": "Follow-up",
        "start": "2026-08-24T10:00:00-03:00",
    }).json()

    response = api.patch(f"/appointments/{first['id']}", json={
        "user_id": USER_ID,
        "start": "2026-08-24T11:00:00-03:00",
    })
    assert response.status_code == 200
    assert response.json()["start"] == "2026-08-24T11:00:00-03:00"
    assert api.get(
        f"/appointments/{first['id']}", params={"user_id": USER_ID}
    ).status_code == 404


def test_missing_user_is_not_created_implicitly(tmp_path):
    api = client(tmp_path)
    response = api.get("/appointments", params={"user_id": "missing"})
    assert response.status_code == 404
