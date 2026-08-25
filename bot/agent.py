import os
from pathlib import Path

from agents import Agent, OpenAIProvider, Runner, RunConfig, SQLiteSession
from dotenv import load_dotenv

from bot.tools import build_tools


INSTRUCTIONS = open("bot/templates/system-prompt.md").read()


def build_agent(api_url: str | None = None, model: str | None = None) -> Agent:
    load_dotenv()
    api_url = api_url or os.getenv("APPOINTMENTS_API_URL", "http://127.0.0.1:8000")
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return Agent(
        name="Appointment Assistant",
        instructions=INSTRUCTIONS,
        model=model,
        tools=build_tools(api_url),
    )


async def run_agent(
    message: str,
    conversation_id: str,
    memory_path: str | Path | None = None,
    api_url: str | None = None,
    model: str | None = None,
) -> str:
    """Run one turn and persist the conversation in SQLite."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    memory_path = memory_path or os.getenv("AGENT_MEMORY_PATH", "memory.sqlite3")
    provider = OpenAIProvider(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    result = await Runner.run(
        build_agent(api_url=api_url, model=model),
        message,
        session=SQLiteSession(conversation_id, memory_path),
        run_config=RunConfig(model_provider=provider),
    )
    return result.final_output