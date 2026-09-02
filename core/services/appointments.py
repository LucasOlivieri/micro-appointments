from collections import defaultdict

from core.models import AppointmentType, BlockedTime, Rule, User
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

    async def list_appointments(self, user_id, appointment_type=None):
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

    async def delete_appointment(self, user_id, appointment_id):
        appointment = await self.get_appointment(user_id, appointment_id)
        if appointment is None:
            return None

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
