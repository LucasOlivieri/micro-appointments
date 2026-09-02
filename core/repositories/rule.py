from __future__ import annotations

from core.models import Rule
from core.repositories.base import BaseRepository


class RuleRepository(BaseRepository):
    model = Rule

    async def list_by_user(self, user_id):
        return await self.model.filter(user_id=user_id).order_by("id").all()
