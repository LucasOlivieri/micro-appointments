from collections import defaultdict

from .db import get_db


CREATED = "created"
UPDATED = "updated"
_ACTION_HANDLERS = defaultdict(list)


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
            "SELECT id, user, reason, start, end, start_datetime, "
            "end_datetime, appointment_type FROM blocked_times "
            "WHERE user = :user_id"
        )
        if bookings_only:
            query += " AND appointment_type IS NOT NULL"

        rows = self.db.query(query, {"user_id": user_id})
        blocked_times = []
        for row in rows:
            if row["appointment_type"]:
                blocked_times.append({
                    "reason": row["reason"],
                    "start": row["start"] or row["start_datetime"],
                    "end": row["end"] or row["end_datetime"],
                    "appointment_type": row["appointment_type"],
                })
            elif row["start"] and row["end"]:
                blocked_times.append({
                    "reason": row["reason"],
                    "start_date": row["start"][:10],
                    "end_date": row["end"][:10],
                })
        return blocked_times

    def create_blocked_time(self, item):
        item = dict(item)
        if "start" in item and "end" in item:
            item.pop("start_datetime", None)
            item.pop("end_datetime", None)
        table = self.db["blocked_times"]
        table.insert(item)
        created = table.get(table.last_pk)
        created.pop("start_datetime", None)
        created.pop("end_datetime", None)
        _dispatch(CREATED, created)
        return created

    def update_blocked_time(self, item_id, changes):
        table = self.db["blocked_times"]
        table.update(item_id, changes)
        updated = table.get(item_id)
        _dispatch(UPDATED, updated)
        return updated