"""External messaging integrations.

Concrete integrations (telegram, google_calendar) are imported lazily by
``IntegrationFactory`` so their heavy dependencies (aiogram, openai, google
client libraries) are only loaded when an integration is actually enabled.
"""

from integrations.base import Integration, IntegrationConfigurationError
from integrations.factory import IntegrationFactory

__all__ = [
    "Integration",
    "IntegrationConfigurationError",
    "IntegrationFactory",
]
