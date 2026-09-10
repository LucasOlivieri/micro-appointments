import asyncio
import logging
from collections.abc import Mapping
from typing import Self

import discord
from discord import Message

from bot.handler import handle_agent_message
from integrations.base import Integration
from integrations.factory import IntegrationFactory

logger = logging.getLogger(__name__)


@IntegrationFactory.register
class DiscordIntegration(Integration):
    """Discord bot integration for the shared receptionist agent."""

    name = "discord"
    required_env_vars = ("DISCORD_BOT_TOKEN",)

    def __init__(self, environ: Mapping[str, str]):
        super().__init__(environ)
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self._started = False
        self._background_task: asyncio.Task | None = None
        self._register_handlers()

    def _discord_task_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Discord bot task cancelled")
        except Exception:
            logger.exception("Discord bot crashed")

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Self:
        cls.validate_env(environ)
        return cls(environ)

    def _register_handlers(self) -> None:
        @self.client.event
        async def on_ready() -> None:
            logger.info("Discord bot logged in as %s", self.client.user)

        @self.client.event
        async def on_message(message: Message) -> None:
            if message.author == self.client.user:
                return
            if not message.content or not message.content.strip():
                return
            conversation_id = f"discord:{message.channel.id}:{message.author.id}"
            try:
                async with message.channel.typing():
                    response = await handle_agent_message(
                        message.content,
                        conversation_id,
                    )
                await message.reply(response)
            except Exception as error:
                await message.reply(f"Unable to reach the appointment agent: {error}")

    async def start(self) -> None:
        if self._started:
            return
        logger.info("Starting Discord bot...")
        self._background_task = asyncio.create_task(
            self.client.start(self.environ["DISCORD_BOT_TOKEN"]),
        )
        self._background_task.add_done_callback(self._discord_task_done)
        self._started = True
        logger.info("Discord integration enabled.")

    async def stop(self) -> None:
        if not self._started:
            return
        await self.client.close()
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
        self._started = False
