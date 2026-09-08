import importlib
import logging
import os
from collections.abc import Mapping

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
    def _import_enabled_builtins(cls, environ: Mapping[str, str]) -> None:
        """Import a built-in integration module only if its env flag is enabled.

        Importing a module triggers its ``@IntegrationFactory.register``
        decorator. Skipping disabled integrations keeps their heavy
        dependencies (aiogram, openai, google client libraries) unloaded.
        """
        for name in ("telegram", "google_calendar"):
            enabled = environ.get(f"{name.upper()}_ENABLED", "").lower()
            if enabled not in {"1", "true", "yes", "on"}:
                continue
            importlib.import_module(f"integrations.{name}")

    @classmethod
    def create_configured(
        cls, environ: Mapping[str, str] | None = None
    ) -> list[Integration]:
        environment = os.environ if environ is None else environ
        cls._import_enabled_builtins(environment)
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
