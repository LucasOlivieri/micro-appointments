from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from api.dependencies import (
    _load_user_or_404,
    _not_found,
    _response_appointment,
    _service,
)
from api.schemas import (
    Appointment,
    AppointmentCreate,
    AppointmentUpdate,
    AvailableSlot,
)
from core.main import book_appointment, get_next_free_slots


def create_router(database_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/appointments",
        response_model=list[Appointment],
        summary="List appointments",
        description="List a user's appointments, optionally filtered by type.",
    )
    def list_appointments(
        user_id: str = Query(description="The user whose appointments to list"),
        appointment_type: str | None = Query(
            default=None, description="Case-insensitive appointment type filter"
        ),
    ):
        _load_user_or_404(user_id, database_path)
        return _service(database_path).list_appointments(user_id, appointment_type)

    @router.get(
        "/appointments/available-slots",
        response_model=list[AvailableSlot],
        summary="Find available appointment slots",
        description=(
            "Return the next available slots for an appointment type. "
            "Results respect the user's timezone, working hours, and blocked times."
        ),
    )
    def available_slots(
        user_id: str = Query(description="The user whose calendar to search"),
        appointment_type: str = Query(
            min_length=1, description="Appointment type name"
        ),
        nr_slots: int = Query(
            default=5, ge=1, le=50,
            description="Number of slots to return, from 1 to 50",
        ),
        from_datetime: datetime | None = Query(
            default=None,
            description="Only return slots starting at or after this ISO 8601 datetime",
        ),
    ):
        user = _load_user_or_404(user_id, database_path)
        try:
            return get_next_free_slots(
                user,
                appointment_type,
                nr_slots=nr_slots,
                from_datetime=from_datetime,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post(
        "/appointments",
        response_model=Appointment,
        status_code=status.HTTP_201_CREATED,
        summary="Create an appointment",
        description="Create an appointment after checking type, hours, and conflicts.",
    )
    def create_appointment(payload: AppointmentCreate):
        user = _load_user_or_404(payload.user_id, database_path)
        try:
            booking = book_appointment(
                user,
                payload.appointment_type,
                payload.start,
                database_path=database_path,
                customer_name=payload.name,
                customer_phone=payload.phone,
            )
            return _response_appointment(booking, payload.user_id)
        except ValueError as error:
            message = str(error)
            code = status.HTTP_409_CONFLICT if "already blocked" in message else 422
            raise HTTPException(status_code=code, detail=message) from error

    @router.get(
        "/appointments/{appointment_id}",
        response_model=Appointment,
        summary="Get an appointment",
    )
    def get_appointment(
        appointment_id: int,
        user_id: str = Query(description="The owner of the appointment"),
    ):
        _load_user_or_404(user_id, database_path)
        appointment = _service(database_path).get_appointment(user_id, appointment_id)
        if appointment is None:
            _not_found(f"Appointment not found: {appointment_id}")
        return appointment

    @router.patch(
        "/appointments/{appointment_id}",
        response_model=Appointment,
        summary="Reschedule an appointment",
        description="Change an appointment's start or type after full conflict validation.",
    )
    def update_appointment(appointment_id: int, payload: AppointmentUpdate):
        user = _load_user_or_404(payload.user_id, database_path)
        service = _service(database_path)
        existing = service.get_appointment(payload.user_id, appointment_id)
        if existing is None:
            _not_found(f"Appointment not found: {appointment_id}")
        if payload.start is None and payload.appointment_type is None:
            raise HTTPException(status_code=422, detail="Provide start or appointment_type")

        user["blocked_time"] = [
            block for block in user.get("blocked_time", [])
            if block.get("id") != appointment_id
            and block.get("start") != existing["start"]
        ]
        appointment_type = payload.appointment_type or existing["appointment_type"]
        start = payload.start or datetime.fromisoformat(existing["start"])
        try:
            replacement = book_appointment(
                user,
                appointment_type,
                start,
                database_path=database_path,
                exclude_start=existing["start"],
                customer_name=existing.get("name"),
                customer_phone=existing.get("phone"),
            )
        except ValueError as error:
            message = str(error)
            code = status.HTTP_409_CONFLICT if "already blocked" in message else 422
            raise HTTPException(status_code=code, detail=message) from error
        service.delete_appointment(payload.user_id, appointment_id)
        return _response_appointment(replacement, payload.user_id)

    @router.delete(
        "/appointments/{appointment_id}",
        response_model=Appointment,
        summary="Cancel an appointment",
        description="Permanently remove an appointment belonging to the specified user.",
    )
    def delete_appointment(
        appointment_id: int,
        user_id: str = Query(description="The owner of the appointment"),
    ):
        _load_user_or_404(user_id, database_path)
        deleted = _service(database_path).delete_appointment(user_id, appointment_id)
        if deleted is None:
            _not_found(f"Appointment not found: {appointment_id}")
        return deleted

    return router
