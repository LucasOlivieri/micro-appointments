import pytest

from core.db import close_db, init_db
from core.models import User
from core.repositories.blocked_time import BlockedTimeRepository
from core.repositories.user import UserRepository


@pytest.fixture
async def repo_db(tmp_path):
    await init_db(tmp_path / "repo.sqlite3")
    yield
    await close_db()


@pytest.mark.anyio
async def test_user_repository_upsert_and_get_by_id(repo_db, tmp_path):
    repo = UserRepository()

    user, created = await repo.upsert(
        "user-1",
        {
            "name": "Doctor Example",
            "email": "doctor@example.com",
            "timezone": "UTC",
        },
    )

    assert created is True
    assert user.id == "user-1"

    fetched = await repo.get_by_id("user-1")
    assert fetched is not None
    assert isinstance(fetched, User)
    assert fetched.name == "Doctor Example"


@pytest.mark.anyio
async def test_blocked_time_repository_list_for_user(repo_db, tmp_path):
    user_repo = UserRepository()
    blocked_repo = BlockedTimeRepository()

    await user_repo.create(
        id="user-1",
        name="Doctor Example",
        email="doctor@example.com",
        timezone="UTC",
    )

    await blocked_repo.create(
        user_id="user-1",
        reason="booked",
        start="2026-08-24T10:00:00+00:00",
        end="2026-08-24T10:15:00+00:00",
        appointment_type="Follow-up",
    )
    await blocked_repo.create(
        user_id="user-1",
        reason="vacation",
        start="2026-08-25T00:00:00+00:00",
        end="2026-08-27T00:00:00+00:00",
        appointment_type=None,
    )

    all_rows = await blocked_repo.list_for_user("user-1")
    booked_rows = await blocked_repo.list_for_user("user-1", bookings_only=True)

    assert len(all_rows) == 2
    assert len(booked_rows) == 1
    assert booked_rows[0].appointment_type == "Follow-up"
