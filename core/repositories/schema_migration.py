from __future__ import annotations

from core.db import get_db
from core.models import SchemaMigration
from core.repositories.base import BaseRepository


class SchemaMigrationRepository(BaseRepository):
    queries_prefix = "schema_migration"
    model_class = SchemaMigration
    table_name = "schema_migrations"
    column_map = {}

    async def get_by_name(self, name):
        db = get_db()
        cursor = await db.execute(self._query("get_by_name"), (name,))
        row = await cursor.fetchone()
        return self._row_to_model(row)
