import json
from typer.testing import CliRunner

import setup


runner = CliRunner()


def test_help_lists_setup_options():
    result = runner.invoke(setup.app, ["--help"])

    assert result.exit_code == 0
    assert "--output" in result.stdout
    assert "--users" in result.stdout
    assert "--timezone" in result.stdout


def test_weekday_selector_returns_selected_weekday(monkeypatch):
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda self: 2})(),
    )

    assert setup._prompt_weekday() == 2


def test_done_finishes_rule_collection(monkeypatch):
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda self: setup.DONE})(),
    )

    assert setup._rules("user") == []


def test_blocked_datetime_uses_user_timezone(monkeypatch):
    answers = iter([
        "2026", "8", "25", "9", "30",
        "2026", "8", "25", "10", "45",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda self: "datetime"})(),
    )

    start, end = setup._prompt_blocked_range("user", "America/Argentina/Buenos_Aires")

    assert start == "2026-08-25T09:30:00-03:00"
    assert end == "2026-08-25T10:45:00-03:00"


def test_blocked_date_range_outputs_full_timezone_datetimes(monkeypatch):
    answers = iter([
        "2026", "8", "25",
        "2026", "8", "27",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda self: "date"})(),
    )

    start, end = setup._prompt_blocked_range("user", "UTC")

    assert start == "2026-08-25T00:00:00+00:00"
    assert end == "2026-08-27T00:00:00+00:00"


def test_build_config_creates_requested_number_of_users(monkeypatch):
    def build_user(timezone):
        return {
            "id": timezone,
            "timezone": timezone,
            "rules": [{"id": 1}],
            "appointment_types": [{"id": 1}],
            "blocked_times": [{"id": 1}],
        }

    monkeypatch.setattr(setup, "build_user", build_user)

    config = setup.build_config(2, "UTC")

    assert len(config["users"]) == 2
    assert config["users"][0]["timezone"] == "UTC"
    for collection_name in ("rules", "appointment_types", "blocked_times"):
        assert [
            item["id"]
            for user in config["users"]
            for item in user[collection_name]
        ] == [1, 2]


def test_generated_config_is_json_serializable(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "build_config", lambda users, timezone: {
        "users": [{"id": "user", "timezone": timezone}],
    })
    output = tmp_path / "config.json"

    result = runner.invoke(setup.app, ["--output", str(output), "--timezone", "UTC"])

    assert result.exit_code == 0
    assert json.loads(output.read_text()) == {
        "users": [{"id": "user", "timezone": "UTC"}],
    }