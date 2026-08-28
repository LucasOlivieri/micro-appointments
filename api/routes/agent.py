from datetime import datetime
from string import Template

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bot.agent import run_agent


def create_router() -> APIRouter:
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

        user_id = str(payload.get("user_id", "")).strip()
        message = str(payload.get("message", ""))
        conversation_id = str(payload.get("conversation_id") or "ws-default")

        if not message or not message.strip():
            await websocket.send_json({"response": "Please enter a request."})
            await websocket.close()
            return
        if not user_id:
            await websocket.send_json({
                "response": "Enter an appointment user ID before sending a request."
            })
            await websocket.close()
            return

        current_time = str(datetime.now())
        prompt = Template(open("bot/templates/message.md").read()).substitute(
            user_id=user_id, current_time=current_time, message=message
        )
        try:
            response = await run_agent(prompt, conversation_id)
        except Exception as error:
            response = f"Unable to reach the appointment agent: {error}"

        await websocket.send_json({"response": response})
        await websocket.close()

    return router