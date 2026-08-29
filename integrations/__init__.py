"""External messaging integrations."""

from integrations.base import Integration, IntegrationConfigurationError
from integrations.factory import IntegrationFactory
from integrations.telegram import TelegramIntegration

__all__ = [
    "Integration",
    "IntegrationConfigurationError",
    "IntegrationFactory",
    "TelegramIntegration",
]
