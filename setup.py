import json
import uuid
from datetime import datetime
from pathlib import Path

from tzlocal import get_localzone_name


OUTPUT_PATH = Path(__file__).resolve().parent / "config.json"
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _prompt_required(label):
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("A value is required.")


def _prompt_int(label, minimum=0):
    while True:
        try:
            value = int(input(f"{label}: ").strip())
        except ValueError:
            value = None
        if value is not None and value >= minimum:
            return value
        print(f"Enter a whole number greater than or equal to {minimum}.")


def _prompt_time(label):
    while True:
        value = input(f"{label} (HH:MM): ").strip()
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError:
            print("Enter a time in HH:MM format.")


def _prompt_weekday():
    while True:
        value = input("Weekday (Monday-Sunday): ").strip().lower()
        if value in WEEKDAYS:
            return WEEKDAYS[value]
        if value.isdigit() and 0 <= int(value) <= 6:
            return int(value)
        print("Enter a weekday name or a number from 0 (Monday) to 6 (Sunday).")


def _prompt_list(label, collect):
    items = []
    print(f"\n{label} (press Enter on the first prompt to finish)")
    while True:
        item = collect()
        if item is None:
            return items
        item["id"] = len(items) + 1
        items.append(item)


def _rules(user_id):
    def collect():
        weekday = input("Weekday (Monday-Sunday): ").strip().lower()
        if not weekday:
            return None
        if weekday not in WEEKDAYS and not (weekday.isdigit() and 0 <= int(weekday) <= 6):
            print("Enter a weekday name or a number from 0 (Monday) to 6 (Sunday).")
            return collect()
        weekday_number = WEEKDAYS[weekday] if weekday in WEEKDAYS else int(weekday)
        return {
            "user": user_id,
            "weekday": weekday_number,
            "start_time": _prompt_time("Start time"),
            "end_time": _prompt_time("End time"),
        }

    return _prompt_list("Rules", collect)


def _appointment_types(user_id):
    def collect():
        name = input("Appointment name: ").strip()
        if not name:
            return None
        return {
            "user": user_id,
            "name": name,
            "duration_minutes": _prompt_int("Duration in minutes", minimum=1),
        }

    return _prompt_list("Appointment types", collect)


def _blocked_times(user_id):
    def collect():
        reason = input("Reason: ").strip()
        if not reason:
            return None
        return {
            "user": user_id,
            "reason": reason,
            "start": _prompt_required("Start (ISO date or datetime)"),
            "end": _prompt_required("End (ISO date or datetime)"),
        }

    return _prompt_list("Blocked times", collect)


def build_config():
    user_id = str(uuid.uuid4())
    return {
        "user": {
            "name": _prompt_required("Name"),
            "email": _prompt_required("Email"),
            "timezone": get_localzone_name(),
            "id": user_id,
            "rules": _rules(user_id),
            "appointment_types": _appointment_types(user_id),
            "blocked_times": _blocked_times(user_id),
        }
    }


def main():
    config = build_config()
    OUTPUT_PATH.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")
    print(f"Configuration written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()