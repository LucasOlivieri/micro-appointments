from __future__ import annotations

from core.db import get_db
from core.models import User
from core.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    queries_prefix = "users"
    model_class = User
    table_name = "users"
    column_map = {}  # DB column -> model field (same names)

    async def upsert(self, user_id, defaults):
        db = get_db()
        sql = self._query("upsert")
        await db.execute(
            sql,
            (
                user_id,
                defaults.get("name"),
                defaults.get("email"),
                defaults.get("timezone", "America/Argentina/Buenos_Aires"),
                defaults.get("message"),
                defaults.get("system_prompt"),
            ),
        )
        await db.commit()
        return await self.get_by_id(user_id), True

    async def list_all(self):
        db = get_db()
        cursor = await db.execute(self._query("list_all"))
        rows = await cursor.fetchall()
        return [User(**dict(row)) for row in rows]
