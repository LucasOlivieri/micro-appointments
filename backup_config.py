"""
Script to backup config.json from the database.

Exports the current database state back into config.json format with a timestamped
filename.
The script reads users, rules, appointment_types, and blocked_times,
reconstructs the nested config structure, and saves it as JSON.

Usage:
    python backup_config.py                              # Save to project root
    python backup_config.py --output-dir ./backups       # Save to custom directory
    python backup_config.py --verbose                    # Show detailed output
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.db import init_db
from core.services.appointments import AppointmentsService


async def export_config_from_db(
    database_path: str | Path = "db.sqlite3",
) -> dict[str, Any]:
    """
    Export the current database state as a config.json structure.

    Returns:
        dict: Configuration with nested users, rules, appointment_types
            and blocked_times
    """
    await init_db(database_path)
    service = AppointmentsService(database_path)

    config = {"users": []}

    for user in await service.list_users():
        user_id = user["id"]

        rules = await service.list_rules(user_id)
        appointment_types = await service.list_appointment_types(user_id)
        blocked_times = await service.list_blocked_time_rows(user_id)

        user_obj = {
            "name": user.get("name"),
            "email": user.get("email"),
            "timezone": user.get("timezone"),
            "id": user_id,
            "rules": rules,
            "appointment_types": appointment_types,
            "blocked_times": blocked_times,
        }

        config["users"].append(user_obj)

    return config


def backup_config(
    output_dir: Path | None = None,
    verbose: bool = False,
    database_path: str | Path = "db.sqlite3",
) -> Path:
    """
    Create a timestamped backup of the config from the database.

    Args:
        output_dir: Directory to save the backup file. Defaults to project root.
        verbose: Print detailed output.
        database_path: Path to SQLite database file.

    Returns:
        Path: Path to the created backup file.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = output_dir / f"backups/config_backup_{timestamp}.json"

    if verbose:
        print("Exporting config from database...")

    config = asyncio.run(export_config_from_db(database_path=database_path))

    num_users = len(config.get("users", []))
    num_rules = sum(len(u.get("rules", [])) for u in config.get("users", []))
    num_types = sum(
        len(u.get("appointment_types", [])) for u in config.get("users", [])
    )
    num_blocked = sum(len(u.get("blocked_times", [])) for u in config.get("users", []))

    if verbose:
        print(f"  Users: {num_users}")
        print(f"  Rules: {num_rules}")
        print(f"  Appointment Types: {num_types}")
        print(f"  Blocked Times: {num_blocked}")

    backup_file.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if verbose:
        print(f"Backup saved to: {backup_file}")
    else:
        print(f"Backup created: {backup_file}")

    return backup_file


def main():
    """Command-line interface for the backup script."""
    parser = argparse.ArgumentParser(
        description="Backup config.json from the database with a timestamped filename.",
        epilog="Example: python backup_config.py --output-dir ./backups --verbose",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save the backup file (default: project root)",
    )
    parser.add_argument(
        "--database-path",
        type=str,
        default="db.sqlite3",
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed output"
    )

    args = parser.parse_args()

    try:
        backup_config(
            output_dir=args.output_dir,
            verbose=args.verbose,
            database_path=args.database_path,
        )
    except FileNotFoundError as error:
        print(f"Error: Database file not found: {error}")
        raise SystemExit(1) from error
    except Exception as error:
        print(f"Error during backup: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
