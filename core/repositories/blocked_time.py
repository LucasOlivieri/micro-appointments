from __future__ import annotations

from core.db import get_db
from core.models import BlockedTime
from core.repositories.base import BaseRepository


class BlockedTimeRepository(BaseRepository):
    queries_prefix = "blocked_times"
    model_class = BlockedTime
    table_name = "blocked_times"
    column_map = {"user": "user_id"}

    async def create(self, **payload):
        db = get_db()
        mapped = self._map_payload(payload)
        cursor = await db.execute(
            self._query("create"),
            (
                mapped.get("user"),
                mapped.get("reason"),
                mapped.get("start"),
                mapped.get("end"),
                mapped.get("appointment_type"),
                mapped.get("customer"),
                mapped.get("google_event_id"),
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid
        return await self.get_by_id(row_id)

    async def list_for_user(self, user_id, *, bookings_only=False):
        db = get_db()
        if bookings_only:
            cursor = await db.execute(self._query("list_booked_for_user"), (user_id,))
        else:
            cursor = await db.execute(self._query("list_for_user"), (user_id,))
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def list_booked_for_user(self, user_id, appointment_type=None):
        db = get_db()
        if appointment_type is not None:
            sql = (
                self._query("list_booked_for_user")
                + " AND LOWER(appointment_type) = LOWER(?)"
            )
            cursor = await db.execute(sql, (user_id, appointment_type))
        else:
            cursor = await db.execute(self._query("list_booked_for_user"), (user_id,))
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def get_booked_by_user(self, user_id, appointment_id):
        db = get_db()
        cursor = await db.execute(
            self._query("get_booked_by_user"), (appointment_id, user_id)
        )
        row = await cursor.fetchone()
        return self._row_to_model(row)

    async def list_rows_for_user(self, user_id):
        db = get_db()
        cursor = await db.execute(self._query("list_rows_for_user"), (user_id,))
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]
