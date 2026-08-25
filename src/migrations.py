import json

from sqlite_utils import Migrations


migrations = Migrations("main")

@migrations()
def create_tables(db):
    db["users"].create({
        "id": str,
        "name": str,
        "email": str,
        "timezone": str
    }, pk="id", defaults={"timezone": "America/Argentina/Buenos_Aires"}, if_not_exists=True)
    db["rules"].create({
        "id": int,
        "user": str,
        "weekday": int,
        "start_time": str,
        "end_time": str
    }, pk="id", foreign_keys=[
        ("user", "users", "id")
    ], if_not_exists=True)
    db["appointment_types"].create({
        "id": int,
        "user": str,
        "name": str,
        "duration_minutes": int
    }, pk="id", foreign_keys=[
        ("user", "users", "id")
    ], if_not_exists=True)
    db["blocked_times"].create({
        "id": int,
        "user": str,
        "reason": str,
        "start": str,
        "end": str,
        "start_datetime": str,
        "end_datetime": str,
        "appointment_type": str,
    }, pk="id", foreign_keys=[
        ("user", "users", "id")
    ], if_not_exists=True)


@migrations()
def add_booking_columns(db):
    columns = {
        row["name"]
        for row in db.query("PRAGMA table_info(blocked_times)")
    }
    for column in ("start_datetime", "end_datetime", "appointment_type"):
        if column not in columns:
            db.execute(f'ALTER TABLE blocked_times ADD COLUMN "{column}" TEXT')

@migrations()
def setup_user(db):
    CONFIG = json.loads(open("config.json").read())
    user = CONFIG.get("user")
    user_data = {
        "id": user["id"],
        "email": user["email"],
        "timezone": user["timezone"],
        "name": user["name"]
    }
    rules = user["rules"]
    blocked_times = user["blocked_times"]
    appointment_types = user["appointment_types"]

    db.table("users").upsert(user_data)
    db.table("rules").upsert_all(rules)
    db.table("blocked_times").upsert_all(blocked_times)
    db.table("appointment_types").upsert_all(appointment_types)