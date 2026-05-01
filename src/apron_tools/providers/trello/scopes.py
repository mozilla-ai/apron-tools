"""Scope definitions for Trello tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class TrelloScope(Scope):
    """Trello API access scopes."""

    READ = (
        "read",
        "Read Access",
        "View your Trello boards, lists, and cards",
        "read",
        False,
    )
    WRITE = (
        "write",
        "Write Access",
        "Create and modify boards, lists, and cards",
        "write",
        False,
    )


SCOPES: dict[str, list[TrelloScope]] = {
    "trello_list_boards": [TrelloScope.READ],
    "trello_list_lists": [TrelloScope.READ],
    "trello_list_cards": [TrelloScope.READ],
    "trello_get_card": [TrelloScope.READ],
    "trello_create_card": [TrelloScope.WRITE],
    "trello_move_cards": [TrelloScope.WRITE],
    "trello_set_card_due_dates": [TrelloScope.WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="trello",
    display_name="Trello",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
