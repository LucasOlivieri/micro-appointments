# Micro Appointments

A small scheduling app for managing doctors or staff calendars, appointment types, and booked availability. It uses SQLite as the persistence layer, a FastAPI API for interacting with the calendar, and configuration-driven user setup.

## Features

- Configurable users with timezone-aware calendar rules
- Recurring weekly availability rules
- Appointment type definitions with duration values
- Blocked time ranges for vacations or maintenance
- Booking logic that prevents double-booking
- FastAPI endpoints for listing users and scheduling appointments
- Agent tooling for an LLM-style assistant to operate the calendar

## Project structure

- `api/` — FastAPI application and routes
- `bot/` — agent/client tooling used by the assistant
- `core/` — scheduling logic, DB bootstrap, and recurrence calculations
- `tests/` — pytest coverage for app behavior
- `config.json` — runtime user configuration used to seed the database
- `setup.py` — interactive config generator

## Configuration

The app reads scheduling data from `config.json`.

Example structure:

```json
{
  "users": [
    {
      "id": "user-uuid",
      "name": "Dr. Example",
      "email": "doctor@example.com",
      "timezone": "America/Argentina/Buenos_Aires",
      "rules": [
        {
          "id": 1,
          "user": "user-uuid",
          "rrule": "FREQ=WEEKLY;BYDAY=MO",
          "start": "09:00",
          "end": "17:00"
        }
      ],
      "appointment_types": [
        {
          "id": 1,
          "user": "user-uuid",
          "name": "Follow-up",
          "duration_minutes": 15
        }
      ],
      "blocked_times": [
        {
          "id": 1,
          "user": "user-uuid",
          "reason": "vacation",
          "start": "2026-01-01T00:00:00+00:00",
          "end": "2026-01-03T00:00:00+00:00"
        }
      ]
    }
  ]
}
```

### Generate or update config

```bash
python setup.py
```

You can also set a custom output path or timezone:

```bash
python setup.py --output config.json --timezone UTC
```

### Backup config from database

To create a timestamped backup of the current configuration stored in the database:

```bash
python backup_config.py
```

This generates a file like `config_backup_2026-08-29_14-30-45.json` in the project root.

Options:

```bash
python backup_config.py --output-dir ./backups  # Save to custom directory
python backup_config.py --verbose               # Show detailed export statistics
```

Backups include all users, rules, appointment types, and blocked times in the same format as `config.json`.

## Database setup

The app initializes SQLite via `core/db.py`. On startup it applies migrations and then syncs data from `config.json` into the database tables.

This keeps the database aligned with the current configuration file without requiring manual SQL updates.

## Run the API

Using `uv`:

```bash
uv run uvicorn api.main:app --reload
```

Then open:

- http://localhost:8000/docs for the FastAPI Swagger UI

## Run tests

```bash
uv run pytest
```

## Notes

- Times are stored as ISO 8601 strings with timezone information.
- The booking logic checks working hours, blocked ranges, and appointment duration before creating a reservation.
- The app is designed to support multiple users, each with their own rules and appointment types.
