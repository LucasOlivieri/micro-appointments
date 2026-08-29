import pytest

from integrations.base import Integration, IntegrationConfigurationError
from integrations.factory import IntegrationFactory


class ExampleIntegration(Integration):
    name = "example"
    required_env_vars = ("EXAMPLE_TOKEN", "EXAMPLE_URL")

    @classmethod
    def from_env(cls, environ):
        cls.validate_env(environ)
        return cls(environ)

    async def start(self):
        pass

    async def stop(self):
        pass


def test_validation_reports_all_missing_variables():
    with pytest.raises(
        IntegrationConfigurationError, match="EXAMPLE_TOKEN, EXAMPLE_URL"
    ):
        ExampleIntegration.validate_env({})


def test_factory_only_creates_explicitly_enabled_integrations():
    IntegrationFactory.register(ExampleIntegration)

    assert IntegrationFactory.create_configured({}) == []
    assert (
        IntegrationFactory.create_configured(
            {
                "EXAMPLE_ENABLED": "true",
                "EXAMPLE_TOKEN": "token",
                "EXAMPLE_URL": "https://example.test",
            }
        )[0].name
        == "example"
    )
