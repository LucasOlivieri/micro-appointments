import pytest
from test_main import TestBookAppointment
from tortoise.contrib.test import tortoise_test_context

import core.main as main_module
from core.migrations import sync_config_to_db


@pytest.fixture(autouse=True)
async def isolated_database(tmp_path, monkeypatch):
    path = tmp_path / "testdb.sqlite3"
    monkeypatch.setattr(main_module, "DATABASE_PATH", path)

    async with tortoise_test_context(
        modules=["core.models"],
        db_url=f"sqlite://{path}",
    ):
        await sync_config_to_db()
        yield


class TestBooking(TestBookAppointment):
    __test__ = True
