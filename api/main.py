import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import Response

from api.dependencies import DEFAULT_DATABASE_PATH
from api.routes.agent import create_router as create_agent_router
from api.routes.appointments import create_router as create_appointments_router
from api.routes.users import create_router as create_users_router
from integrations import Integration, IntegrationFactory

logger = logging.getLogger(__name__)

load_dotenv()


def create_app(database_path: str | Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    database_path = Path(database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.warning("REGISTRY: %s", IntegrationFactory._registry)
        logger.warning("TELEGRAM_ENABLED: %r", os.environ.get("TELEGRAM_ENABLED"))
        configured: list[Integration] = IntegrationFactory.create_configured()
        logger.warning(
            "CONFIGURED: %s",
            [integration.name for integration in configured],
        )
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

    app = FastAPI(
        title="Appointments API",
        description=(
            "Create, inspect, reschedule, and cancel appointments. "
            "All appointment times are ISO 8601 datetimes."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(create_users_router(database_path))
    app.include_router(create_appointments_router(database_path))
    app.include_router(create_agent_router(database_path))

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

    return app


app = create_app()
