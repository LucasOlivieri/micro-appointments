from __future__ import annotations

from tortoise.expressions import Q

from core.models import BlockedTime
from core.repositories.base import BaseRepository


class BlockedTimeRepository(BaseRepository):
    model = BlockedTime

    async def list_for_user(self, user_id, *, bookings_only=False):
        query = self.model.filter(user_id=user_id)
        if bookings_only:
            query = query.filter(~Q(appointment_type=None))
        return await query.order_by("start", "id").all()

    async def list_booked_for_user(self, user_id, appointment_type=None):
        query = self.model.filter(user_id=user_id, reason="booked")
        if appointment_type is not None:
            query = query.filter(appointment_type__iexact=appointment_type)
        return await query.order_by("start", "id").all()

    async def get_booked_by_user(self, user_id, appointment_id):
        return await self.model.filter(
            id=appointment_id,
            user_id=user_id,
            reason="booked",
        ).first()

    async def list_rows_for_user(self, user_id):
        return await self.model.filter(user_id=user_id).order_by("id").all()
