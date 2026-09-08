from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from api.admin import mount_sqlite_panel
from api.dependencies import DEFAULT_DATABASE_PATH
from api.routes.agent import create_router as create_agent_router
from api.routes.appointments import create_router as create_appointments_router
from api.routes.dashboard import create_router as create_dashboard_router
from api.routes.users import create_router as create_users_router
from config import Config
from core.db import close_db, init_db
from core.models import User
from integrations.base import Integration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def create_app(
    database_path: str | Path = DEFAULT_DATABASE_PATH, on_startup=None
) -> FastAPI:
    database_path = Path(database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db(database_path)
        if on_startup:
            await on_startup(database_path)

        # Imported lazily so heavy deps (aiogram, openai) only load when an
        # integration is actually enabled.
        from integrations import IntegrationFactory

        configured: list[Integration] = IntegrationFactory.create_configured()
        app.state.integrations = configured
        for integration in configured:
            try:
                await integration.start()
            except Exception:
                logger.exception("Unable to start %s integration", integration.name)
        try:
            yield
        finally:
            for integration in reversed(configured):
                try:
                    await integration.stop()
                except Exception:
                    logger.exception("Unable to stop %s integration", integration.name)
            await close_db()

    app = FastAPI(
        title="Appointments API",
        description=(
            "Create, inspect, reschedule, and cancel appointments. "
            "All appointment times are ISO 8601 datetimes."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    mount_sqlite_panel(
        app,
        db_path="db.sqlite3",
        title="micro-appointments",
        prefix=f"/{Config.ADMIN_URL}",
    )
    app.include_router(create_users_router(database_path))
    app.include_router(create_appointments_router(database_path))
    app.include_router(create_agent_router(database_path))
    app.state.dashboard_sessions = {}
    app.include_router(create_dashboard_router(database_path))

    @app.post("/integrations/telegram/webhook")
    async def telegram_webhook(request: Request) -> Response:
        integrations: list[Integration] = getattr(app.state, "integrations", [])
        telegram = next(
            (
                integration
                for integration in integrations
                if integration.name == "telegram"
            ),
            None,
        )
        if telegram is None:
            return Response(status_code=404)
        secret = telegram.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return Response(status_code=403)
        await telegram.handle_webhook(await request.json())  # type: ignore[attr-defined]
        return Response(status_code=200)

    @app.get("/health")
    async def health():
        integrations: list[Integration] = getattr(app.state, "integrations", [])
        try:
            await User.all().limit(1).values("id")
        except Exception:
            logger.exception("Health check database query failed")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "degraded",
                    "database": "unavailable",
                    "integrations": [integration.name for integration in integrations],
                },
            )
        return {
            "status": "ok",
            "database": "ok",
            "integrations": [integration.name for integration in integrations],
        }

    return app


app = create_app()
