import json
import uuid
from datetime import date, datetime, time
from pathlib import Path

import typer
import questionary
from tzlocal import get_localzone_name
from zoneinfo import ZoneInfo


OUTPUT_PATH = Path(__file__).resolve().parent / "config.json"
app = typer.Typer(help="Create the calendar configuration for one or more users.")
DONE = "__done__"
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


def _prompt_weekday(label="Weekday"):
    choices = [
        questionary.Choice(day.title(), value=weekday)
        for day, weekday in WEEKDAYS.items()
    ]
    choices.append(questionary.Choice("Done", value=DONE))
    return questionary.select(f"{label}:", choices=choices).ask()


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
        weekday_number = _prompt_weekday()
        if weekday_number in {None, DONE}:
            return None
        return {
            "user": user_id,
            "weekday": weekday_number,
            "start": _prompt_time("Start time"),
            "end": _prompt_time("End time"),
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


def _prompt_date(label):
    while True:
        try:
            return date(
                _prompt_int(f"{label} year", minimum=1),
                _prompt_int(f"{label} month", minimum=1),
                _prompt_int(f"{label} day", minimum=1),
            )
        except ValueError:
            print("Enter a valid calendar date.")


def _prompt_datetime(label, timezone):
    while True:
        selected_date = _prompt_date(label)
        hour = _prompt_int(f"{label} hour", minimum=0)
        minute = _prompt_int(f"{label} minute", minimum=0)
        try:
            return datetime.combine(
                selected_date,
                time(hour, minute),
                tzinfo=ZoneInfo(timezone),
            )
        except ValueError:
            print("Enter an hour from 0 to 23 and a minute from 0 to 59.")


def _prompt_blocked_range(user_id, timezone):
    block_type = questionary.select(
        "Block type:",
        choices=[
            questionary.Choice("Date range", value="date"),
            questionary.Choice("Datetime interval", value="datetime"),
        ],
    ).ask()
    if block_type is None:
        return _prompt_blocked_range(user_id, timezone)

    if block_type == "date":
        start = _prompt_date("Start")
        end = _prompt_date("End")
        if end < start:
            print("End must be on or after start.")
            return _prompt_blocked_range(user_id, timezone)
        start_value = datetime.combine(start, time.min, tzinfo=ZoneInfo(timezone))
        end_value = datetime.combine(end, time.min, tzinfo=ZoneInfo(timezone))
    else:
        start_value = _prompt_datetime("Start", timezone)
        end_value = _prompt_datetime("End", timezone)
        if end_value <= start_value:
            print("End must be after start.")
            return _prompt_blocked_range(user_id, timezone)

    return start_value.isoformat(), end_value.isoformat()


def _blocked_times(user_id, timezone):
    def collect():
        reason = input("Reason: ").strip()
        if not reason:
            return None
        start, end = _prompt_blocked_range(user_id, timezone)
        return {
            "user": user_id,
            "reason": reason,
            "start": start,
            "end": end,
        }

    return _prompt_list("Blocked times", collect)


def build_user(timezone):
    user_id = str(uuid.uuid4())
    return {
        "name": _prompt_required("Name"),
        "email": _prompt_required("Email"),
        "timezone": timezone,
        "id": user_id,
        "rules": _rules(user_id),
        "appointment_types": _appointment_types(user_id),
        "blocked_times": _blocked_times(user_id, timezone),
    }


def build_config(user_count=1, timezone=None):
    timezone = timezone or get_localzone_name()
    try:
        ZoneInfo(timezone)
    except Exception as error:
        raise ValueError(f"Unknown timezone: {timezone}") from error
    users = [build_user(timezone) for _ in range(user_count)]
    for collection_name in ("rules", "appointment_types", "blocked_times"):
        item_id = 1
        for user in users:
            for item in user[collection_name]:
                item["id"] = item_id
                item_id += 1
    return {"users": users}


@app.command()
def main(
    output: Path = typer.Option(OUTPUT_PATH, "--output", "-o", help="Configuration file to write."),
    users: int = typer.Option(1, "--users", "-n", min=1, help="Number of users to configure."),
    timezone: str = typer.Option(None, help="Timezone used for all users and blocked times."),
):
    """Interactively create a configuration file."""
    config = build_config(users, timezone)
    output.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")
    typer.echo(f"Configuration written to {output}")


if __name__ == "__main__":
    app()