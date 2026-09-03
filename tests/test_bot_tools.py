from bot.tools import build_tools


def test_bot_exposes_customer_lookup_and_cancellation_tools():
    tools = build_tools("http://localhost:8000")
    names = {tool.name for tool in tools}

    assert "find_customer_appointments" in names
    assert "cancel_appointment" in names
