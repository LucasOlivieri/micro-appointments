from pathlib import Path

from fastapi import APIRouter, Query

from api.dependencies import _load_user_or_404, _service
from api.schemas import AvailableAppointmentType, User


def create_router(database_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/users",
        response_model=list[User],
        summary="List users",
        description="List users whose calendars can be searched or booked.",
    )
    def list_users():
        return list(_service(database_path).db.query(
            "SELECT id, name, timezone FROM users ORDER BY name, id"
        ))

    @router.get(
        "/appointments/available-types",
        response_model=list[AvailableAppointmentType],
        summary="List available appointment types",
        description="List the appointment types configured for a user's calendar.",
    )
    def available_appointment_types(
        user_id: str = Query(description="The user whose appointment types to list"),
    ):
        user = _load_user_or_404(user_id, database_path)
        return [
            {
                "name": appointment_type["name"],
                "duration_minutes": appointment_type["duration_minutes"],
            }
            for appointment_type in user["appointment_types"]
        ]

    return router
