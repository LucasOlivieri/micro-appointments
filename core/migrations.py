import json
import logging
from pathlib import Path

from core.db import get_db

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def load_config(config_path: str | Path | None = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.json"
    config_path = Path(config_path)
    if not config_path.exists():
        return {"users": []}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _load_migration_sql(name: str) -> str:
    path = _MIGRATIONS_DIR / f"{name}.sql"
    if not path.exists():
        raise FileNotFoundError(f"Migration file not found: {path}")
    return path.read_text(encoding="utf-8")


async def _table_exists(table_name: str) -> bool:
    db = get_db()
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return bool(await cursor.fetchone())


async def _column_exists(table_name: str, column_name: str) -> bool:
    db = get_db()
    cursor = await db.execute(f"PRAGMA table_info({table_name})")
    rows = await cursor.fetchall()
    return any(row["name"] == column_name for row in rows)


async def _mark_migration(name: str) -> None:
    db = get_db()
    await db.execute(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)", (name,)
    )
    await db.commit()


async def _is_applied(name: str) -> bool:
    db = get_db()
    cursor = await db.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (name,))
    return bool(await cursor.fetchone())


_MIGRATIONS = [
    "001_create_tables",
    "002_add_booking_columns",
    "003_add_rule_recurrence_columns",
    "004_add_customer_table",
    "005_add_google_event_id_column",
    "006_drop_customer_fk",
    "007_add_user_prompt_columns",
    "008_add_advance_notice",
]

# Migrations that use ALTER TABLE ADD COLUMN — need column-existence check
_ALTER_MIGRATIONS = {
    "002_add_booking_columns": ("blocked_times", "appointment_type"),
    "003_add_rule_recurrence_columns": ("rules", "rrule"),
    "004_add_customer_table": ("blocked_times", "customer"),
    "005_add_google_event_id_column": ("blocked_times", "google_event_id"),
    "007_add_user_prompt_columns": ("users", "message"),
    "008_add_advance_notice": ("appointment_types", "advance_notice_minutes"),
}

# Migrations that use CREATE TABLE IF NOT EXISTS — need table-existence check
_CREATE_MIGRATIONS = {
    "001_create_tables": "users",
    "004_add_customer_table": "customer",
}


