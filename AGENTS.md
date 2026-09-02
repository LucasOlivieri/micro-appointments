# AGENTS.md

## Purpose
This repository contains a scheduling and appointment management service with a FastAPI API, SQLite/Tortoise ORM persistence, appointment business logic in `core/`, and optional Telegram/Google integrations. Follow these instructions when making code changes or adding new agent-facing guidance.

## Project overview
- `api/`: FastAPI application and route layer.
- `core/`: scheduling business logic, ORM models, migrations, config sync, database bootstrap, service orchestration, and repository layer.
- `core/appointments.py`: service layer for scheduling and appointment operations.
- `core/repositories/`: one async repository per Tortoise model, plus a shared base abstraction.
- `bot/`: local assistant/agent tooling and CLI entrypoints.
- `integrations/`: Telegram and Google Calendar integration implementations.
- `tests/`: pytest suite covering API, scheduling, integration, and setup behavior.
- `config.json`: runtime configuration used to seed database data.
- `README.md`: primary project documentation and operational guidance.

## Tech stack
- Python 3.14
- FastAPI
- Tortoise ORM
- SQLite
- `uv` for dependency and task management
- pytest for automated tests

## Working conventions
- Prefer small, targeted edits over broad refactors.
- Keep business logic in `core/` and route handlers thin; do not move scheduling logic into FastAPI route functions.
- Preserve async patterns. Most I/O and DB work is async.
- Keep persistence behind repository interfaces in `core/repositories/`; `AppointmentsService` should orchestrate business logic and remain independent from `api/` and HTTP concerns.
- Maintain compatibility with the existing SQLite/Tortoise setup and configuration sync flow.
- Respect existing naming and serialization conventions used by the appointment service.
- When changing DB or config behavior, check the corresponding startup/migration path in `core/db.py` and `core/migrations.py`.

## Development workflow
1. Use the project environment via `uv` rather than ad hoc global Python installs.
2. Reproduce or understand the issue before patching.
3. Add or update a focused test to cover behavior changes when practical.
4. Run the smallest relevant test command first.
5. Verify the affected behavior before considering the task complete.
6. If the task is to fix a bug, create a test to prevent it from happening in the future.

## Common commands
- Start the API:
  - `uv run uvicorn api.main:app --reload`
- Run the full test suite:
  - `uv run pytest`
- Run a targeted test file or test selection:
  - `uv run pytest tests/test_api_appointments.py`
  - `uv run pytest tests/test_api_appointments.py -k create`
- Lint check:
  - `uv run ruff check .`
- Formatting check:
  - `uv run black --check .`
- Type check:
  - `uv run mypy api core bot`

## Repository-specific rules
- The app initializes the DB at startup via `api.main.create_app()` and `core.db.init_db()`.
- Configuration is synced to the database through `core.migrations.sync_config_to_db()` during startup.
- `config.json` is the source of user/rule/availability data; changes to schema or config shape should be compatible with the sync logic.
- The `integrations/` layer is optional and resilient: startup failures should be logged without crashing the API unless the issue is directly tied to the requested change.
- Telegram and Google integrations are feature flags driven by environment variables; do not assume they are enabled in local development.

## Environment and integration notes
- Telegram integration is controlled by:
  - `TELEGRAM_ENABLED`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_WEBHOOK_URL`
  - `TELEGRAM_WEBHOOK_SECRET`
- Google Calendar integration is controlled by:
  - `GOOGLE_CALENDAR_ENABLED`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
  - `GOOGLE_TOKEN_FILE`
- If integration setup is required, prefer a minimal config and keep failure handling graceful.

## Testing expectations
- Prefer real behavior tests over mock-heavy tests.
- Keep fixtures and setup minimal and close to the actual app flow.
- When changing scheduling, availability, or appointment booking logic, verify through the relevant tests in `tests/` instead of relying only on manual reasoning.

## Before finishing work
- Review the diff and confirm the change is scoped to the task.
- Ensure the relevant validation command was run and the output was checked.
- Update documentation only when the behavior or setup changed meaningfully.

## Notes for future agents
- The project is not a generic CRUD app; it is a scheduling system with recurring rules, blocked periods, and booking constraints.
- The most important logic is concentrated around appointment availability and recurrence, so changes there should be tested carefully.
- Favor compatibility with the project’s current patterns and configuration flow over introducing new architectural layers.
