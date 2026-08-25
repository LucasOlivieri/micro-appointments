from datetime import datetime, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .appointments import AppointmentsService


DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


def _database_blocked_times(user_id, bookings_only=False):
    service = AppointmentsService(DATABASE_PATH)
    return service.list_blocked_times(user_id, bookings_only)


def load_user(user_id):
    """Load a user and its scheduling data from SQLite."""
    service = AppointmentsService(DATABASE_PATH)
    user = service.db["users"].get(user_id)
    user["rules"] = list(service.db.query(
        "SELECT id, user, weekday, start_time, end_time "
        "FROM rules WHERE user = :user_id ORDER BY id",
        {"user_id": user_id},
    ))
    user["appointment_types"] = list(service.db.query(
        "SELECT id, user, name, duration_minutes "
        "FROM appointment_types WHERE user = :user_id ORDER BY id",
        {"user_id": user_id},
    ))
    user["blocked_time"] = _database_blocked_times(user_id)
    return user


def _refresh_database_blocked_times(user):
    if "id" in user:
        user["blocked_time"] = [
            block for block in user.get("blocked_time", [])
            if not (
                block.get("reason") == "booked"
                and "start" in block
                and "end" in block
            )
        ]
        user["blocked_time"].extend(
            _database_blocked_times(user["id"], bookings_only=True)
        )


def get_appointment_type(user, appointment_type):
    for appt in user["appointment_types"]:
        if appt["name"].lower() == appointment_type.lower():
            return appt
    raise ValueError(f"Unknown appointment type: {appointment_type}")


def is_blocked(user, start, end):
    for block in user.get("blocked_time", []):

        # Exact datetime interval
        if (
            "start" in block and "end" in block
        ) or (
            "start_datetime" in block and "end_datetime" in block
        ):
            block_start_value = block["start"] if "start" in block else block["start_datetime"]
            block_end_value = block["end"] if "end" in block else block["end_datetime"]
            block_start = datetime.fromisoformat(
                block_start_value
            )
            block_end = datetime.fromisoformat(
                block_end_value
            )

            if start < block_end and end > block_start:
                return True

        # Entire date range
        elif "start_date" in block:
            block_start = datetime.combine(
                date.fromisoformat(block["start_date"]),
                time.min,
                tzinfo=start.tzinfo,
            )

            block_end = datetime.combine(
                date.fromisoformat(block["end_date"]) + timedelta(days=1),
                time.min,
                tzinfo=start.tzinfo,
            )

            if start < block_end and end > block_start:
                return True

        # Recurring month
        elif "condition" in block:
            month = block["condition"].get("month")

            if month and start.strftime("%B").lower() == month.lower():
                return True

    return False


def get_working_hours(user, day):
    """
    Return (start, end) for a given date, or None if unavailable.
    """
    weekday = day.weekday()

    for rule in user["rules"]:
        if rule["weekday"] == weekday:
            tz = ZoneInfo(user["timezone"])

            start = datetime.combine(
                day,
                time.fromisoformat(rule["start_time"]),
                tzinfo=tz,
            )
            end = datetime.combine(
                day,
                time.fromisoformat(rule["end_time"]),
                tzinfo=tz,
            )

            return start, end

    return None


def get_next_free_slots(
    user,
    appointment_type,
    nr_slots=5,
    from_datetime=None,
):
    appt = get_appointment_type(user, appointment_type)
    duration = timedelta(minutes=appt["duration_minutes"])

    tz = ZoneInfo(user["timezone"])

    if from_datetime is None:
        from_datetime = datetime.now(tz)

    if from_datetime.tzinfo is None:
        from_datetime = from_datetime.replace(tzinfo=tz)

    slots = []
    day = from_datetime.date()

    while len(slots) < nr_slots:
        working_hours = get_working_hours(user, day)

        if working_hours:
            working_start, working_end = working_hours

            # IMPORTANT:
            # Always start the slot grid from working_start.
            current = working_start

            while current + duration <= working_end:
                slot_end = current + duration

                # Don't return slots that have already started
                if (
                    current >= from_datetime
                    and not is_blocked(user, current, slot_end)
                ):
                    slots.append({
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                        "appointment_type": appt["name"],
                    })

                    if len(slots) >= nr_slots:
                        break

                # Fixed slot grid
                current += duration

        day += timedelta(days=1)

    return slots


def book_appointment(
    user,
    appointment_type,
    start_datetime,
):
    """
    Book an appointment by adding a 'booked' blocked_time entry.
    """
    appt = get_appointment_type(user, appointment_type)
    duration = timedelta(minutes=appt["duration_minutes"])

    tz = ZoneInfo(user["timezone"])

    if isinstance(start_datetime, str):
        start_datetime = datetime.fromisoformat(start_datetime)

    if start_datetime.tzinfo is None:
        start_datetime = start_datetime.replace(tzinfo=tz)

    end_datetime = start_datetime + duration

    _refresh_database_blocked_times(user)

    # Must be inside working hours
    working_hours = get_working_hours(user, start_datetime.date())

    if not working_hours:
        raise ValueError("No working hours on this day")

    working_start, working_end = working_hours

    if start_datetime < working_start or end_datetime > working_end:
        raise ValueError("Appointment is outside working hours")

    # Prevent double booking
    if is_blocked(user, start_datetime, end_datetime):
        raise ValueError("Time slot is already blocked")

    booking = {
        "reason": "booked",
        "start": start_datetime.isoformat(),
        "end": end_datetime.isoformat(),
        "appointment_type": appt["name"],
    }

    if "id" not in user:
        raise ValueError("User must have an id to book an appointment")

    service = AppointmentsService(DATABASE_PATH)
    created = service.create_blocked_time({
        "user": user["id"],
        "reason": booking["reason"],
        "start": booking["start"],
        "end": booking["end"],
        "appointment_type": booking["appointment_type"],
    })
    booking["id"] = created["id"]
    user.setdefault("blocked_time", []).append(booking)

    return booking
