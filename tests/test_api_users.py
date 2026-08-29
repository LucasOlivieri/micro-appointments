from fastapi.testclient import TestClient

from api.main import create_app
from conftest import API_TIMEZONE, API_USER_ID
from core.appointments import AppointmentsService


def test_available_appointment_types_are_listed_for_user(api):
    response = api.get(
        "/appointments/available-types", params={"user_id": API_USER_ID}
    )

    assert response.status_code == 200
    assert response.json() == [
        {"name": "Follow-up", "duration_minutes": 15},
        {"name": "Initial Consultation", "duration_minutes": 30},
    ]


def test_available_appointment_types_require_existing_user(api):
    response = api.get(
        "/appointments/available-types", params={"user_id": "missing"}
    )

    assert response.status_code == 404


def test_users_lists_calendar_users(api, tmp_path):
    service = AppointmentsService(tmp_path / "api.sqlite3")
    service.db["users"].insert({
        "id": "another-user",
        "name": "Another User",
        "email": "another@example.com",
        "timezone": "UTC",
    })

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
            {"name": "Follow-up", "duration_minutes": 15},
            {"name": "Initial Consultation", "duration_minutes": 30},
        ],
    }
    assert [user["name"] for user in users] == sorted(
        user["name"] for user in users
    )


def test_agent_websocket_infers_single_user_when_user_id_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("core.migrations.load_config", lambda *args, **kwargs: {"users": []})

    path = tmp_path / "single-user.sqlite3"
    service = AppointmentsService(path)
    service.db["users"].insert({
        "id": API_USER_ID,
        "name": "API User",
        "email": "api@example.com",
        "timezone": API_TIMEZONE,
    })

    async def fake_run_agent(prompt, conversation_id):
        assert "User ID: api-user" in prompt
        assert "Show me my appointments" in prompt
        assert conversation_id == "ws-session"
        return "Here are your appointments."

    monkeypatch.setattr("api.routes.agent.run_agent", fake_run_agent)

    with TestClient(create_app(path)).websocket_connect("/ws/agent") as websocket:
        websocket.send_json({
            "message": "Show me my appointments",
            "conversation_id": "ws-session",
        })
        data = websocket.receive_json()

    assert data == {"response": "Here are your appointments."}


def test_agent_websocket_runs_like_notebook_client(api, monkeypatch):
    async def fake_run_agent(prompt, conversation_id):
        assert "User ID: api-user" in prompt
        assert "Show me my appointments" in prompt
        assert conversation_id == "ws-session"
        return "Here are your appointments."

    monkeypatch.setattr("api.routes.agent.run_agent", fake_run_agent)

    with api.websocket_connect("/ws/agent") as websocket:
        websocket.send_json({
            "user_id": API_USER_ID,
            "message": "Show me my appointments",
            "conversation_id": "ws-session",
        })
        data = websocket.receive_json()

    assert data == {"response": "Here are your appointments."}
