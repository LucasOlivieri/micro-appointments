from conftest import API_TIMEZONE, API_USER_ID

from core.services.appointments import AppointmentsService


async def test_available_appointment_types_are_listed_for_user(api):
    response = api.get("/appointments/available-types", params={"user_id": API_USER_ID})

    assert response.status_code == 200
    assert response.json() == [
        {"name": "Follow-up", "duration_minutes": 15, "advance_notice_minutes": None},
        {
            "name": "Initial Consultation",
            "duration_minutes": 30,
            "advance_notice_minutes": None,
        },
    ]


async def test_available_appointment_types_require_existing_user(api):
    response = api.get("/appointments/available-types", params={"user_id": "missing"})

    assert response.status_code == 404


def test_health_reports_database_and_integrations(api):
    response = api.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "integrations": [],
    }


async def test_users_lists_calendar_users(api):
    async def create_user():
        service = AppointmentsService("api.sqlite3")
        await service.create_user(
            {
                "id": "another-user",
                "name": "Another User",
                "email": "another@example.com",
                "timezone": "UTC",
            }
        )

    api.portal.call(create_user)

    response = api.get("/users")

    assert response.status_code == 200
    users = response.json()
    users_by_id = {user["id"]: user for user in users}
    assert users_by_id["another-user"] == {
        "id": "another-user",
        "name": "Another User",
        "timezone": "UTC",
        "available_appointment_types": [],
    }
    assert users_by_id[API_USER_ID] == {
        "id": API_USER_ID,
        "name": "API User",
        "timezone": API_TIMEZONE,
        "available_appointment_types": [
            {
                "name": "Follow-up",
                "duration_minutes": 15,
                "advance_notice_minutes": None,
            },
            {
                "name": "Initial Consultation",
                "duration_minutes": 30,
                "advance_notice_minutes": None,
            },
        ],
    }
    assert [user["name"] for user in users] == sorted(user["name"] for user in users)


def test_agent_prompt_uses_user_timezone():
    from bot.handler import build_agent_prompt

    prompt = build_agent_prompt("What time is my appointment?", "api-user", "UTC")

    assert "Current time:" in prompt
    assert "+00:00" in prompt
