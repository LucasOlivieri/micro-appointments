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
    async def list_users():
        service = _service(database_path)
        users = await service.list_users()
        response = []
        for user in users:
            appointment_types = await service.list_appointment_types(user["id"])
            response.append(
                {
                    "id": user["id"],
                    "name": user["name"],
                    "timezone": user["timezone"],
                    "available_appointment_types": [
                        {
                            "name": appointment_type["name"],
                            "duration_minutes": appointment_type["duration_minutes"],
                            "advance_notice_minutes": appointment_type.get(
                                "advance_notice_minutes"
                            ),
                        }
                        for appointment_type in appointment_types
                    ],
                }
            )

        return response

    @router.get(
        "/appointments/available-types",
        response_model=list[AvailableAppointmentType],
        summary="List available appointment types",
        description="List the appointment types configured for a user's calendar.",
    )
    async def available_appointment_types(
        user_id: str = Query(description="The user whose appointment types to list"),
    ):
        user = await _load_user_or_404(user_id, database_path)
        return [
            {
                "name": appointment_type["name"],
                "duration_minutes": appointment_type["duration_minutes"],
                "advance_notice_minutes": appointment_type.get(
                    "advance_notice_minutes"
                ),
            }
            for appointment_type in user["appointment_types"]
        ]

    return router
