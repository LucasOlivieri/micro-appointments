from agents import Agent, OpenAIProvider, RunConfig, Runner, SQLiteSession

from bot.tools import build_tools
from config import Config

INSTRUCTIONS = open("bot/templates/system-prompt.md").read()


def build_agent(model: str | None = None) -> Agent:
    api_url = Config.APPOINTMENTS_API_URL
    model = model or Config.OPENAI_MODEL
    return Agent(
        name="Appointment Assistant",
        instructions=INSTRUCTIONS,
        model=model,
        tools=build_tools(api_url),
    )


async def run_agent(
    message: str,
    conversation_id: str,
    api_url: str | None = None,
    model: str | None = None,
) -> str:
    """Run one turn and persist the conversation in SQLite."""
    api_key = Config.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    memory_path = Config.AGENT_MEMORY_PATH
    provider = OpenAIProvider(
        api_key=api_key,
        base_url=Config.OPENAI_BASE_URL or None,
    )
    result = await Runner.run(
        build_agent(model=model),
        message,
        session=SQLiteSession(conversation_id, memory_path),
        run_config=RunConfig(model_provider=provider),
    )
    return result.final_output
