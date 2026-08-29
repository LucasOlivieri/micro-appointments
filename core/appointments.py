from collections import defaultdict

from .db import get_db

CREATED = "created"
UPDATED = "updated"
_ACTION_HANDLERS: defaultdict = defaultdict(list)


def onaction(action):
    """Register a callback for an appointments service action."""

    def decorator(handler):
        _ACTION_HANDLERS[action].append(handler)
        return handler

    return decorator


def _dispatch(action, item):
    for handler in _ACTION_HANDLERS[action]:
        handler(item)


class AppointmentsService:
    def __init__(self, path):
        self.db = get_db(path)

    def list_blocked_times(self, user_id, bookings_only=False):
        query = (
            "SELECT id, user, reason, start, end, appointment_type "
            "FROM blocked_times "
            "WHERE user = :user_id"
        )
        if bookings_only:
            query += " AND appointment_type IS NOT NULL"

        rows = self.db.query(query, {"user_id": user_id})
        blocked_times = []
        for row in rows:
            if row["appointment_type"]:
                blocked_times.append(
                    {
                        "reason": row["reason"],
                        "start": row["start"],
                        "end": row["end"],
                        "appointment_type": row["appointment_type"],
                    }
                )
            elif row["start"] and row["end"]:
                blocked_times.append(
                    {
                        "reason": row["reason"],
                        "start_date": row["start"][:10],
                        "end_date": row["end"][:10],
                    }
                )
        return blocked_times

    def list_appointments(self, user_id, appointment_type=None):
        query = (
            "SELECT blocked_times.id, blocked_times.user, blocked_times.reason, "
            "blocked_times.start, blocked_times.end, blocked_times.appointment_type, "
            "customer.name, customer.phone "
            "FROM blocked_times "
            "LEFT JOIN customer ON customer.id = blocked_times.customer "
            "WHERE blocked_times.user = :user_id AND blocked_times.reason = 'booked'"
        )
        params = {"user_id": user_id}
        if appointment_type is not None:
            query += (
                " AND lower(blocked_times.appointment_type) = lower(:appointment_type)"
            )
            params["appointment_type"] = appointment_type
        query += " ORDER BY blocked_times.start, blocked_times.id"
        return list(self.db.query(query, params))

    def get_appointment(self, user_id, appointment_id):
        rows = self.db.query(
            "SELECT blocked_times.id, blocked_times.user, blocked_times.reason, "
            "blocked_times.start, blocked_times.end, blocked_times.appointment_type, "
            "customer.name, customer.phone "
            "FROM blocked_times "
            "LEFT JOIN customer ON customer.id = blocked_times.customer "
            "WHERE blocked_times.id = :appointment_id "
            "AND blocked_times.user = :user_id "
            "AND blocked_times.reason = 'booked'",
            {"appointment_id": appointment_id, "user_id": user_id},
        )
        return next(iter(rows), None)

    def delete_appointment(self, user_id, appointment_id):
        appointment = self.get_appointment(user_id, appointment_id)
        if appointment is None:
            return None
        self.db["blocked_times"].delete(appointment_id)
        return appointment

    def create_blocked_time(self, item):
        item = dict(item)
        table = self.db["blocked_times"]
        table.insert(item)
        created = table.get(table.last_pk)
        _dispatch(CREATED, created)
        return created

    def update_blocked_time(self, item_id, changes):
        table = self.db["blocked_times"]
        table.update(item_id, changes)
        updated = table.get(item_id)
        _dispatch(UPDATED, updated)
        return updated
