from __future__ import annotations

from core.db import get_db
from core.models import Customer
from core.repositories.base import BaseRepository


class CustomerRepository(BaseRepository):
    queries_prefix = "customers"
    model_class = Customer
    table_name = "customer"
    column_map = {}

    async def get_by_phone(self, phone):
        db = get_db()
        cursor = await db.execute(self._query("get_by_phone"), (phone,))
        row = await cursor.fetchone()
        return self._row_to_model(row)

    async def upsert(self, customer_id, phone, name, info=None):
        db = get_db()
        await db.execute(
            self._query("upsert"),
            (customer_id, phone, name, info),
        )
        await db.commit()
        return await self.get_by_id(customer_id), True

    async def list_by_ids(self, ids):
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        db = get_db()
        sql = f"SELECT * FROM customer WHERE id IN ({placeholders})"
        cursor = await db.execute(sql, ids)
        rows = await cursor.fetchall()
        return [Customer(**dict(row)) for row in rows]
