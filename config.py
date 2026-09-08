import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # API
    TELEGRAM_ENABLED: bool = os.environ.get("TELEGRAM_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # Bot / Agent
    APPOINTMENTS_API_URL: str = os.environ.get(
        "APPOINTMENTS_API_URL", "http://127.0.0.1:8000"
    )
    OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL: str | None = os.environ.get("OPENAI_BASE_URL")
    APPOINTMENTS_USER_ID: str | None = os.environ.get("APPOINTMENTS_USER_ID")
    AGENT_MEMORY_PATH: str = os.environ.get("AGENT_MEMORY_PATH", "memory.sqlite3")

    # Read-only dashboard
    DASHBOARD_SUPERUSER_KEY: str | None = os.environ.get("DASHBOARD_SUPERUSER_KEY")

    # Admin panel
    ADMIN_USER: str = os.environ.get("ADMIN_USER", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin")

    # Telegram integration
    TELEGRAM_BOT_TOKEN: str | None = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_URL: str | None = os.environ.get("TELEGRAM_WEBHOOK_URL")
    TELEGRAM_WEBHOOK_SECRET: str | None = os.environ.get("TELEGRAM_WEBHOOK_SECRET")

    # Google Calendar integration
    GOOGLE_CALENDAR_ENABLED: bool = os.environ.get(
        "GOOGLE_CALENDAR_ENABLED", ""
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = os.environ.get(
        "GOOGLE_OAUTH_CLIENT_SECRET"
    )
    GOOGLE_TOKEN_FILE: str = os.environ.get("GOOGLE_TOKEN_FILE", "google_token.json")
