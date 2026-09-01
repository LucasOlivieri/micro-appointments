from conftest import API_USER_ID


async def test_available_slots_respect_type_and_start_filter(api):
    response = api.get(
        "/appointments/available-slots",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "follow-up",
            "nr_slots": 2,
            "from_datetime": "2026-08-24T10:00:00-03:00",
        },
    )

    assert response.status_code == 200
    slots = response.json()
    assert len(slots) == 2
    assert slots[0] == {
        "start": "2026-08-24T10:00:00-03:00",
        "end": "2026-08-24T10:15:00-03:00",
        "appointment_type": "Follow-up",
    }
    assert slots[1]["start"] == "2026-08-24T10:15:00-03:00"


async def test_available_slots_skip_booked_time_and_validate_type(api):
    api.post(
        "/appointments",
        json={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "start": "2026-08-24T10:00:00-03:00",
            "name": "Ada Lovelace",
            "phone": "+541100000001",
        },
    )

    response = api.get(
        "/appointments/available-slots",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Follow-up",
            "nr_slots": 1,
            "from_datetime": "2026-08-24T10:00:00-03:00",
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["start"] == "2026-08-24T10:15:00-03:00"

    response = api.get(
        "/appointments/available-slots",
        params={
            "user_id": API_USER_ID,
            "appointment_type": "Unknown",
        },
    )
    assert response.status_code == 422
