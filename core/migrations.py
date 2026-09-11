import json
from pathlib import Path

from tortoise import BaseDBAsyncClient

from core.models import (
    AppointmentType,
    BlockedTime,
    Customer,
    Rule,
    SchemaMigration,
    User,
)


def load_config(config_path: str | Path | None = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config.json"
    config_path = Path(config_path)
    if not config_path.exists():
        return {"users": []}
    return json.loads(config_path.read_text(encoding="utf-8"))


async def _table_exists(connection: BaseDBAsyncClient, table_name: str) -> bool:
    result = await connection.execute_query_dict(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        [table_name],
    )
    return bool(result)


async def _column_exists(
    connection: BaseDBAsyncClient,
    table_name: str,
    column_name: str,
) -> bool:
    rows = await connection.execute_query_dict(f"PRAGMA table_info({table_name})")
    return any(row.get("name") == column_name for row in rows)


async def _mark_migration(name: str) -> None:
    await SchemaMigration.get_or_create(name=name)


async def _is_applied(name: str) -> bool:
    return await SchemaMigration.filter(name=name).exists()


async def migration_create_tables(connection: BaseDBAsyncClient) -> None:
    if not await _table_exists(connection, "users"):
        await connection.execute_script("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                timezone TEXT NOT NULL DEFAULT 'America/Argentina/Buenos_Aires'
            );
            """)

    if not await _table_exists(connection, "rules"):
        await connection.execute_script("""
            CREATE TABLE rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                user TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                weekday INTEGER,
                start TEXT NOT NULL,
                end TEXT NOT NULL
            );
            """)

    if not await _table_exists(connection, "appointment_types"):
        await connection.execute_script("""
            CREATE TABLE appointment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                user TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL
            );
            """)

    if not await _table_exists(connection, "blocked_times"):
        await connection.execute_script("""
            CREATE TABLE blocked_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                user TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reason TEXT NOT NULL,
                start TEXT NOT NULL,
                end TEXT NOT NULL
            );
            """)


async def migration_add_booking_columns(connection: BaseDBAsyncClient) -> None:
    if not await _column_exists(connection, "blocked_times", "appointment_type"):
        await connection.execute_script(
            'ALTER TABLE blocked_times ADD COLUMN "appointment_type" TEXT;'
        )


async def migration_add_rule_recurrence_columns(connection: BaseDBAsyncClient) -> None:
    if not await _column_exists(connection, "rules", "rrule"):
        await connection.execute_script('ALTER TABLE rules ADD COLUMN "rrule" TEXT;')
    if not await _column_exists(connection, "rules", "dtstart"):
        await connection.execute_script('ALTER TABLE rules ADD COLUMN "dtstart" TEXT;')
    if not await _column_exists(connection, "rules", "exclude_dates"):
        await connection.execute_script(
            'ALTER TABLE rules ADD COLUMN "exclude_dates" JSON;'
        )


async def migration_add_customer_table(connection: BaseDBAsyncClient) -> None:
    if not await _table_exists(connection, "customer"):
        await connection.execute_script("""
            CREATE TABLE customer (
                id TEXT PRIMARY KEY NOT NULL,
                phone TEXT UNIQUE,
                name TEXT,
                info TEXT
            );
            """)
    if not await _column_exists(connection, "blocked_times", "customer"):
        await connection.execute_script(
            'ALTER TABLE blocked_times ADD COLUMN "customer" TEXT;'
        )


async def migration_drop_customer_fk(connection: BaseDBAsyncClient) -> None:
    """Drop FK constraint on blocked_times.customer by recreating the table."""
    table_info = await connection.execute_query_dict(
        "PRAGMA foreign_key_list(blocked_times)"
    )
    has_customer_fk = any(row.get("table") == "customer" for row in table_info)
    if not has_customer_fk:
        return

    await connection.execute_script("""
        CREATE TABLE blocked_times_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            user TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            appointment_type TEXT,
            customer TEXT,
            google_event_id TEXT
        );
        INSERT INTO blocked_times_new SELECT * FROM blocked_times;
        DROP TABLE blocked_times;
        ALTER TABLE blocked_times_new RENAME TO blocked_times;
    """)


async def migration_add_google_event_id_column(connection: BaseDBAsyncClient) -> None:
    if not await _column_exists(connection, "blocked_times", "google_event_id"):
        await connection.execute_script(
            'ALTER TABLE blocked_times ADD COLUMN "google_event_id" TEXT;'
        )


async def migration_add_user_prompt_columns(connection: BaseDBAsyncClient) -> None:
    if not await _column_exists(connection, "users", "message"):
        await connection.execute_script('ALTER TABLE users ADD COLUMN "message" TEXT;')
    if not await _column_exists(connection, "users", "system_prompt"):
        await connection.execute_script(
            'ALTER TABLE users ADD COLUMN "system_prompt" TEXT;'
        )


async def migration_add_advance_notice(connection: BaseDBAsyncClient) -> None:
    """Add advance_notice_minutes column to appointment_types table."""
    if not await _column_exists(
        connection, "appointment_types", "advance_notice_minutes"
    ):
        await connection.execute_script(
            'ALTER TABLE appointment_types ADD COLUMN "advance_notice_minutes" INTEGER;'
        )


_MIGRATIONS = [
    ("001_create_tables", migration_create_tables),
    ("002_add_booking_columns", migration_add_booking_columns),
    ("003_add_rule_recurrence_columns", migration_add_rule_recurrence_columns),
    ("004_add_customer_table", migration_add_customer_table),
    ("005_add_google_event_id_column", migration_add_google_event_id_column),
    ("006_drop_customer_fk", migration_drop_customer_fk),
    ("007_add_user_prompt_columns", migration_add_user_prompt_columns),
    ("008_add_advance_notice", migration_add_advance_notice),
]


async def apply_migrations() -> None:
    connection = User._meta.db

    await connection.execute_script("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL UNIQUE
        );
        """)

    for name, migration in _MIGRATIONS:
        if await _is_applied(name):
            continue
        await migration(connection)
        await _mark_migration(name)


