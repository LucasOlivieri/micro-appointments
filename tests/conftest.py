import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.appointments import AppointmentsService
from core.db import init_db

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


async def seed_api_database(path):
    await init_db(path)
    service = AppointmentsService(path)
    await service.create_user(
        {
            "id": API_USER_ID,
            "name": "API User",
            "email": "api@example.com",
            "timezone": API_TIMEZONE,
        }
    )
    for weekday in range(5):
        await service.create_rule(
            {
                "user_id": API_USER_ID,
                "weekday": weekday,
                "start": "09:00",
                "end": "17:00",
            }
        )
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Follow-up",
            "duration_minutes": 15,
        }
    )
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Initial Consultation",
            "duration_minutes": 30,
        }
    )


async def seed_api_data(path):
    service = AppointmentsService(path)
    await service.create_user(
        {
            "id": API_USER_ID,
            "name": "API User",
            "email": "api@example.com",
            "timezone": API_TIMEZONE,
        }
    )
    for weekday in range(5):
        await service.create_rule(
            {
                "user_id": API_USER_ID,
                "weekday": weekday,
                "start": "09:00",
                "end": "17:00",
            }
        )
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Follow-up",
            "duration_minutes": 15,
        }
    )
    await service.create_appointment_type(
        {
            "user_id": API_USER_ID,
            "name": "Initial Consultation",
            "duration_minutes": 30,
        }
    )


async def seed_single_user(path):
    service = AppointmentsService(path)

    await service.create_user(
        {
            "id": API_USER_ID,
            "name": "API User",
            "email": "api@example.com",
            "timezone": API_TIMEZONE,
        }
    )


@pytest.fixture
def single_user_api(tmp_path):
    path = tmp_path / "single-user.sqlite3"
    app = create_app(path, on_startup=seed_single_user)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api(tmp_path):
    path = tmp_path / "api.sqlite3"
    app = create_app(path, on_startup=seed_api_data)
    with TestClient(app) as client:
        yield client
