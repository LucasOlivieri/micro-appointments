"""
Script to backup config.json from the database.

Exports the current database state back into config.json format with a timestamped
filename.
The script queries users, rules, appointment_types, and blocked_times tables,
reconstructs the nested config structure, and saves it as JSON.

Usage:
    python backup_config.py                              # Save to project root
    python backup_config.py --output-dir ./backups       # Save to custom directory
    python backup_config.py --verbose                    # Show detailed output
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.db import get_db


def export_config_from_db() -> dict[str, Any]:
    """
    Export the current database state as a config.json structure.

    Returns:
        dict: Configuration with nested users, rules, appointment_types
            and blocked_times
    """
    db = get_db()

    config = {"users": []}

    # Fetch all users
    users = list(db["users"].rows)

    for user in users:
        user_id = user["id"]

        # Fetch related records for this user
        rules = [row for row in db["rules"].rows if row.get("user") == user_id]
        appointment_types = [
            row for row in db["appointment_types"].rows if row.get("user") == user_id
        ]
        blocked_times = [
            row for row in db["blocked_times"].rows if row.get("user") == user_id
        ]

        # Build user object with nested structure
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
) -> Path:
    """
    Create a timestamped backup of the config from the database.

    Args:
        output_dir: Directory to save the backup file. Defaults to project root.
        verbose: Print detailed output.

    Returns:
        Path: Path to the created backup file.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = output_dir / f"backups/config_backup_{timestamp}.json"

    if verbose:
        print("Exporting config from database...")

    # Export config from database
    config = export_config_from_db()

    # Count statistics
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

    # Write to file
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
        "--verbose", "-v", action="store_true", help="Print detailed output"
    )

    args = parser.parse_args()

    try:
        backup_config(output_dir=args.output_dir, verbose=args.verbose)
    except FileNotFoundError as e:
        print(f"Error: Database file not found: {e}")
        exit(1)
    except Exception as e:
        print(f"Error during backup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
