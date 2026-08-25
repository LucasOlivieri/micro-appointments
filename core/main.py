from datetime import datetime, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .appointments import AppointmentsService


DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"


def _database_blocked_times(
    user_id, bookings_only=False, database_path=None,
):
    if database_path is None:
        database_path = DATABASE_PATH
    service = AppointmentsService(database_path)
    return service.list_blocked_times(user_id, bookings_only)


def load_user(user_id, database_path=None):
    """Load a user and its scheduling data from SQLite."""
    if database_path is None:
        database_path = DATABASE_PATH
    service = AppointmentsService(database_path)
    user = service.db["users"].get(user_id)
    user["rules"] = list(service.db.query(
        "SELECT id, user, weekday, start, end "
        "FROM rules WHERE user = :user_id ORDER BY id",
        {"user_id": user_id},
    ))
    user["appointment_types"] = list(service.db.query(
        "SELECT id, user, name, duration_minutes "
        "FROM appointment_types WHERE user = :user_id ORDER BY id",
        {"user_id": user_id},
    ))
    user["blocked_time"] = _database_blocked_times(
        user_id, database_path=database_path,
    )
    return user


def _refresh_database_blocked_times(
    user, database_path=None, exclude_start=None,
):
    if database_path is None:
        database_path = DATABASE_PATH
    if "id" in user:
        user["blocked_time"] = [
            block for block in user.get("blocked_time", [])
            if not (
                block.get("reason") == "booked"
                and "start" in block
                and "end" in block
            )
        ]
        bookings = _database_blocked_times(
            user["id"], bookings_only=True, database_path=database_path,
        )
        if exclude_start is not None:
            bookings = [
                booking for booking in bookings
                if booking.get("start") != exclude_start
            ]
        user["blocked_time"].extend(bookings)


def get_appointment_type(user, appointment_type):
    for appt in user["appointment_types"]:
        if appt["name"].lower() == appointment_type.lower():
            return appt
    raise ValueError(f"Unknown appointment type: {appointment_type}")


def is_blocked(user, start, end):
    for block in user.get("blocked_time", []):

        # Exact datetime interval
        if "start" in block and "end" in block:
            block_start_value = block["start"]
            block_end_value = block["end"]
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
                time.fromisoformat(rule["start"]),
                tzinfo=tz,
            )
            end = datetime.combine(
                day,
                time.fromisoformat(rule["end"]),
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
    start,
    database_path=None,
    exclude_start=None,
    customer_name=None,
    customer_phone=None,
):
    """
    Book an appointment by adding a 'booked' blocked_time entry.
    """
    if database_path is None:
        database_path = DATABASE_PATH
    appt = get_appointment_type(user, appointment_type)
    duration = timedelta(minutes=appt["duration_minutes"])

    tz = ZoneInfo(user["timezone"])

    if isinstance(start, str):
        start = datetime.fromisoformat(start)

    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)

    end = start + duration

    _refresh_database_blocked_times(user, database_path, exclude_start)

    # Must be inside working hours
    working_hours = get_working_hours(user, start.date())

    if not working_hours:
        raise ValueError("No working hours on this day")

    working_start, working_end = working_hours

    if start < working_start or end > working_end:
        raise ValueError("Appointment is outside working hours")

    # Prevent double booking
    if is_blocked(user, start, end):
        raise ValueError("Time slot is already blocked")

    booking = {
        "reason": "booked",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "appointment_type": appt["name"],
    }

    if "id" not in user:
        raise ValueError("User must have an id to book an appointment")

    if customer_name is not None and not customer_name.strip():
        raise ValueError("Customer name is required")
    if customer_phone is not None and not customer_phone.strip():
        raise ValueError("Customer phone is required")
    if (customer_name is None) != (customer_phone is None):
        raise ValueError("Customer name and phone are required together")

    service = AppointmentsService(database_path)
    customer_id = None
    if customer_name is not None:
        customer = next(
            service.db.query(
                "SELECT id FROM customer WHERE phone = :phone",
                {"phone": customer_phone.strip()},
            ),
            None,
        )
        customer_phone = customer_phone.strip()
        customer_name = customer_name.strip()
        if customer is None:
            service.db["customer"].insert({
                "id": customer_phone,
                "phone": customer_phone,
                "name": customer_name,
            })
        else:
            service.db.execute(
                "UPDATE customer SET id = :id, name = :name "
                "WHERE phone = :phone",
                {
                    "id": customer_phone,
                    "name": customer_name,
                    "phone": customer_phone,
                },
            )
        customer_id = customer_phone
    created = service.create_blocked_time({
        "user": user["id"],
        "reason": booking["reason"],
        "start": booking["start"],
        "end": booking["end"],
        "appointment_type": booking["appointment_type"],
        **({"customer": customer_id} if customer_id is not None else {}),
    })
    booking["id"] = created["id"]
    if customer_id is not None:
        booking["name"] = customer_name
        booking["phone"] = customer_phone
    user.setdefault("blocked_time", []).append(booking)

    return booking
