"""Slack provider.

API docs: https://docs.slack.dev/apis/web-api/
"""

from __future__ import annotations

#: Prefix Slack uses for bot-user OAuth tokens (``xoxb-``). Bot tokens
#: authenticate as the workspace's Slack app and cannot access user-perspective
#: data (search.messages, users.conversations, etc.).
BOT_TOKEN_PREFIX = "xoxb-"

#: Prefix Slack uses for user OAuth tokens (``xoxp-``). User tokens act on
#: behalf of an installing user and are required for user-scoped APIs.
USER_TOKEN_PREFIX = "xoxp-"


def is_bot_token(token: str) -> bool:
    """Return True if ``token`` is a Slack bot token (xoxb-)."""
    return token.startswith(BOT_TOKEN_PREFIX)


def is_user_token(token: str) -> bool:
    """Return True if ``token`` is a Slack user token (xoxp-)."""
    return token.startswith(USER_TOKEN_PREFIX)


__all__ = [
    "BOT_TOKEN_PREFIX",
    "USER_TOKEN_PREFIX",
    "is_bot_token",
    "is_user_token",
]
