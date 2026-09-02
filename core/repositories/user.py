from __future__ import annotations

from core.models import User
from core.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def upsert(self, user_id, defaults):
        return await self.model.update_or_create(id=user_id, defaults=defaults)

    async def list_all(self):
        return await self.model.all().order_by("name", "id")
