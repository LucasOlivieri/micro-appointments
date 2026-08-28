from pathlib import Path

from fastapi import FastAPI

from api.dependencies import DEFAULT_DATABASE_PATH
from api.routes.agent import create_router as create_agent_router
from api.routes.appointments import create_router as create_appointments_router
from api.routes.users import create_router as create_users_router


def create_app(database_path: str | Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    database_path = Path(database_path)
    app = FastAPI(
        title="Appointments API",
        description=(
            "Create, inspect, reschedule, and cancel appointments. "
            "All appointment times are ISO 8601 datetimes."
        ),
        version="1.0.0",
    )
    app.include_router(create_users_router(database_path))
    app.include_router(create_appointments_router(database_path))
    app.include_router(create_agent_router())
    return app


app = create_app()
