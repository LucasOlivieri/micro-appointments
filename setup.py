import json
import uuid
from datetime import date, datetime, time
from pathlib import Path

import typer
import questionary
from tzlocal import get_localzone_name
from zoneinfo import ZoneInfo


OUTPUT_PATH = Path(__file__).resolve().parent / "config.json"
app = typer.Typer(
    help=(
        "Create the calendar configuration used to find and book appointments "
        "for one or more users."
    )
)
DONE = "__done__"
HOUR_CHOICES = [questionary.Choice(str(hour), value=hour) for hour in range(24)]
MINUTE_CHOICES = [
    questionary.Choice(f"{minute:02d}", value=minute)
    for minute in range(0, 60, 5)
]
MONTH_CHOICES = [
    questionary.Choice(date(2000, month, 1).strftime("%b"), value=month)
    for month in range(1, 13)
]
DURATION_CHOICES = [
    questionary.Choice(
        f"{duration} minutes" if duration < 60 else f"{duration // 60} hours"
        if duration % 60 == 0
        else f"{duration // 60} hours {duration % 60} minutes",
        value=duration,
    )
    for duration in range(5, 241, 5)
]
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
RRULE_WEEKDAYS = {
    weekday: code
    for weekday, code in zip(WEEKDAYS.values(), ("MO", "TU", "WE", "TH", "FR", "SA", "SU"))
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
    hour = questionary.select(f"{label} hour:", choices=HOUR_CHOICES).ask()
    minute = questionary.select(f"{label} minute:", choices=MINUTE_CHOICES).ask()
    return f"{hour:02d}:{minute:02d}"


def _prompt_weekday(label="Weekday"):
    choices = [
        questionary.Choice(day.title(), value=weekday)
        for day, weekday in WEEKDAYS.items()
    ]
    choices.append(questionary.Choice("Done", value=DONE))
    return questionary.select(f"{label}:", choices=choices).ask()


def _prompt_list(label, instructions, collect):
    items = []
    print(f"\n{label}\n{instructions}")
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
            "rrule": f"FREQ=WEEKLY;BYDAY={RRULE_WEEKDAYS[weekday_number]}",
            "start": _prompt_time("Start time"),
            "end": _prompt_time("End time"),
        }

    return _prompt_list(
        "Weekly availability",
        "Add the days and hours when appointments can be booked. Choose Done when finished.",
        collect,
    )


def _appointment_types(user_id):
    def collect():
        name = input("Appointment name: ").strip()
        if not name:
            return None
        return {
            "user": user_id,
            "name": name,
            "duration_minutes": questionary.select(
                "How long should this appointment last?",
                choices=DURATION_CHOICES,
            ).ask(),
        }

    return _prompt_list(
        "Appointment types",
        "Add each service people can book. Leave the name blank when finished.",
        collect,
    )


def _prompt_date(label):
    while True:
        try:
            year = _prompt_int(f"{label} year", minimum=1)
            month = questionary.select(
                f"{label} month:", choices=MONTH_CHOICES
            ).ask()
            day = _prompt_int(f"{label} day", minimum=1)
            return date(
                year,
                month,
                day,
            )
        except ValueError:
            print("Enter a valid calendar date.")


def _prompt_blocked_range(user_id, timezone):
    start = _prompt_date("Start")
    end = _prompt_date("End")
    if end < start:
        print("End must be on or after start.")
        return _prompt_blocked_range(user_id, timezone)
    start_value = datetime.combine(start, time.min, tzinfo=ZoneInfo(timezone))
    end_value = datetime.combine(end, time.min, tzinfo=ZoneInfo(timezone))

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

    return _prompt_list(
        "Blocked times",
        "Add date ranges when appointments are not available. Leave the reason blank when finished.",
        collect,
    )


def build_user(timezone):
    print("\nSet up a user who can receive appointments.")
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


def _user_label(user):
    return f"{user['name']} ({user['email']})"


def _manage_users(users, timezone):
    current_user = users[0] if users else None
    while True:
        choices = []
        if users:
            choices.append(questionary.Choice("Change current user", value="select"))
        choices.append(questionary.Choice("Create a new user", value="create"))
        if users:
            choices.append(questionary.Choice("Delete an existing user", value="delete"))
        choices.append(questionary.Choice("Finish setup", value="finish"))
        action = questionary.select(
            f"Current user: {_user_label(current_user) if current_user else 'none'}\nWhat would you like to do?",
            choices=choices,
        ).ask()

        if action in {None, "finish"}:
            return users
        if action == "select":
            current_user = questionary.select(
                "Choose the current user:",
                choices=[
                    questionary.Choice(_user_label(user), value=user)
                    for user in users
                ],
            ).ask()
        elif action == "create":
            current_user = build_user(timezone)
            users.append(current_user)
        elif action == "delete":
            user = questionary.select(
                "Choose the user to delete:",
                choices=[
                    questionary.Choice(_user_label(user), value=user)
                    for user in users
                ],
            ).ask()
            if user is not None:
                users.remove(user)
                if user is current_user:
                    current_user = users[0] if users else None


def _renumber_items(users):
    for collection_name in ("rules", "appointment_types", "blocked_times"):
        item_id = 1
        for user in users:
            for item in user[collection_name]:
                item["id"] = item_id
                item_id += 1


def build_config(user_count=1, timezone=None):
    timezone = timezone or get_localzone_name()
    try:
        ZoneInfo(timezone)
    except Exception as error:
        raise ValueError(f"Unknown timezone: {timezone}") from error
    users = [build_user(timezone) for _ in range(user_count)]
    _renumber_items(users)
    return {"users": users}


@app.command()
def main(
    output: Path = typer.Option(OUTPUT_PATH, "--output", "-o", help="Configuration file to write."),
    users: int = typer.Option(1, "--users", "-n", min=1, help="Number of users to configure."),
    timezone: str = typer.Option(None, help="Timezone used for all users and blocked times."),
):
    """Interactively create or update a configuration file."""
    selected_timezone = timezone or get_localzone_name()
    try:
        ZoneInfo(selected_timezone)
    except Exception as error:
        raise ValueError(f"Unknown timezone: {selected_timezone}") from error

    if output.exists():
        config = json.loads(output.read_text(encoding="utf-8"))
        config["users"] = _manage_users(config.get("users", []), selected_timezone)
        _renumber_items(config["users"])
    else:
        config = build_config(users, selected_timezone)
    output.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")
    typer.echo(f"Configuration written to {output}")


if __name__ == "__main__":
    app()