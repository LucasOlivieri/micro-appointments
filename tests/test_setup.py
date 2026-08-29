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


def test_time_choices_cover_hours_and_minutes():
    hour_values = [choice.value for choice in setup.HOUR_CHOICES]
    minute_values = [choice.value for choice in setup.MINUTE_CHOICES]

    assert hour_values == list(range(24))
    assert minute_values == list(range(0, 60, 5))
    assert setup.MINUTE_CHOICES[0].title == "00"
    assert setup.MINUTE_CHOICES[-1].title == "55"


def test_month_choices_cover_january_to_december():
    assert [choice.value for choice in setup.MONTH_CHOICES] == list(range(1, 13))
    assert [choice.title for choice in setup.MONTH_CHOICES] == [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]


def test_duration_choices_cover_five_minutes_to_four_hours():
    values = [choice.value for choice in setup.DURATION_CHOICES]

    assert values == list(range(5, 241, 5))


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


def test_blocked_date_range_uses_user_timezone(monkeypatch):
    answers = iter(
        [
            "2026",
            "25",
            "2026",
            "25",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    selections = iter([8, 8])
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type(
            "Prompt", (), {"ask": lambda self: next(selections)}
        )(),
    )

    start, end = setup._prompt_blocked_range("user", "America/Argentina/Buenos_Aires")

    assert start == "2026-08-25T00:00:00-03:00"
    assert end == "2026-08-25T00:00:00-03:00"


def test_blocked_date_range_outputs_full_timezone_datetimes(monkeypatch):
    answers = iter(
        [
            "2026",
            "25",
            "2026",
            "27",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    selections = iter([8, 8])
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type(
            "Prompt", (), {"ask": lambda self: next(selections)}
        )(),
    )

    start, end = setup._prompt_blocked_range("user", "UTC")

    assert start == "2026-08-25T00:00:00+00:00"
    assert end == "2026-08-27T00:00:00+00:00"


def test_manage_users_can_create_and_delete_user(monkeypatch):
    new_user = {
        "id": "new-user",
        "name": "New User",
        "email": "new@example.com",
        "timezone": "UTC",
        "rules": [],
        "appointment_types": [],
        "blocked_times": [],
    }
    selections = iter(["create", "delete", new_user, "finish"])
    monkeypatch.setattr(
        setup.questionary,
        "select",
        lambda *args, **kwargs: type(
            "Prompt", (), {"ask": lambda self: next(selections)}
        )(),
    )
    monkeypatch.setattr(setup, "build_user", lambda timezone: new_user)

    assert setup._manage_users([], "UTC") == []


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
            item["id"] for user in config["users"] for item in user[collection_name]
        ] == [1, 2]


def test_generated_config_is_json_serializable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        setup,
        "build_config",
        lambda users, timezone: {
            "users": [{"id": "user", "timezone": timezone}],
        },
    )
    output = tmp_path / "config.json"

    result = runner.invoke(setup.app, ["--output", str(output), "--timezone", "UTC"])

    assert result.exit_code == 0
    assert json.loads(output.read_text()) == {
        "users": [{"id": "user", "timezone": "UTC"}],
    }
