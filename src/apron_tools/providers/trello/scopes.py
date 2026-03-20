"""Scope definitions for Trello tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class TrelloScope(StrEnum):
    """Trello API access scopes."""

    READ = "read"
    WRITE = "write"


SCOPES: dict[str, list[TrelloScope]] = {
    "trello_list_boards": [TrelloScope.READ],
    "trello_list_lists": [TrelloScope.READ],
    "trello_list_cards": [TrelloScope.READ],
    "trello_get_card": [TrelloScope.READ],
    "trello_create_card": [TrelloScope.WRITE],
    "trello_move_card": [TrelloScope.WRITE],
    "trello_set_card_due_date": [TrelloScope.WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="trello",
    display_name="Trello",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
