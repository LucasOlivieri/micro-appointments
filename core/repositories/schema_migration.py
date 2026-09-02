from __future__ import annotations

from core.models import SchemaMigration
from core.repositories.base import BaseRepository


class SchemaMigrationRepository(BaseRepository):
    model = SchemaMigration
