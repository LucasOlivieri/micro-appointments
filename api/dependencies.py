from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from core.main import load_user
from core.services.appointments import AppointmentsService

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


def _not_found(detail: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def _load_user_or_404(user_id: str, database_path: Path) -> dict[str, Any]:  # type: ignore
    try:
        return await load_user(user_id, database_path=database_path)
    except KeyError, TypeError:
        _not_found(f"User not found: {user_id}")


def _service(database_path: Path) -> AppointmentsService:
    return AppointmentsService(database_path)


def _response_appointment(appointment: dict[str, Any], user_id: str):
    if "user" in appointment:
        return appointment
    return {**appointment, "user": user_id}
