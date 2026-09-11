from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from conftest import API_USER_ID

from core.services.appointments import AppointmentsService


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
        f"/appointments/{created['id']}",
        params={"user_id": API_USER_ID, "customer_phone": "+541100000001"},
    )
    assert deleted.status_code == 200
    assert (
        api.get(
            f"/appointments/{created['id']}", params={"user_id": API_USER_ID}
        ).status_code
        == 404
    )


async def test_only_customer_can_cancel_appointment(api):
    created = api.post("/appointments", json=appointment_payload()).json()
    response = api.delete(
        f"/appointments/{created['id']}",
        params={"user_id": API_USER_ID, "customer_phone": "+541100000002"},
    )
    assert response.status_code == 403
    assert (
        api.get(
            f"/appointments/{created['id']}", params={"user_id": API_USER_ID}
        ).status_code
        == 200
    )

    response = api.delete(
        f"/appointments/{created['id']}",
        params={"user_id": API_USER_ID, "customer_phone": "+541100000001"},
    )
    assert response.status_code == 200


async def test_list_appointments_filters_by_date_and_customer(api):
    first = api.post("/appointments", json=appointment_payload()).json()
    second_payload = appointment_payload(name="Grace Hopper")
    second_payload["start"] = "2026-08-25T10:00:00-03:00"
    second_payload["phone"] = "+541100000002"
    second = api.post("/appointments", json=second_payload).json()

    response = api.get(
        "/appointments",
        params={
            "user_id": API_USER_ID,
            "from_datetime": "2026-08-25T00:00:00-03:00",
            "to_datetime": "2026-08-25T23:59:59-03:00",
        },
    )
    assert [item["id"] for item in response.json()] == [second["id"]]
    response = api.get(
        "/appointments/by-customer",
        params={"user_id": API_USER_ID, "customer_phone": "+541100000001"},
    )
    assert [item["id"] for item in response.json()] == [first["id"]]


async def test_daily_availability_returns_hours_and_free_slots(api):
    response = api.get(
        "/appointments/availability",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "date": "2026-08-24",
        },
    )

    assert response.status_code == 200
    availability = response.json()
    assert availability["date"] == "2026-08-24"
    assert availability["working_start"] == "2026-08-24T09:00:00-03:00"
    assert availability["working_end"] == "2026-08-24T17:00:00-03:00"
    assert len(availability["available_slots"]) == 32


async def test_daily_availability_is_empty_outside_working_days(api):
    response = api.get(
        "/appointments/availability",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "date": "2026-08-29",
        },
    )

    assert response.status_code == 200
    assert response.json()["working_start"] is None
    assert response.json()["available_slots"] == []


async def test_daily_availability_only_returns_blocks_for_requested_date(api, tmp_path):
    api.portal.call(seed_block, tmp_path / "api.sqlite3")

    response = api.get(
        "/appointments/availability",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "date": "2026-08-24",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["blocked_periods"]) == 1
    assert response.json()["blocked_periods"][0] == {
        "reason": "vacation",
        "start_date": "2026-08-24",
        "end_date": "2026-08-24",
    }

    response = api.get(
        "/appointments/availability",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "date": "2026-09-08",
        },
    )

    assert response.status_code == 200
    assert response.json()["blocked_periods"] == []


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


async def test_advance_notice_rejects_early_booking(api, tmp_path):
    """Booking a slot within the advance notice window should return 422."""
    # Create an appointment type with a 1440 min (24h) advance notice
    path = tmp_path / "api.sqlite3"
    service = AppointmentsService(path)
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Advance Notice Type",
            "duration_minutes": 30,
            "advance_notice_minutes": 1440,
        }
    )
    # Try to book a slot 1 hour from now — should be rejected
    soon = (
        datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")) + timedelta(hours=1)
    ).isoformat()
    payload = appointment_payload(appointment_type="Advance Notice Type")
    payload["start"] = soon
    response = api.post("/appointments", json=payload)
    assert response.status_code == 422
    assert "1440 minutes in advance" in response.json()["detail"]


async def test_advance_notice_allows_future_booking(api, tmp_path):
    """Booking a slot well past the deadline should succeed."""
    path = tmp_path / "api.sqlite3"
    service = AppointmentsService(path)
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Advance Notice Type",
            "duration_minutes": 30,
            "advance_notice_minutes": 1440,
        }
    )
    payload = appointment_payload(appointment_type="Advance Notice Type")
    payload["start"] = "2026-09-28T10:00:00-03:00"
    response = api.post("/appointments", json=payload)
    assert response.status_code == 201


async def test_advance_notice_no_restriction_when_unset(api):
    """When advance_notice_minutes is not set, booking works as before."""
    payload = appointment_payload()
    response = api.post("/appointments", json=payload)
    assert response.status_code == 201
