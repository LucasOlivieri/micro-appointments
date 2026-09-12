import pytest
from test_main import TestBookAppointment

import core.main as main_module
from core.db import close_db, init_db
from core.migrations import sync_config_to_db


@pytest.fixture(autouse=True)
async def isolated_database(tmp_path, monkeypatch):
    path = tmp_path / "testdb.sqlite3"
    monkeypatch.setattr(main_module, "DATABASE_PATH", path)
    await init_db(path, sync_config=False)
    await sync_config_to_db()
    yield
    await close_db()


class TestBooking(TestBookAppointment):
    __test__ = True
