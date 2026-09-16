from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_404_NOT_FOUND

from api.admin.router import verify_admin
from api.dependencies import _service

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _templates() -> Jinja2Templates:
    return Jinja2Templates(directory=str(_TEMPLATES_DIR))


def create_router(database_path: Path) -> APIRouter:
    router = APIRouter(dependencies=[Depends(verify_admin)])

    @router.get("/setup", response_class=HTMLResponse, include_in_schema=False)
    async def setup_page():
        page = _TEMPLATES_DIR / "setup.html"
        return HTMLResponse(page.read_text(encoding="utf-8"))

    @router.get("/setup/data")
    async def setup_data():
        """Aggregate all setup data: users, rules, appointment types, blocked times."""
        service = _service(database_path)
        users = await service.list_users()
        result = []
        for user in users:
            rules = await service.list_rules(user["id"])
            appointment_types = await service.list_appointment_types(user["id"])
            blocked_times = await service.list_blocked_time_rows(user["id"])
            result.append(
                {
                    **user,
                    "rules": rules,
                    "appointment_types": appointment_types,
                    "blocked_times": blocked_times,
                }
            )
        return result

    # ── Users ──

    @router.post("/setup/users")
    async def create_user(payload: dict):
        service = _service(database_path)
        user = await service.create_user(payload)
        return user

    @router.put("/setup/users/{user_id}")
    async def update_user(user_id: str, payload: dict):
        service = _service(database_path)
        user = await service.upsert_user({"id": user_id, **payload})
        return user

    @router.delete("/setup/users/{user_id}")
    async def delete_user(user_id: str):
        service = _service(database_path)
        result = await service.delete_user(user_id)
        if result is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
        return result

    # ── Rules ──

    @router.post("/setup/rules")
    async def create_rule(payload: dict):
        service = _service(database_path)
        rule = await service.create_rule(payload)
        return rule

    @router.put("/setup/rules/{rule_id}")
    async def update_rule(rule_id: int, payload: dict):
        service = _service(database_path)
        rule = await service.update_rule(rule_id, payload)
        return rule

    @router.delete("/setup/rules/{rule_id}")
    async def delete_rule(rule_id: int):
        service = _service(database_path)
        await service.delete_rule(rule_id)
        return {"ok": True}

    # ── Appointment Types ──

    @router.post("/setup/appointment-types")
    async def create_appointment_type(payload: dict):
        service = _service(database_path)
        atype = await service.create_appointment_type(payload)
        return atype

    @router.put("/setup/appointment-types/{type_id}")
    async def update_appointment_type(type_id: int, payload: dict):
        service = _service(database_path)
        atype = await service.update_appointment_type(type_id, payload)
        return atype

    @router.delete("/setup/appointment-types/{type_id}")
    async def delete_appointment_type(type_id: int):
        service = _service(database_path)
        await service.delete_appointment_type(type_id)
        return {"ok": True}

    # ── Blocked Times ──

    @router.post("/setup/blocked-times")
    async def create_blocked_time(payload: dict):
        service = _service(database_path)
        bt = await service.create_blocked_time(payload)
        return bt

    @router.put("/setup/blocked-times/{bt_id}")
    async def update_blocked_time(bt_id: int, payload: dict):
        service = _service(database_path)
        bt = await service.update_blocked_time(bt_id, payload)
        return bt

    @router.delete("/setup/blocked-times/{bt_id}")
    async def delete_blocked_time(bt_id: int):
        service = _service(database_path)
        await service.blocked_times.delete_by_id(bt_id)
        return {"ok": True}

    return router
