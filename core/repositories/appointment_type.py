from __future__ import annotations

from core.db import get_db
from core.models import AppointmentType
from core.repositories.base import BaseRepository


class AppointmentTypeRepository(BaseRepository):
    queries_prefix = "appointment_types"
    model_class = AppointmentType
    table_name = "appointment_types"
    column_map = {"user": "user_id"}

    async def create(self, **payload):
        db = get_db()
        mapped = self._map_payload(payload)
        cursor = await db.execute(
            self._query("create"),
            (
                mapped.get("user"),
                mapped.get("name"),
                mapped.get("duration_minutes"),
                mapped.get("advance_notice_minutes"),
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid
        return await self.get_by_id(row_id)

    async def list_by_user(self, user_id):
        db = get_db()
        cursor = await db.execute(self._query("list_by_user"), (user_id,))
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]
