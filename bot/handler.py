from datetime import datetime
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo

from bot.agent import run_agent

_MESSAGE_TEMPLATE = Template(
    (Path(__file__).parent / "templates" / "message.md").read_text()
)


async def handle_agent_message(
    message: str,
    conversation_id: str,
    user_id: str | None = None,
) -> str:
    """Build the standard prompt and run one agent conversation turn."""
    return await run_agent(
        build_agent_prompt(message, user_id),
        conversation_id,
    )


def build_agent_prompt(
    message: str,
    user_id: str | None = None,
    timezone: str | None = None,
    message_template: str | None = None,
) -> str:
    """Build the standard user-aware prompt without executing the agent."""
    current_time = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now()
    template = Template(message_template) if message_template else _MESSAGE_TEMPLATE
    return template.substitute(
        user_id=user_id or "not provided",
        current_time=str(current_time),
        message=message,
    )
