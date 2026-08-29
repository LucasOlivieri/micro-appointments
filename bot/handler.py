from datetime import datetime
from pathlib import Path
from string import Template

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


def build_agent_prompt(message: str, user_id: str | None = None) -> str:
    """Build the standard user-aware prompt without executing the agent."""
    return _MESSAGE_TEMPLATE.substitute(
        user_id=user_id or "not provided",
        current_time=str(datetime.now()),
        message=message,
    )
