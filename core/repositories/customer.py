from __future__ import annotations

from core.models import Customer
from core.repositories.base import BaseRepository


class CustomerRepository(BaseRepository):
    model = Customer

    async def get_by_phone(self, phone):
        return await self.model.filter(phone=phone).first()

    async def upsert(self, customer_id, phone, name, info=None):
        return await self.model.update_or_create(
            id=customer_id,
            defaults={"phone": phone, "name": name, "info": info},
        )

    async def list_by_ids(self, ids):
        if not ids:
            return []
        return await self.model.filter(id__in=list(ids)).all()