async def apply_migrations() -> None:
    db = get_db()

    # Ensure schema_migrations tracking table exists
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL UNIQUE
        )
    """)
    await db.commit()

    for name in _MIGRATIONS:
        if await _is_applied(name):
            continue

        # Skip if the table/column already exists (idempotency)
        if name in _ALTER_MIGRATIONS:
            table, column = _ALTER_MIGRATIONS[name]
            if await _column_exists(table, column):
                await _mark_migration(name)
                continue

        if name in _CREATE_MIGRATIONS:
            table = _CREATE_MIGRATIONS[name]
            if await _table_exists(table):
                await _mark_migration(name)
                continue

        # Special handling for 006_drop_customer_fk — check FK existence
        if name == "006_drop_customer_fk":
            cursor = await db.execute("PRAGMA foreign_key_list(blocked_times)")
            fk_rows = await cursor.fetchall()
            has_customer_fk = any(row["table"] == "customer" for row in fk_rows)
            if not has_customer_fk:
                await _mark_migration(name)
                continue

        sql = _load_migration_sql(name)
        await db.executescript(sql)
        await db.commit()
        await _mark_migration(name)
        logger.info("Applied migration: %s", name)


def _serialize_exclude_dates(dates):
    return json.dumps(dates) if dates else None


async def sync_config_to_db(config_path: str | Path | None = None) -> None:
    config = load_config(config_path)
    db = get_db()

    for user in config.get("users", []):
        await db.execute(
            """INSERT INTO users (id, name, email, timezone, message, system_prompt)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name = excluded.name,
                   email = excluded.email,
                   timezone = excluded.timezone,
                   message = excluded.message,
                   system_prompt = excluded.system_prompt""",
            (
                user["id"],
                user.get("name"),
                user.get("email"),
                user.get("timezone") or "America/Argentina/Buenos_Aires",
                user.get("message"),
                user.get("system_prompt"),
            ),
        )

        for rule in user.get("rules", []):
            rule_id = rule.get("id")
            if rule_id is None:
                await db.execute(
                    """INSERT INTO rules (user, weekday, start, end, rrule, dtstart,
                       exclude_dates)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user["id"],
                        rule.get("weekday"),
                        rule.get("start"),
                        rule.get("end"),
                        rule.get("rrule"),
                        rule.get("dtstart"),
                        _serialize_exclude_dates(rule.get("exclude_dates")),
                    ),
                )
            else:
                await db.execute(
                    """INSERT INTO rules (id, user, weekday, start, end, rrule, dtstart,
                       exclude_dates)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           user = excluded.user,
                           weekday = excluded.weekday,
                           start = excluded.start,
                           end = excluded.end,
                           rrule = excluded.rrule,
                           dtstart = excluded.dtstart,
                           exclude_dates = excluded.exclude_dates""",
                    (
                        rule_id,
                        user["id"],
                        rule.get("weekday"),
                        rule.get("start"),
                        rule.get("end"),
                        rule.get("rrule"),
                        rule.get("dtstart"),
                        _serialize_exclude_dates(rule.get("exclude_dates")),
                    ),
                )

        for blocked in user.get("blocked_times", []):
            blocked_id = blocked.get("id")
            if blocked_id is None:
                await db.execute(
                    """INSERT INTO blocked_times
                       (user, reason, start, end, appointment_type,
                       google_event_id, customer)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user["id"],
                        blocked.get("reason"),
                        blocked.get("start"),
                        blocked.get("end"),
                        blocked.get("appointment_type"),
                        blocked.get("google_event_id"),
                        blocked.get("customer"),
                    ),
                )
            else:
                await db.execute(
                    """INSERT INTO blocked_times
                       (id, user, reason, start, end, appointment_type,
                       google_event_id, customer)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           user = excluded.user,
                           reason = excluded.reason,
                           start = excluded.start,
                           end = excluded.end,
                           appointment_type = excluded.appointment_type,
                           google_event_id = excluded.google_event_id,
                           customer = excluded.customer""",
                    (
                        blocked_id,
                        user["id"],
                        blocked.get("reason"),
                        blocked.get("start"),
                        blocked.get("end"),
                        blocked.get("appointment_type"),
                        blocked.get("google_event_id"),
                        blocked.get("customer"),
                    ),
                )

        for appointment_type in user.get("appointment_types", []):
            appointment_id = appointment_type.get("id")
            if appointment_id is None:
                await db.execute(
                    """INSERT INTO appointment_types
                       (user, name, duration_minutes, advance_notice_minutes)
                       VALUES (?, ?, ?, ?)""",
                    (
                        user["id"],
                        appointment_type.get("name"),
                        appointment_type.get("duration_minutes"),
                        appointment_type.get("advance_notice_minutes"),
                    ),
                )
            else:
                await db.execute(
                    """INSERT INTO appointment_types
                       (id, user, name, duration_minutes, advance_notice_minutes)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           user = excluded.user,
                           name = excluded.name,
                           duration_minutes = excluded.duration_minutes,
                           advance_notice_minutes = excluded.advance_notice_minutes""",
                    (
                        appointment_id,
                        user["id"],
                        appointment_type.get("name"),
                        appointment_type.get("duration_minutes"),
                        appointment_type.get("advance_notice_minutes"),
                    ),
                )

    # Sync customers from blocked_times
    cursor = await db.execute(
        "SELECT DISTINCT customer FROM blocked_times WHERE customer IS NOT NULL"
    )
    phone_rows = await cursor.fetchall()
    for row in phone_rows:
        phone = row["customer"]
        cursor2 = await db.execute("SELECT 1 FROM customer WHERE id = ?", (phone,))
        if not await cursor2.fetchone():
            await db.execute(
                "INSERT INTO customer (id, phone, name) VALUES (?, ?, ?)",
                (phone, phone, phone),
            )

    await db.commit()
