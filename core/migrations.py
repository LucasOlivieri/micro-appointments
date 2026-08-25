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
        "start": str,
        "end": str
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
    }, pk="id", foreign_keys=[
        ("user", "users", "id")
    ], if_not_exists=True)


@migrations()
def add_booking_columns(db):
    columns = {
        row["name"]
        for row in db.query("PRAGMA table_info(blocked_times)")
    }
    if "appointment_type" not in columns:
        db.execute(f'ALTER TABLE blocked_times ADD COLUMN "appointment_type" TEXT')

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
    print("Creating user: ", user_data)
    rules = user["rules"]
    blocked_times = user["blocked_times"]
    appointment_types = user["appointment_types"]

    db.table("users").upsert(user_data)
    db.table("rules").upsert_all(rules)
    db.table("blocked_times").upsert_all(blocked_times)
    db.table("appointment_types").upsert_all(appointment_types)

@migrations()
def add_customer_column(db):
    db["customer"].create({
        "id": str,
        "phone": str,
        "name": str,
        "info": str
    })
    db.table("blocked_times").add_column("customer", fk="customer", fk_col="id")