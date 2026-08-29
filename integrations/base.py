from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import ClassVar


class IntegrationConfigurationError(ValueError):
    """Raised when an enabled integration is missing required configuration."""


class Integration(ABC):
    """Common lifecycle and configuration contract for external integrations."""

    name: ClassVar[str]
    required_env_vars: ClassVar[tuple[str, ...]] = ()

    def __init__(self, environ: Mapping[str, str]):
        self.environ = environ

    @classmethod
    def validate_env(cls, environ: Mapping[str, str]) -> None:
        missing = [
            variable
            for variable in cls.required_env_vars
            if not environ.get(variable, "").strip()
        ]
        if missing:
            variables = ", ".join(missing)
            raise IntegrationConfigurationError(
                f"{cls.name} integration is missing required environment "
                f"variables: {variables}"
            )

    @classmethod
    @abstractmethod
    def from_env(cls, environ: Mapping[str, str]) -> Integration:
        """Build a configured integration after validating its environment."""

    @abstractmethod
    async def start(self) -> None:
        """Start accepting messages."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop accepting messages and release resources."""
