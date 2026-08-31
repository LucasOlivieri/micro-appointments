import logging
from collections.abc import Mapping

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, Update

from bot.handler import handle_agent_message
from integrations.base import Integration
from integrations.factory import IntegrationFactory

logger = logging.getLogger(__name__)


@IntegrationFactory.register
class TelegramIntegration(Integration):
    """Telegram webhook integration for the shared receptionist agent."""

    name = "telegram"
    required_env_vars = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_URL")

    def __init__(self, environ: Mapping[str, str]):
        super().__init__(environ)
        self.bot = Bot(token=environ["TELEGRAM_BOT_TOKEN"])
        self.dispatcher = Dispatcher()
        self.router = Router()
        self._started = False
        self._register_handlers()

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> TelegramIntegration:
        cls.validate_env(environ)
        return cls(environ)

    def _register_handlers(self) -> None:
        @self.router.message()
        async def handle_message(message: Message) -> None:
            if not message.text or not message.text.strip() or not message.chat:
                return
            conversation_id = f"telegram:{message.chat.id}"
            try:
                response = await handle_agent_message(
                    message.text,
                    conversation_id,
                )
                await message.answer(response)
            except Exception as error:
                await message.answer(f"Unable to reach the appointment agent: {error}")

    async def start(self) -> None:
        if self._started:
            return
        self.dispatcher.include_router(self.router)
        await self.bot.set_webhook(
            url=self.environ["TELEGRAM_WEBHOOK_URL"],
            secret_token=self.environ.get("TELEGRAM_WEBHOOK_SECRET") or None,
        )
        self._started = True
        logger.info("Telegram integration enabled.")

    async def stop(self) -> None:
        if not self._started:
            await self.bot.session.close()
            return
        await self.bot.delete_webhook()
        await self.bot.session.close()
        self._started = False

    async def handle_webhook(self, payload: Mapping[str, object]) -> None:
        update = Update.model_validate(payload, context={"bot": self.bot})
        await self.dispatcher.feed_update(self.bot, update)
