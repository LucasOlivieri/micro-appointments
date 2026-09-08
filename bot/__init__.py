"""OpenAI appointment scheduling agent.

``bot.agent`` and ``bot.tools`` are imported lazily by their consumers so the
OpenAI SDK is only loaded when the agent is actually used.
"""
