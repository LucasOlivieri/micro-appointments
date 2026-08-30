import json
from pathlib import Path

from sqlite_utils import Migrations


def load_config(config_path=None):
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.json"
    config_path = Path(config_path)
    if not config_path.exists():
        return {"users": []}
    return json.loads(config_path.read_text(encoding="utf-8"))


def sync_config_to_db(db, config_path=None):
    config = load_config(config_path)
    for user in config.get("users", []):
        db["users"].upsert(
            {
                "id": user["id"],
                "email": user.get("email"),
                "timezone": user.get("timezone"),
                "name": user.get("name"),
            }
        )
        db["rules"].upsert_all(user.get("rules", []), pk="id")
        db["blocked_times"].upsert_all(user.get("blocked_times", []), pk="id")
        db["appointment_types"].upsert_all(
            user.get("appointment_types", []),
            pk="id",
        )


migrations = Migrations("main")


@migrations()
def create_tables(db):
    db["users"].create(
        {"id": str, "name": str, "email": str, "timezone": str},
        pk="id",
        defaults={"timezone": "America/Argentina/Buenos_Aires"},
        if_not_exists=True,
    )
    db["rules"].create(
        {"id": int, "user": str, "weekday": int, "start": str, "end": str},
        pk="id",
        foreign_keys=[("user", "users", "id")],
        if_not_exists=True,
    )
    db["appointment_types"].create(
        {"id": int, "user": str, "name": str, "duration_minutes": int},
        pk="id",
        foreign_keys=[("user", "users", "id")],
        if_not_exists=True,
    )
    db["blocked_times"].create(
        {
            "id": int,
            "user": str,
            "reason": str,
            "start": str,
            "end": str,
        },
        pk="id",
        foreign_keys=[("user", "users", "id")],
        if_not_exists=True,
    )


@migrations()
def add_booking_columns(db):
    columns = {row["name"] for row in db.query("PRAGMA table_info(blocked_times)")}
    if "appointment_type" not in columns:
        db.execute('ALTER TABLE blocked_times ADD COLUMN "appointment_type" TEXT')


@migrations()
def add_rule_recurrence_columns(db):
    columns = {row["name"] for row in db.query("PRAGMA table_info(rules)")}
    if "rrule" not in columns:
        db.execute('ALTER TABLE rules ADD COLUMN "rrule" TEXT')
    if "dtstart" not in columns:
        db.execute('ALTER TABLE rules ADD COLUMN "dtstart" TEXT')
    if "exclude_dates" not in columns:
        db.execute('ALTER TABLE rules ADD COLUMN "exclude_dates" TEXT')


@migrations()
def add_customer_column(db):
    db["customer"].create(
        {"id": str, "phone": str, "name": str, "info": str}, if_not_exists=True
    )
    columns = {row["name"] for row in db.query("PRAGMA table_info(blocked_times)")}
    if "customer" not in columns:
        db.table("blocked_times").add_column("customer", fk="customer", fk_col="id")


@migrations()
def setup_user(db):
    sync_config_to_db(db)


@migrations()
def add_google_event_id_column(db):
    columns = {row["name"] for row in db.query("PRAGMA table_info(blocked_times)")}
    if "google_event_id" not in columns:
        db.execute('ALTER TABLE blocked_times ADD COLUMN "google_event_id" TEXT')
