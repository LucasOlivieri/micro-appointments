from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from core.models import AppointmentType, BlockedTime, Rule, User
from core.recurrence import rule_applies_on
from core.repositories.appointment_type import AppointmentTypeRepository
from core.repositories.blocked_time import BlockedTimeRepository
from core.repositories.customer import CustomerRepository
from core.repositories.rule import RuleRepository
from core.repositories.user import UserRepository

CREATED = "created"
UPDATED = "updated"
DELETED = "deleted"
_ACTION_HANDLERS: defaultdict = defaultdict(list)


def onaction(action):
    """Register a callback for an appointments service action."""

    def decorator(handler):
        _ACTION_HANDLERS[action].append(handler)
        return handler

    return decorator


async def _dispatch(action, item):
    for handler in _ACTION_HANDLERS[action]:
        result = handler(item)
        if hasattr(result, "__await__"):
            await result


def _serialize_blocked_time(item: BlockedTime) -> dict:
    return {
        "id": item.id,
        "user": item.user_id,
        "reason": item.reason,
        "start": item.start,
        "end": item.end,
        "appointment_type": item.appointment_type,
        "customer": item.customer,
        "google_event_id": item.google_event_id,
    }


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "timezone": user.timezone,
    }


def _serialize_rule(rule: Rule) -> dict:
    return {
        "id": rule.id,
        "user": rule.user_id,
        "weekday": rule.weekday,
        "start": rule.start,
        "end": rule.end,
        "rrule": rule.rrule,
        "dtstart": rule.dtstart,
        "exclude_dates": rule.exclude_dates,
    }


def _serialize_appointment_type(item: AppointmentType) -> dict:
    return {
        "id": item.id,
        "user": item.user_id,
        "name": item.name,
        "duration_minutes": item.duration_minutes,
        "advance_notice_minutes": item.advance_notice_minutes,
    }


