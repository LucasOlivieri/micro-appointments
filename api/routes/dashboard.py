import hmac
import os
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from api.dependencies import _service
from config import Config
from core.repositories.customer import CustomerRepository


def _setting(name: str) -> str | None:
    return os.environ.get(name) or getattr(Config, name, None)


def _authenticate(request: Request, database_path: Path) -> dict[str, str]:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    session = getattr(request.app.state, "dashboard_sessions", {}).get(token)
    if scheme.lower() != "bearer" or not token or session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if session.get("database_path") != str(database_path):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return session


def _serialize_customer(customer) -> dict[str, object]:
    return {
        "id": customer.id,
        "phone": customer.phone,
        "name": customer.name,
        "info": customer.info,
    }


async def _dashboard_data(database_path: Path, session: dict[str, str]):
    service = _service(database_path)
    all_users = await service.list_users()
    if session["role"] == "admin":
        users = all_users
    else:
        users = [user for user in all_users if user["id"] == session["user_id"]]

    user_ids = [user["id"] for user in users]
    rules = []
    appointment_types = []
    blocked_times = []
    appointments = []
    for user_id in user_ids:
        rules.extend(await service.list_rules(user_id))
        appointment_types.extend(await service.list_appointment_types(user_id))
        blocked_times.extend(await service.list_blocked_time_rows(user_id))
        appointments.extend(await service.list_appointments(user_id))

    customers = await CustomerRepository().list_all()
    if session["role"] != "admin":
        appointment_phones = {item["phone"] for item in appointments}
        customers = [
            customer for customer in customers if customer.phone in appointment_phones
        ]

    return {
        "role": session["role"],
        "users": users,
        "rules": rules,
        "appointment_types": appointment_types,
        "blocked_times": blocked_times,
        "appointments": appointments,
        "customers": [_serialize_customer(customer) for customer in customers],
    }


def create_router(database_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_page():
        page = Path("api/templates/dashboard.html")
        return HTMLResponse(page.read_text(encoding="utf-8"))

    @router.post("/dashboard/login")
    async def dashboard_login(payload: dict[str, str], request: Request):
        key = payload.get("key", "")
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        superuser_key = _setting("DASHBOARD_SUPERUSER_KEY")
        if superuser_key and hmac.compare_digest(key, superuser_key):
            role = "admin"
            user_id = ""
        else:
            user_id = key
            if await _service(database_path).get_user(user_id) is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            role = "user"

        token = secrets.token_urlsafe(32)
        request.app.state.dashboard_sessions[token] = {
            "role": role,
            "user_id": user_id,
            "database_path": str(database_path),
        }
        return {"token": token, "role": role}

    @router.get("/dashboard/data")
    async def dashboard_data(request: Request):
        session = _authenticate(request, database_path)
        return await _dashboard_data(database_path, session)

    @router.post("/dashboard/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def dashboard_logout(request: Request):
        authorization = request.headers.get("Authorization", "")
        _, _, token = authorization.partition(" ")
        request.app.state.dashboard_sessions.pop(token, None)

    return router
