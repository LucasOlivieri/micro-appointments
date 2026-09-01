from collections import defaultdict

from tortoise.expressions import Q

from .models import AppointmentType, BlockedTime, Customer, Rule, User

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
    def __init__(self, path):
        self.path = str(path)

    async def list_blocked_times(self, user_id, bookings_only=False):
        query = BlockedTime.filter(user_id=user_id)
        if bookings_only:
            query = query.filter(~Q(appointment_type=None))
        query = query.order_by("start", "id")

        blocked_times = []
        for row in await query.all():
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
        user = await User.create(**dict(payload))
        return _serialize_user(user)

    async def upsert_user(self, payload):
        body = dict(payload)
        user_id = body["id"]
        defaults = {
            "name": body.get("name"),
            "email": body.get("email"),
            "timezone": body.get("timezone") or "America/Argentina/Buenos_Aires",
        }
        user, _ = await User.update_or_create(id=user_id, defaults=defaults)
        return _serialize_user(user)

    async def get_user(self, user_id):
        user = await User.filter(id=user_id).first()
        if user is None:
            return None
        return _serialize_user(user)

    async def list_users(self):
        rows = await User.all().order_by("name", "id")
        return [_serialize_user(row) for row in rows]

    async def create_rule(self, payload):
        body = dict(payload)
        if "user" in body and "user_id" not in body:
            body["user_id"] = body.pop("user")
        item = await Rule.create(**body)
        return _serialize_rule(item)

    async def list_rules(self, user_id):
        rows = await Rule.filter(user_id=user_id).order_by("id")
        return [_serialize_rule(row) for row in rows]

    async def create_appointment_type(self, payload):
        body = dict(payload)
        if "user" in body and "user_id" not in body:
            body["user_id"] = body.pop("user")
        item = await AppointmentType.create(**body)
        return _serialize_appointment_type(item)

    async def list_appointment_types(self, user_id):
        rows = await AppointmentType.filter(user_id=user_id).order_by("id")
        return [_serialize_appointment_type(row) for row in rows]

    async def find_customer_by_phone(self, phone):
        customer = await Customer.filter(phone=phone).first()
        if customer is None:
            return None
        return {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "info": customer.info,
        }

    async def upsert_customer(self, customer_id, phone, name):
        customer, _ = await Customer.update_or_create(
            id=customer_id,
            defaults={"phone": phone, "name": name},
        )
        return {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "info": customer.info,
        }

    async def list_appointments(self, user_id, appointment_type=None):
        query = BlockedTime.filter(user_id=user_id, reason="booked")
        if appointment_type is not None:
            query = query.filter(appointment_type__iexact=appointment_type)
        rows = await query.order_by("start", "id")

        customer_ids = {row.customer for row in rows if row.customer}
        customers = {}
        if customer_ids:
            for c in await Customer.filter(id__in=list(customer_ids)):
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
        row = await BlockedTime.filter(
            id=appointment_id,
            user_id=user_id,
            reason="booked",
        ).first()
        if row is None:
            return None

        c = await Customer.filter(id=row.customer).first() if row.customer else None
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

        await BlockedTime.filter(id=appointment_id).delete()
        await _dispatch(DELETED, appointment)
        return appointment

    async def create_blocked_time(self, item):
        payload = dict(item)
        if "user" in payload and "user_id" not in payload:
            payload["user_id"] = payload.pop("user")

        created = await BlockedTime.create(**payload)
        result = _serialize_blocked_time(created)
        await _dispatch(CREATED, result)
        return result

    async def update_blocked_time(self, item_id, changes):
        payload = dict(changes)
        if "user" in payload and "user_id" not in payload:
            payload["user_id"] = payload.pop("user")

        await BlockedTime.filter(id=item_id).update(**payload)
        updated = await BlockedTime.get(id=item_id)
        result = _serialize_blocked_time(updated)
        await _dispatch(UPDATED, result)
        return result

    async def list_blocked_time_rows(self, user_id):
        rows = await BlockedTime.filter(user_id=user_id).order_by("id")
        return [_serialize_blocked_time(row) for row in rows]
