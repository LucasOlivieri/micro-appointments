from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import core.services.appointments as appointments_module
from core.db import close_db, init_db
from core.repositories import BlockedTimeRepository, UserRepository
from core.services.appointments import AppointmentsService, onaction


@pytest.fixture
async def service(tmp_path):
    await init_db(tmp_path / "testdb.sqlite3")
    service = AppointmentsService(tmp_path / "testdb.sqlite3")
    await service.create_user(
        {
            "id": "user-1",
            "name": "User",
            "email": "user@example.com",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )
    yield service
    await close_db()


@pytest.fixture(autouse=True)
def clear_action_handlers():
    appointments_module._ACTION_HANDLERS.clear()
    yield
    appointments_module._ACTION_HANDLERS.clear()


async def test_create_returns_item_and_dispatches_created(service):
    received = []

    @onaction("created")
    async def sync_to_calendar(item):
        received.append(item)

    created = await service.create_blocked_time(
        {
            "user": "user-1",
            "reason": "booked",
            "start": "2026-08-24T10:00:00-03:00",
            "end": "2026-08-24T10:15:00-03:00",
            "appointment_type": "Follow-up",
        }
    )

    assert isinstance(created["id"], int)
    assert created["start"] == "2026-08-24T10:00:00-03:00"
    assert created["end"] == "2026-08-24T10:15:00-03:00"
    assert "start_datetime" not in created
    assert "end_datetime" not in created
    assert received == [created]


async def test_update_returns_item_and_dispatches_updated(service):
    created = await service.create_blocked_time(
        {
            "user": "user-1",
            "reason": "booked",
            "start": "2026-08-24T10:00:00-03:00",
            "end": "2026-08-24T10:15:00-03:00",
            "appointment_type": "Follow-up",
        }
    )
    received = []

    @onaction("updated")
    async def sync_update(item):
        received.append(item)

    updated = await service.update_blocked_time(
        created["id"],
        {
            "reason": "rescheduled",
        },
    )

    assert updated["reason"] == "rescheduled"
    assert received == [updated]


async def test_service_has_main_compatibility_logic(tmp_path):
    await init_db(tmp_path / "testdb.sqlite3")
    service = AppointmentsService(tmp_path / "testdb.sqlite3")
    await service.create_user(
        {
            "id": "user-2",
            "name": "User Two",
            "email": "user2@example.com",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )
    await service.create_rule(
        {
            "user": "user-2",
            "weekday": 0,
            "start": "09:00",
            "end": "17:00",
        }
    )
    await service.create_appointment_type(
        {
            "user": "user-2",
            "name": "Follow-up",
            "duration_minutes": 15,
        }
    )

    user = await service.get_user("user-2")
    user["rules"] = await service.list_rules("user-2")
    user["appointment_types"] = await service.list_appointment_types("user-2")
    user["blocked_time"] = []

    assert service.get_appointment_type(user, "follow-up")["name"] == "Follow-up"
    slots = service.get_next_free_slots(
        user,
        "Follow-up",
        nr_slots=2,
        from_datetime=datetime(
            2026, 8, 24, 8, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires")
        ),
    )
    assert len(slots) >= 2
    assert all(slot["appointment_type"] == "Follow-up" for slot in slots)


async def test_service_uses_model_repositories(service):
    assert isinstance(service.users, UserRepository)
    assert isinstance(service.blocked_times, BlockedTimeRepository)
    assert await service.users.get_by_id("user-1") is not None