class AppointmentsService:
    def __init__(
        self,
        path,
        *,
        users: UserRepository | None = None,
        rules: RuleRepository | None = None,
        appointment_types: AppointmentTypeRepository | None = None,
        customers: CustomerRepository | None = None,
        blocked_times: BlockedTimeRepository | None = None,
    ):
        self.path = str(path)
        self.users = users or UserRepository()
        self.rules = rules or RuleRepository()
        self.appointment_types = appointment_types or AppointmentTypeRepository()
        self.customers = customers or CustomerRepository()
        self.blocked_times = blocked_times or BlockedTimeRepository()

    async def list_blocked_times(self, user_id, bookings_only=False):
        rows = await self.blocked_times.list_for_user(
            user_id, bookings_only=bookings_only
        )

        blocked_times = []
        for row in rows:
            if row.appointment_type:
                blocked_times.append(
                    {
                        "reason": row.reason,
                        "start": row.start,
                        "end": row.end,
                        "appointment_type": row.appointment_type,
                    }
                )
            elif row.start and row.end:
                blocked_times.append(
                    {
                        "reason": row.reason,
                        "start_date": row.start[:10],
                        "end_date": row.end[:10],
                    }
                )
        return blocked_times

    async def create_user(self, payload):
        user = await self.users.create(**dict(payload))
        return _serialize_user(user)

    async def upsert_user(self, payload):
        body = dict(payload)
        user_id = body["id"]
        defaults = {
            "name": body.get("name"),
            "email": body.get("email"),
            "timezone": body.get("timezone") or "America/Argentina/Buenos_Aires",
        }
        user, _ = await self.users.upsert(user_id, defaults)
        return _serialize_user(user)

    async def get_user(self, user_id):
        user = await self.users.get_by_id(user_id)
        if user is None:
            return None
        return _serialize_user(user)

    async def list_users(self):
        rows = await self.users.list_all()
        return [_serialize_user(row) for row in rows]

    async def create_rule(self, payload):
        body = dict(payload)
        if "user" in body and "user_id" not in body:
            body["user_id"] = body.pop("user")
        item = await self.rules.create(**body)
        return _serialize_rule(item)

    async def list_rules(self, user_id):
        rows = await self.rules.list_by_user(user_id)
        return [_serialize_rule(row) for row in rows]

    async def create_appointment_type(self, payload):
        body = dict(payload)
        if "user" in body and "user_id" not in body:
            body["user_id"] = body.pop("user")
        item = await self.appointment_types.create(**body)
        return _serialize_appointment_type(item)

    async def list_appointment_types(self, user_id):
        rows = await self.appointment_types.list_by_user(user_id)
        return [_serialize_appointment_type(row) for row in rows]

    async def find_customer_by_phone(self, phone):
        customer = await self.customers.get_by_phone(phone)
        if customer is None:
            return None
        return {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "info": customer.info,
        }

    async def upsert_customer(self, customer_id, phone, name):
        customer, _ = await self.customers.upsert(customer_id, phone, name)
        return {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "info": customer.info,
        }

    async def list_appointments(
        self,
        user_id,
        appointment_type=None,
        from_datetime=None,
        to_datetime=None,
        customer_phone=None,
    ):
        rows = await self.blocked_times.list_booked_for_user(
            user_id,
            appointment_type=appointment_type,
        )

        customer_ids = {row.customer for row in rows if row.customer}
        customers = {}
        if customer_ids:
            for c in await self.customers.list_by_ids(list(customer_ids)):
                customers[c.id] = c

        appointments = []
        for row in rows:
            if customer_phone is not None and row.customer != customer_phone:
                continue
            start = datetime.fromisoformat(row.start)
            if from_datetime is not None:
                bound = from_datetime
                if bound.tzinfo is None:
                    bound = bound.replace(tzinfo=start.tzinfo)
                if start < bound:
                    continue
            if to_datetime is not None:
                bound = to_datetime
                if bound.tzinfo is None:
                    bound = bound.replace(tzinfo=start.tzinfo)
                if start > bound:
                    continue
            c = customers.get(row.customer) if row.customer else None
            appointments.append(
                {
                    "id": row.id,
                    "user": row.user_id,
                    "reason": row.reason,
                    "start": row.start,
                    "end": row.end,
                    "appointment_type": row.appointment_type,
                    "name": c.name if c else None,
                    "phone": c.phone if c else None,
                }
            )
        return appointments

    async def get_appointment(self, user_id, appointment_id):
        row = await self.blocked_times.get_booked_by_user(user_id, appointment_id)
        if row is None:
            return None

        c = await self.customers.get_by_id(row.customer) if row.customer else None
        return {
            "id": row.id,
            "user": row.user_id,
            "reason": row.reason,
            "start": row.start,
            "end": row.end,
            "appointment_type": row.appointment_type,
            "name": c.name if c else None,
            "phone": c.phone if c else None,
            "google_event_id": row.google_event_id,
        }

    async def delete_appointment(self, user_id, appointment_id, customer_phone):
        appointment = await self.get_appointment(user_id, appointment_id)
        if appointment is None:
            return None
        if appointment["phone"] != customer_phone:
            raise PermissionError("Only the customer can cancel this appointment")

        await self.blocked_times.delete_by_id(appointment_id)
        await _dispatch(DELETED, appointment)
        return appointment

    async def create_blocked_time(self, item):
        payload = dict(item)
        if "user" in payload and "user_id" not in payload:
            payload["user_id"] = payload.pop("user")

        created = await self.blocked_times.create(**payload)
        result = _serialize_blocked_time(created)
        await _dispatch(CREATED, result)
        return result

    async def update_blocked_time(self, item_id, changes):
        payload = dict(changes)
        if "user" in payload and "user_id" not in payload:
            payload["user_id"] = payload.pop("user")

        updated = await self.blocked_times.update(item_id, **payload)
        result = _serialize_blocked_time(updated)
        await _dispatch(UPDATED, result)
        return result

    async def list_blocked_time_rows(self, user_id):
        rows = await self.blocked_times.list_rows_for_user(user_id)
        return [_serialize_blocked_time(row) for row in rows]

    async def _database_blocked_times(self, user_id, bookings_only=False):
        return await self.list_blocked_times(user_id, bookings_only)

    async def load_user(self, user_id):
        user = await self.get_user(user_id)
        if user is None:
            raise KeyError(user_id)
        user["rules"] = await self.list_rules(user_id)
        user["appointment_types"] = await self.list_appointment_types(user_id)
        user["blocked_time"] = await self._database_blocked_times(user_id)
        return user

    async def _refresh_database_blocked_times(self, user, exclude_start=None):
        if "id" in user:
            user["blocked_time"] = [
                block
                for block in user.get("blocked_time", [])
                if not (
                    block.get("reason") == "booked"
                    and "start" in block
                    and "end" in block
                )
            ]
            bookings = await self._database_blocked_times(
                user["id"], bookings_only=True
            )
            if exclude_start is not None:
                bookings = [
                    booking
                    for booking in bookings
                    if booking.get("start") != exclude_start
                ]
            user["blocked_time"].extend(bookings)

    def get_appointment_type(self, user, appointment_type):
        for appt in user["appointment_types"]:
            if appt["name"].lower() == appointment_type.lower():
                return appt
        raise ValueError(f"Unknown appointment type: {appointment_type}")

    def is_blocked(self, user, start, end):
        for block in user.get("blocked_time", []):
            if "start" in block and "end" in block:
                block_start_value = block["start"]
                block_end_value = block["end"]
                block_start = datetime.fromisoformat(block_start_value)
                block_end = datetime.fromisoformat(block_end_value)

                if start < block_end and end > block_start:
                    return True
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
            elif "condition" in block:
                month = block["condition"].get("month")
                if month and start.strftime("%B").lower() == month.lower():
                    return True

        return False

    def get_working_hours(self, user, day):
        for rule in user["rules"]:
            tz = ZoneInfo(user["timezone"])
            if rule_applies_on(rule, day, tz):
                start = datetime.combine(
                    day, time.fromisoformat(rule["start"]), tzinfo=tz
                )
                end = datetime.combine(day, time.fromisoformat(rule["end"]), tzinfo=tz)
                return start, end
        return None

    def get_next_free_slots(
        self, user, appointment_type, nr_slots=5, from_datetime=None
    ):
        appt = self.get_appointment_type(user, appointment_type)
        duration = timedelta(minutes=appt["duration_minutes"])
        tz = ZoneInfo(user["timezone"])

        if from_datetime is None:
            from_datetime = datetime.now(tz)
        if from_datetime.tzinfo is None:
            from_datetime = from_datetime.replace(tzinfo=tz)

        slots = []
        from_datetime = from_datetime.astimezone(tz)
        day = from_datetime.date()

        # Compute the earliest allowed booking time based on advance notice
        advance_minutes = appt.get("advance_notice_minutes")
        earliest_allowed = None
        if advance_minutes is not None:
            earliest_allowed = datetime.now(tz) + timedelta(minutes=advance_minutes)

        for _ in range(366):
            if len(slots) >= nr_slots:
                break
            working_hours = self.get_working_hours(user, day)
            if working_hours:
                working_start, working_end = working_hours
                current = working_start
                while current + duration <= working_end:
                    slot_end = current + duration
                    if current >= from_datetime and not self.is_blocked(
                        user, current, slot_end
                    ):
                        # Skip slots that violate the advance booking deadline
                        if earliest_allowed is not None and current < earliest_allowed:
                            current += duration
                            continue
                        slots.append(
                            {
                                "start": current.isoformat(),
                                "end": slot_end.isoformat(),
                                "appointment_type": appt["name"],
                            }
                        )
                        if len(slots) >= nr_slots:
                            break
                    current += duration
            day += timedelta(days=1)
        return slots

    def get_daily_availability(self, user, appointment_type, target_date):
        appt = self.get_appointment_type(user, appointment_type)
        duration = timedelta(minutes=appt["duration_minutes"])
        working_hours = self.get_working_hours(user, target_date)
        timezone = ZoneInfo(user["timezone"])
        day_start = datetime.combine(target_date, time.min, tzinfo=timezone)
        day_end = day_start + timedelta(days=1)
        blocked_periods = []
        for block in user.get("blocked_time", []):
            if "start" in block and "end" in block:
                block_start = datetime.fromisoformat(block["start"])
                block_end = datetime.fromisoformat(block["end"])
                if block_start < day_end and block_end > day_start:
                    blocked_periods.append(block)
            elif "start_date" in block and "end_date" in block:
                block_start = datetime.combine(
                    date.fromisoformat(block["start_date"]),
                    time.min,
                    tzinfo=timezone,
                )
                block_end = datetime.combine(
                    date.fromisoformat(block["end_date"]) + timedelta(days=1),
                    time.min,
                    tzinfo=timezone,
                )
                if block_start < day_end and block_end > day_start:
                    blocked_periods.append(block)
            elif (
                block.get("condition", {}).get("month", "").lower()
                == target_date.strftime("%B").lower()
            ):
                blocked_periods.append(block)
        if not working_hours:
            return {
                "date": target_date.isoformat(),
                "timezone": user["timezone"],
                "working_start": None,
                "working_end": None,
                "blocked_periods": blocked_periods,
                "available_slots": [],
            }

        working_start, working_end = working_hours
        slots = []
        current = working_start

        # Compute the earliest allowed booking time based on advance notice
        advance_minutes = appt.get("advance_notice_minutes")
        earliest_allowed = None
        if advance_minutes is not None:
            earliest_allowed = datetime.now(timezone) + timedelta(
                minutes=advance_minutes
            )

        while current + duration <= working_end:
            slot_end = current + duration
            if not self.is_blocked(user, current, slot_end):
                # Skip slots that violate the advance booking deadline
                if earliest_allowed is not None and current < earliest_allowed:
                    current += duration
                    continue
                slots.append(
                    {
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                        "appointment_type": appt["name"],
                    }
                )
            current += duration

        return {
            "date": target_date.isoformat(),
            "timezone": user["timezone"],
            "working_start": working_start.isoformat(),
            "working_end": working_end.isoformat(),
            "blocked_periods": blocked_periods,
            "available_slots": slots,
        }

    async def book_appointment(
        self,
        user,
        appointment_type,
        start,
        exclude_start=None,
        customer_name=None,
        customer_phone=None,
    ):
        appt = self.get_appointment_type(user, appointment_type)
        duration = timedelta(minutes=appt["duration_minutes"])
        tz = ZoneInfo(user["timezone"])

        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        else:
            start = start.astimezone(tz)

        # Enforce advance booking deadline if set
        advance_minutes = appt.get("advance_notice_minutes")
        if advance_minutes is not None:
            now = datetime.now(tz)
            deadline = now + timedelta(minutes=advance_minutes)
            if start < deadline:
                raise ValueError(
                    f"Appointments must be booked at least {advance_minutes} minutes "
                    "in advance"
                )

        end = start + duration
        await self._refresh_database_blocked_times(user, exclude_start)

        working_hours = self.get_working_hours(user, start.date())
        if not working_hours:
            raise ValueError("No working hours on this day")

        working_start, working_end = working_hours
        if start < working_start or end > working_end:
            raise ValueError("Appointment is outside working hours")

        if self.is_blocked(user, start, end):
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

        customer_id = None
        if customer_name is not None:
            customer_phone = customer_phone.strip()
            customer_name = customer_name.strip()
            await self.upsert_customer(
                customer_id=customer_phone,
                phone=customer_phone,
                name=customer_name,
            )
            customer_id = customer_phone
        created = await self.create_blocked_time(
            {
                "user": user["id"],
                "reason": booking["reason"],
                "start": booking["start"],
                "end": booking["end"],
                "appointment_type": booking["appointment_type"],
                **({"customer": customer_id} if customer_id is not None else {}),
            }
        )
        booking["id"] = created["id"]
        if customer_id is not None:
            booking["name"] = customer_name
            booking["phone"] = customer_phone
        user.setdefault("blocked_time", []).append(booking)
        return booking
