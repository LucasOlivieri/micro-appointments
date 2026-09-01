import pytest
from test_main import TestBookAppointment

import core.main as main_module
from core.db import init_db


@pytest.fixture(autouse=True)
async def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DATABASE_PATH", tmp_path / "testdb.sqlite3")
    await init_db(tmp_path / "testdb.sqlite3")


class TestBooking(TestBookAppointment):
    __test__ = True