async def sync_config_to_db(config_path: str | Path | None = None) -> None:
    config = load_config(config_path)
    for user in config.get("users", []):
        await User.update_or_create(
            defaults={
                "name": user.get("name"),
                "email": user.get("email"),
                "timezone": user.get("timezone") or "America/Argentina/Buenos_Aires",
            },
            id=user["id"],
        )

        for rule in user.get("rules", []):
            rule_defaults = {
                "user_id": user["id"],
                "weekday": rule.get("weekday"),
                "start": rule.get("start"),
                "end": rule.get("end"),
                "rrule": rule.get("rrule"),
                "dtstart": rule.get("dtstart"),
                "exclude_dates": rule.get("exclude_dates"),
            }
            rule_id = rule.get("id")
            if rule_id is None:
                await Rule.create(**rule_defaults)
            else:
                await Rule.update_or_create(defaults=rule_defaults, id=rule_id)

        for blocked in user.get("blocked_times", []):
            blocked_defaults = {
                "user_id": user["id"],
                "reason": blocked.get("reason"),
                "start": blocked.get("start"),
                "end": blocked.get("end"),
                "appointment_type": blocked.get("appointment_type"),
                "google_event_id": blocked.get("google_event_id"),
                "customer": blocked.get("customer"),
            }
            blocked_id = blocked.get("id")
            if blocked_id is None:
                await BlockedTime.create(**blocked_defaults)
            else:
                await BlockedTime.update_or_create(
                    defaults=blocked_defaults, id=blocked_id
                )

        for appointment_type in user.get("appointment_types", []):
            appointment_defaults = {
                "user_id": user["id"],
                "name": appointment_type.get("name"),
                "duration_minutes": appointment_type.get("duration_minutes"),
                "advance_notice_minutes": appointment_type.get(
                    "advance_notice_minutes"
                ),
            }
            appointment_id = appointment_type.get("id")
            if appointment_id is None:
                await AppointmentType.create(**appointment_defaults)
            else:
                await AppointmentType.update_or_create(
                    defaults=appointment_defaults,
                    id=appointment_id,
                )

    existing_customers = {
        customer.phone: customer
        for customer in await Customer.filter().all()
        if customer.phone is not None
    }
    for user in config.get("users", []):
        for blocked in user.get("blocked_times", []):
            phone = blocked.get("customer")
            if not phone:
                continue
            customer = existing_customers.get(phone)
            if customer is None:
                customer = await Customer.create(id=phone, phone=phone, name=phone)
                existing_customers[phone] = customer
