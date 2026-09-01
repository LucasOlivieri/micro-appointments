from conftest import API_USER_ID

from core.appointments import AppointmentsService


def appointment_payload(appointment_type="Follow-up", name="Ada Lovelace"):
    return {
        "user_id": API_USER_ID,
        "appointment_type": appointment_type,
        "start": "2026-08-24T10:00:00-03:00",
        "name": name,
        "phone": "+541100000001",
    }


async def seed_block(path):
    service = AppointmentsService(path)
    await service.create_blocked_time(
        {
            "user": API_USER_ID,
            "reason": "vacation",
            "start": "2026-08-24T12:00:00-03:00",
            "end": "2026-08-24T13:00:00-03:00",
        }
    )


async def test_create_and_list_appointment(api):
    response = api.post("/appointments", json=appointment_payload("follow-up"))

    assert response.status_code == 201
    appointment = response.json()
    assert appointment["appointment_type"] == "Follow-up"
    assert appointment["end"] == "2026-08-24T10:15:00-03:00"
    assert appointment["name"] == "Ada Lovelace"
    assert appointment["phone"] == "+541100000001"
    assert api.get("/appointments", params={"user_id": API_USER_ID}).json() == [
        appointment
    ]


async def test_list_filter_is_case_insensitive_and_excludes_blocks(api, tmp_path):
    api.post("/appointments", json=appointment_payload())
    api.portal.call(seed_block, tmp_path / "api.sqlite3")
    response = api.get(
        "/appointments",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "FOLLOW-UP",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["reason"] == "booked"


async def test_create_reports_conflicts_and_unknown_types(api):
    payload = appointment_payload()
    assert api.post("/appointments", json=payload).status_code == 201
    assert api.post("/appointments", json=payload).status_code == 409
    payload["appointment_type"] = "Unknown"
    assert api.post("/appointments", json=payload).status_code == 422


async def test_get_and_delete_enforce_ownership(api):
    created = api.post("/appointments", json=appointment_payload()).json()
    assert (
        api.get(
            f"/appointments/{created['id']}", params={"user_id": "other"}
        ).status_code
        == 404
    )
    deleted = api.delete(
        f"/appointments/{created['id']}", params={"user_id": API_USER_ID}
    )
    assert deleted.status_code == 200
    assert (
        api.get(
            f"/appointments/{created['id']}", params={"user_id": API_USER_ID}
        ).status_code
        == 404
    )


async def test_reschedule_revalidates_and_keeps_original_when_conflicting(api):
    first = api.post("/appointments", json=appointment_payload()).json()
    second = appointment_payload(name="Grace Hopper")
    second["start"] = "2026-08-24T11:00:00-03:00"
    api.post("/appointments", json=second)

    response = api.patch(
        f"/appointments/{first['id']}",
        json={
            "user_id": API_USER_ID,
            "start": "2026-08-24T11:00:00-03:00",
        },
    )
    assert response.status_code == 409
    assert (
        api.get(
            f"/appointments/{first['id']}", params={"user_id": API_USER_ID}
        ).status_code
        == 200
    )


async def test_reschedule_moves_to_a_free_slot(api):
    first = api.post("/appointments", json=appointment_payload()).json()
    response = api.patch(
        f"/appointments/{first['id']}",
        json={
            "user_id": API_USER_ID,
            "start": "2026-08-24T11:00:00-03:00",
        },
    )
    assert response.status_code == 200
    assert response.json()["start"] == "2026-08-24T11:00:00-03:00"
    assert (
        api.get(
            f"/appointments/{first['id']}", params={"user_id": API_USER_ID}
        ).status_code
        == 404
    )


async def test_missing_user_is_not_created_implicitly(single_user_api):
    assert (
        single_user_api.get("/appointments", params={"user_id": "missing"}).status_code
        == 404
    )
