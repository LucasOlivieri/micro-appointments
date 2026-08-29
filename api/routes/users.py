from pathlib import Path

from fastapi import APIRouter, Query

from api.dependencies import _load_user_or_404, _service
from api.schemas import AvailableAppointmentType, UserOut


def create_router(database_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/users",
        response_model=list[UserOut],
        summary="List users",
        description="List users whose calendars can be searched or booked.",
    )
    def list_users():
        service = _service(database_path)
        rows = list(service.db.query(
            """
            SELECT
                u.id,
                u.name,
                u.timezone,
                at.name AS appointment_type_name,
                at.duration_minutes
            FROM users u
            LEFT JOIN appointment_types at ON at.user = u.id
            ORDER BY u.name, u.id, at.id
            """
        ))

        users_by_id: dict[str, dict] = {}
        for row in rows:
            user_id = row["id"]
            user = users_by_id.setdefault(
                user_id,
                {
                    "id": row["id"],
                    "name": row["name"],
                    "timezone": row["timezone"],
                    "available_appointment_types": [],
                },
            )
            if row["appointment_type_name"] is not None:
                user["available_appointment_types"].append(
                    {
                        "name": row["appointment_type_name"],
                        "duration_minutes": row["duration_minutes"],
                    }
                )

        return list(users_by_id.values())

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
