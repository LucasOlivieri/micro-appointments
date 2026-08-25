import sqlite_utils

import pytest

import src.appointments as appointments_module
from src.appointments import AppointmentsService, onaction


@pytest.fixture
def service(tmp_path):
    service = AppointmentsService(tmp_path / "testdb.sqlite3")
    service.db["users"].insert({
        "id": "user-1",
        "name": "User",
        "email": "user@example.com",
        "timezone": "America/Argentina/Buenos_Aires",
    })
    return service


@pytest.fixture(autouse=True)
def clear_action_handlers():
    appointments_module._ACTION_HANDLERS.clear()
    yield
    appointments_module._ACTION_HANDLERS.clear()


def test_create_returns_item_and_dispatches_created(service):
    received = []

    @onaction("created")
    def sync_to_calendar(item):
        received.append(item)

    created = service.create_blocked_time({
        "user": "user-1",
        "reason": "booked",
        "start": "2026-08-24T10:00:00-03:00",
        "end": "2026-08-24T10:15:00-03:00",
        "appointment_type": "Follow-up",
    })

    assert isinstance(created["id"], int)
    assert created["start"] == "2026-08-24T10:00:00-03:00"
    assert created["end"] == "2026-08-24T10:15:00-03:00"
    assert "start_datetime" not in created
    assert "end_datetime" not in created
    assert received == [created]


def test_update_returns_item_and_dispatches_updated(service):
    created = service.create_blocked_time({
        "user": "user-1",
        "reason": "booked",
        "start": "2026-08-24T10:00:00-03:00",
        "end": "2026-08-24T10:15:00-03:00",
        "appointment_type": "Follow-up",
    })
    received = []

    @onaction("updated")
    def sync_update(item):
        received.append(item)

    updated = service.update_blocked_time(created["id"], {
        "reason": "rescheduled",
    })

    assert updated["reason"] == "rescheduled"
    assert received == [updated]