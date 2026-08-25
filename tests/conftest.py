import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.appointments import AppointmentsService


API_USER_ID = "api-user"
API_TIMEZONE = "America/Argentina/Buenos_Aires"


@pytest.fixture
def user():
    return {
        "id": "595b6fb0-bef2-4a55-a122-34ab5e8bcc77",
        "timezone": API_TIMEZONE,
        "appointment_types": [
            {"name": "Initial Consultation", "duration_minutes": 30},
            {"name": "Follow-up", "duration_minutes": 15},
        ],
        "rules": [
            {"weekday": weekday, "start": "09:00", "end": "17:00"}
            for weekday in range(5)
        ],
        "blocked_time": [],
    }


def seed_api_database(path):
    service = AppointmentsService(path)
    service.db["users"].insert({
        "id": API_USER_ID,
        "name": "API User",
        "email": "api@example.com",
        "timezone": API_TIMEZONE,
    })
    for weekday in range(5):
        service.db["rules"].insert({
            "user": API_USER_ID,
            "weekday": weekday,
            "start": "09:00",
            "end": "17:00",
        })
    service.db["appointment_types"].insert({
        "user": API_USER_ID,
        "name": "Follow-up",
        "duration_minutes": 15,
    })
    service.db["appointment_types"].insert({
        "user": API_USER_ID,
        "name": "Initial Consultation",
        "duration_minutes": 30,
    })


@pytest.fixture
def api(tmp_path):
    path = tmp_path / "api.sqlite3"
    seed_api_database(path)
    return TestClient(create_app(path))
