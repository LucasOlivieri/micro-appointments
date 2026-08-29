import logging
import os
from collections.abc import Mapping

from dotenv import load_dotenv

from integrations.base import Integration

logger = logging.getLogger(__name__)


class IntegrationFactory:
    """Create enabled integrations from environment configuration."""

    _registry: dict[str, type[Integration]] = {}

    @classmethod
    def register(cls, integration_class: type[Integration]) -> type[Integration]:
        cls._registry[integration_class.name] = integration_class
        return integration_class

    @classmethod
    def create_configured(
        cls, environ: Mapping[str, str] | None = None
    ) -> list[Integration]:
        load_dotenv()
        environment = os.environ if environ is None else environ
        integrations: list[Integration] = []
        for name, integration_class in cls._registry.items():
            enabled = environment.get(f"{name.upper()}_ENABLED", "").lower()
            if enabled not in {"1", "true", "yes", "on"}:
                continue
            try:
                integrations.append(integration_class.from_env(environment))
            except ValueError as error:
                logger.error("Skipping %s integration: %s", name, error)
        return integrations
