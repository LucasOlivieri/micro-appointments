from __future__ import annotations

from tortoise import Model


class BaseRepository:
    model: type[Model] | None = None

    async def create(self, **payload):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.create(**payload)

    async def update(self, item_id, **payload):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        await self.model.filter(id=item_id).update(**payload)
        return await self.model.get(id=item_id)

    async def delete_by_id(self, item_id):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.filter(id=item_id).delete()

    async def get_by_id(self, item_id):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.filter(id=item_id).first()

    async def first(self, **filters):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.filter(**filters).first()

    async def list(self, **filters):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.filter(**filters).all()

    async def list_all(self, *, order_by=None):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        query = self.model.all()
        if order_by:
            query = query.order_by(*order_by)
        return await query.all()

    async def update_or_create(self, **kwargs):
        if self.model is None:
            raise NotImplementedError("Repository model is not configured.")
        return await self.model.update_or_create(**kwargs)
