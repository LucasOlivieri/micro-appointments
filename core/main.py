from pathlib import Path

from .services.appointments import AppointmentsService

DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


def _service(database_path=None):
    if database_path is None:
        database_path = DATABASE_PATH
    return AppointmentsService(database_path)


async def _database_blocked_times(
    user_id,
    bookings_only=False,
    database_path=None,
):
    return await _service(database_path)._database_blocked_times(user_id, bookings_only)


async def load_user(user_id, database_path=None):
    """Compatibility wrapper for legacy imports."""
    return await _service(database_path).load_user(user_id)


async def _refresh_database_blocked_times(
    user,
    database_path=None,
    exclude_start=None,
):
    await _service(database_path)._refresh_database_blocked_times(user, exclude_start)


def get_appointment_type(user, appointment_type):
    return _service().get_appointment_type(user, appointment_type)


def is_blocked(user, start, end):
    return _service().is_blocked(user, start, end)


def get_working_hours(user, day):
    return _service().get_working_hours(user, day)


def get_next_free_slots(
    user,
    appointment_type,
    nr_slots=5,
    from_datetime=None,
):
    return _service().get_next_free_slots(
        user,
        appointment_type,
        nr_slots=nr_slots,
        from_datetime=from_datetime,
    )


async def book_appointment(
    user,
    appointment_type,
    start,
    database_path=None,
    exclude_start=None,
    customer_name=None,
    customer_phone=None,
):
    service = _service(database_path)
    return await service.book_appointment(
        user,
        appointment_type,
        start,
        exclude_start=exclude_start,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
