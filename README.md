# Micro Appointments

A small scheduling app for managing doctors or staff calendars, appointment types, and booked availability. It uses SQLite as the persistence layer, a FastAPI API for interacting with the calendar, and configuration-driven user setup.

[![CI/CD](https://github.com/LucasOlivieri/micro-appointments/actions/workflows/ci.yml/badge.svg)](https://github.com/LucasOlivieri/micro-appointments/actions/workflows/ci.yml)

## Features

- Configurable users with timezone-aware calendar rules
- Recurring weekly availability rules
- Appointment type definitions with duration values
- Blocked time ranges for vacations or maintenance
- Booking logic that prevents double-booking
- FastAPI endpoints for listing users and scheduling appointments
- Agent tooling for an LLM-style assistant to operate the calendar
- Telegram webhook integration for the receptionist assistant

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

### Telegram integration

Telegram is disabled by default. To enable it, configure the following environment
variables before starting the API:

```text
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.example/integrations/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=optional-secret
```

The application registers the webhook during startup and removes it during shutdown.
All Telegram chats use the same receptionist agent. The agent determines which
appointment user applies based on the conversation. Invalid Telegram configuration or
startup failures are logged without preventing the API from starting.

## Run tests

```bash
uv run pytest
```

## Run CI checks locally (before push)

Use the same checks that run in CI so you catch issues before pushing:

```bash
# 1) Sync project dependencies
uv sync --group test

# 2) Install CI tooling in your local env (one-time)
uv pip install ruff black mypy bandit

# 3) Run quality checks
uv run ruff check .
uv run black --check .
uv run mypy api core bot
uv run bandit -q -r api core bot

# 4) Run tests
uv run pytest -q
```

## Pre-commit hooks

The project includes a `.pre-commit-config.yaml` with the following hooks:

| Hook | Stage | Description |
|------|-------|-------------|
| `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files` | commit | General file hygiene |
| `ruff` | commit | Lint and auto-fix |
| `black` | commit | Code formatting |
| `bandit` | push | Security scan (`api`, `core`, `bot`) |
| `mypy` | push | Type checking (`api`, `core`, `bot`) |
| `pytest` | push | Run test suite |

Install the hooks with:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

To run all hooks manually:

```bash
uv run pre-commit run --all-files
```

Optional (same container build used by CI on `main` pushes):

```bash
docker build -t micro-appointments:local .
```

## Notes

- Times are stored as ISO 8601 strings with timezone information.
- The booking logic checks working hours, blocked ranges, and appointment duration before creating a reservation.
- The app is designed to support multiple users, each with their own rules and appointment types.
