from datetime import datetime
from pathlib import Path
from string import Template

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dependencies import DEFAULT_DATABASE_PATH, _service
from bot.agent import run_agent


def _resolve_user_id(database_path: Path, user_id: str | None) -> str:
    user_id = (user_id or "").strip()
    if user_id:
        return user_id

    rows = list(_service(database_path).db.query(
        "SELECT id FROM users ORDER BY LOWER(name), id"
    ))
    if len(rows) == 1:
        return str(rows[0]["id"])
    return ""


def create_router(database_path: Path = DEFAULT_DATABASE_PATH) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/agent")
    async def agent_websocket(websocket: WebSocket):
        await websocket.accept()
        try:
            payload = await websocket.receive_json()
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.send_json({"response": "Invalid message payload."})
            await websocket.close()
            return

        if not isinstance(payload, dict):
            await websocket.send_json({"response": "Invalid message payload."})
            await websocket.close()
            return

        user_id = _resolve_user_id(database_path, payload.get("user_id"))
        message = str(payload.get("message", ""))
        conversation_id = str(payload.get("conversation_id") or "ws-default")

        if not message or not message.strip():
            await websocket.send_json({"response": "Please enter a request."})
            await websocket.close()
            return

        current_time = str(datetime.now())
        prompt = Template(open("bot/templates/message.md").read()).substitute(
            user_id=user_id or "not provided",
            current_time=current_time,
            message=message,
        )
        try:
            response = await run_agent(prompt, conversation_id)
        except Exception as error:
            response = f"Unable to reach the appointment agent: {error}"

        await websocket.send_json({"response": response})
        await websocket.close()

    return router