from __future__ import annotations

from core.db import get_db, get_query


class BaseRepository:
    queries_prefix: str | None = None
    model_class: type | None = None
    column_map: dict[str, str] = {}
    table_name: str | None = None

    def _query(self, name: str) -> str:
        if self.queries_prefix is None:
            raise NotImplementedError("Repository queries_prefix is not configured.")
        return get_query(f"{self.queries_prefix}/{name}")

    def _row_to_model(self, row):
        if row is None:
            return None
        data = dict(row)
        for db_col, model_field in self.column_map.items():
            if db_col in data:
                data[model_field] = data.pop(db_col)
        return self.model_class(**data)

    def _map_payload(self, payload: dict) -> dict:
        """Reverse map: model field names -> DB column names."""
        mapped = {}
        reverse_map = {v: k for k, v in self.column_map.items()}
        for key, value in payload.items():
            db_key = reverse_map.get(key, key)
            mapped[db_key] = value
        return mapped

    async def create(self, **payload):
        db = get_db()
        mapped = self._map_payload(payload)
        columns = ", ".join(mapped.keys())
        placeholders = ", ".join("?" for _ in mapped)
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        cursor = await db.execute(sql, tuple(mapped.values()))
        await db.commit()
        # For INTEGER PK tables, lastrowid is the new id.
        # For TEXT PK tables, fall back to the payload id.
        row_id = cursor.lastrowid
        if row_id and "id" not in mapped:
            return await self.get_by_id(row_id)
        return await self.get_by_id(payload.get("id"))

    async def get_by_id(self, item_id):
        db = get_db()
        cursor = await db.execute(self._query("get_by_id"), (item_id,))
        row = await cursor.fetchone()
        return self._row_to_model(row)

    async def delete_by_id(self, item_id):
        db = get_db()
        await db.execute(self._query("delete_by_id"), (item_id,))
        await db.commit()

    async def update(self, item_id, **payload):
        db = get_db()
        mapped = self._map_payload(payload)
        set_clause = ", ".join(f"{col}=?" for col in mapped)
        params = list(mapped.values()) + [item_id]
        sql = f"UPDATE {self.table_name} SET {set_clause} WHERE id=?"
        await db.execute(sql, params)
        await db.commit()
        return await self.get_by_id(item_id)

    async def first(self, **filters):
        db = get_db()
        where_clause = " AND ".join(f"{k}=?" for k in filters)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT 1"
        cursor = await db.execute(sql, tuple(filters.values()))
        row = await cursor.fetchone()
        return self._row_to_model(row)

    async def list(self, **filters):
        db = get_db()
        where_clause = " AND ".join(f"{k}=?" for k in filters)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        cursor = await db.execute(sql, tuple(filters.values()))
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def list_all(self, *, order_by=None):
        db = get_db()
        sql = f"SELECT * FROM {self.table_name}"
        if order_by:
            sql += f" ORDER BY {', '.join(order_by)}"
        cursor = await db.execute(sql)
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def update_or_create(self, **kwargs):
        raise NotImplementedError("Use a specific upsert method instead.")

    async def list_by_ids(self, ids: list):
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        db = get_db()
        sql = f"SELECT * FROM {self.table_name} WHERE id IN ({placeholders})"
        cursor = await db.execute(sql, ids)
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]
