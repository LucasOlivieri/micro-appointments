from pathlib import Path

from api.dependencies import DEFAULT_DATABASE_PATH

_DEFAULT_CONVERSATION_ID = "gradio-chat"


async def run_agent(*args, **kwargs):
    from bot.agent import run_agent as _run_agent

    return await _run_agent(*args, **kwargs)


def create_chat(database_path: Path = DEFAULT_DATABASE_PATH):
    from gradio import ChatInterface, Textbox

    async def chat(message: str, history: list, conversation_id: str) -> str:
        if not message or not message.strip():
            return "Please enter a request."
        cid = conversation_id.strip() if conversation_id else _DEFAULT_CONVERSATION_ID
        try:
            return await run_agent(message, cid)
        except Exception as error:
            return f"Unable to reach the appointment agent: {error}"

    return ChatInterface(
        fn=chat,
        title="Appointment Agent",
        description="Ask for available slots, schedule an appointment, "
        "or move an existing one.",
        additional_inputs=[
            Textbox(
                label="Conversation ID (optional)",
                placeholder=_DEFAULT_CONVERSATION_ID,
            )
        ],
        examples=[
            ["Hola, quiero un turno"],
            ["Quiero un turno con Lucas"],
            ["¿Qué horarios tenés disponible?"],
        ],
    )


def gradio_chat(app):
    from gradio.routes import mount_gradio_app

    return mount_gradio_app(
        app,
        create_chat(),
        path="/chat",
    )
