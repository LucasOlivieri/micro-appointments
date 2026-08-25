from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlite_utils.db import NotFoundError

from core.appointments import AppointmentsService
from core.main import book_appointment, get_next_free_slots, load_user


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


class AppointmentCreate(BaseModel):
    user_id: str = Field(description="The ID of the user who owns the appointment")
    appointment_type: str = Field(min_length=1, description="Appointment type name")
    start: datetime = Field(description="Appointment start, preferably with a timezone")
    name: str = Field(min_length=1, description="Customer name")
    phone: str = Field(min_length=1, description="Customer phone number")


class AppointmentUpdate(BaseModel):
    user_id: str = Field(description="The ID of the user who owns the appointment")
    appointment_type: str | None = Field(default=None, min_length=1)
    start: datetime | None = None


class Appointment(BaseModel):
    id: int
    user: str
    reason: str
    start: str
    end: str
    appointment_type: str
    name: str | None = None
    phone: str | None = None


class AvailableSlot(BaseModel):
    start: str
    end: str
    appointment_type: str


class AvailableAppointmentType(BaseModel):
    name: str
    duration_minutes: int


def _not_found(detail: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _load_user_or_404(user_id: str, database_path: Path) -> dict[str, Any]:
    try:
        return load_user(user_id, database_path=database_path)
    except (KeyError, NotFoundError, TypeError):
        _not_found(f"User not found: {user_id}")


def _service(database_path: Path) -> AppointmentsService:
    return AppointmentsService(database_path)


def _response_appointment(appointment: dict[str, Any], user_id: str):
    if "user" in appointment:
        return appointment
    return {**appointment, "user": user_id}


def create_app(database_path: str | Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    database_path = Path(database_path)
    app = FastAPI(
        title="Appointments API",
        description=(
            "Create, inspect, reschedule, and cancel appointments. "
            "All appointment times are ISO 8601 datetimes."
        ),
        version="1.0.0",
    )

    @app.get(
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

    @app.get(
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

    @app.get(
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

    @app.post(
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

    @app.get(
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

    @app.patch(
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

    @app.delete(
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

    return app


app = create_app()
