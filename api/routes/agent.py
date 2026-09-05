from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dependencies import DEFAULT_DATABASE_PATH
from bot.agent import run_agent
from bot.handler import build_agent_prompt
from core.models import User


async def _resolve_user_id(database_path: Path, user_id: str | None) -> str:
    user_id = (user_id or "").strip()
    if user_id:
        return user_id

    rows = await User.all().order_by("name", "id").values("id")
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

        user_id = await _resolve_user_id(database_path, payload.get("user_id"))
        user = await User.filter(id=user_id).first() if user_id else None
        timezone = user.timezone if user else None
        message_template = user.message if user else None
        system_prompt = user.system_prompt if user else None
        message = str(payload.get("message", ""))
        conversation_id = str(payload.get("conversation_id") or "ws-default")

        if not message or not message.strip():
            await websocket.send_json({"response": "Please enter a request."})
            await websocket.close()
            return

        try:
            prompt = build_agent_prompt(message, user_id, timezone, message_template)
            if system_prompt:
                response = await run_agent(
                    prompt, conversation_id, system_prompt=system_prompt
                )
            else:
                response = await run_agent(prompt, conversation_id)
        except Exception as error:
            response = f"Unable to reach the appointment agent: {error}"

        await websocket.send_json({"response": response})
        await websocket.close()

    return router
