"""Trello tool functions for interacting with the Trello REST API."""

from __future__ import annotations

from typing import Any

import httpx

from apron_tools._utils import parse_csv_ids
from apron_tools.providers.trello.types import (
    CreateCardParams,
    CreateCardResult,
    GetCardParams,
    GetCardResult,
    ListBoardsParams,
    ListBoardsResult,
    ListCardsParams,
    ListCardsResult,
    ListListsParams,
    ListListsResult,
    MoveCardItem,
    MoveCardsParams,
    MoveCardsResult,
    SetCardDueDateItem,
    SetCardDueDatesParams,
    SetCardDueDatesResult,
    TrelloBoard,
    TrelloCard,
    TrelloCardDetail,
    TrelloList,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.trello.com/1"
_TIMEOUT = 60.0
_API_DOCS = "https://developer.atlassian.com/cloud/trello/rest/"


def _auth_params(api_key: str, token: str) -> dict[str, str]:
    """Build authentication query parameters for a Trello API request."""
    return {"key": api_key, "token": token}


def _redact_error(exc: Exception) -> str:
    """Return an error string with Trello auth query params redacted."""
    import re

    return re.sub(r"(key|token)=[^&\s]+", r"\1=REDACTED", str(exc))


@tool(
    scopes=SCOPES["trello_list_boards"],
    api_docs=f"{_API_DOCS}api-group-members/#api-members-id-boards-get",
    provider="trello",
)
async def trello_list_boards(
    params: ListBoardsParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> ListBoardsResult:
    """List boards the authenticated Trello member belongs to."""
    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "filter": params.filter,
        "fields": "name,id,closed,url,shortUrl,prefs",
        "lists": "none",
        "limit": params.limit,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/members/me/boards", params=query)
    except httpx.HTTPError as exc:
        return ListBoardsResult(success=False, error=_redact_error(exc))

    if not resp.is_success:
        return ListBoardsResult(
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    boards = [TrelloBoard.model_validate(b) for b in resp.json()]
    return ListBoardsResult(success=True, boards=boards)


@tool(
    scopes=SCOPES["trello_list_lists"],
    api_docs=f"{_API_DOCS}api-group-boards/#api-boards-id-lists-get",
    provider="trello",
)
async def trello_list_lists(
    params: ListListsParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> ListListsResult:
    """List lists on a Trello board."""
    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "fields": "name,id,closed,pos",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/boards/{params.board_id}/lists", params=query)
    except httpx.HTTPError as exc:
        return ListListsResult(success=False, error=_redact_error(exc))

    if not resp.is_success:
        return ListListsResult(
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    lists = [TrelloList.model_validate(lst) for lst in resp.json()]
    return ListListsResult(success=True, lists=lists)


@tool(
    scopes=SCOPES["trello_list_cards"],
    api_docs=f"{_API_DOCS}api-group-lists/#api-lists-id-cards-get",
    provider="trello",
)
async def trello_list_cards(
    params: ListCardsParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> ListCardsResult:
    """List cards on a Trello board or in a specific list."""
    if not params.list_id and not params.board_id:
        return ListCardsResult(success=False, error="Either board_id or list_id must be provided.")

    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "filter": params.filter,
        "fields": "name,id,idList,due,dueComplete,shortUrl,closed",
        "members": "false",
        "limit": params.limit,
    }

    endpoint = (
        f"{base_url}/lists/{params.list_id}/cards" if params.list_id else f"{base_url}/boards/{params.board_id}/cards"
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(endpoint, params=query)
    except httpx.HTTPError as exc:
        return ListCardsResult(success=False, error=_redact_error(exc))

    if not resp.is_success:
        return ListCardsResult(
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    cards = [TrelloCard.model_validate(c) for c in resp.json()]
    return ListCardsResult(success=True, cards=cards)


@tool(
    scopes=SCOPES["trello_get_card"],
    api_docs=f"{_API_DOCS}api-group-cards/#api-cards-id-get",
    provider="trello",
)
async def trello_get_card(
    params: GetCardParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> GetCardResult:
    """Retrieve details of a single Trello card."""
    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "fields": "name,id,desc,due,dueComplete,idList,idBoard,shortUrl,url,closed",
        "list": "true",
        "board": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{base_url}/cards/{params.card_id}", params=query)
    except httpx.HTTPError as exc:
        return GetCardResult(success=False, error=_redact_error(exc))

    if not resp.is_success:
        return GetCardResult(
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    card = TrelloCardDetail.model_validate(resp.json())
    return GetCardResult(success=True, card=card)


@tool(
    scopes=SCOPES["trello_create_card"],
    api_docs=f"{_API_DOCS}api-group-cards/#api-cards-post",
    provider="trello",
)
async def trello_create_card(
    params: CreateCardParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> CreateCardResult:
    """Create a new card on a Trello list."""
    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "idList": params.list_id,
        "name": params.name,
        "desc": params.description,
        "pos": params.position,
    }
    if params.due_date:
        query["due"] = params.due_date

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{base_url}/cards", params=query)
    except httpx.HTTPError as exc:
        return CreateCardResult(success=False, error=_redact_error(exc))

    if not resp.is_success:
        return CreateCardResult(
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    return CreateCardResult.model_validate(resp.json())


async def _move_one_card(
    card_id: str,
    query: dict[str, Any],
    base_url: str,
) -> MoveCardItem:
    """Move a single Trello card and shape the per-card outcome."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.put(f"{base_url}/cards/{card_id}", params=query)
    except httpx.HTTPError as exc:
        return MoveCardItem(card_id=card_id, success=False, error=_redact_error(exc))

    if not resp.is_success:
        return MoveCardItem(
            card_id=card_id,
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return MoveCardItem(card_id=data.get("id", card_id), success=True, name=data.get("name", ""))


@tool(
    scopes=SCOPES["trello_move_cards"],
    api_docs=f"{_API_DOCS}api-group-cards/#api-cards-id-put",
    provider="trello",
)
async def trello_move_cards(
    params: MoveCardsParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> MoveCardsResult:
    """Move one or more Trello cards to a different list.

    ``list_id`` and ``position`` are applied to every card in the call.
    Per-card outcomes are returned in ``items`` so partial failures surface
    without aborting the whole bulk call.
    """
    card_ids = parse_csv_ids(params.card_ids)
    if not card_ids:
        return MoveCardsResult(success=False, error="No card IDs provided.")

    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "idList": params.list_id,
        "pos": params.position,
    }

    items = [await _move_one_card(card_id, query, base_url) for card_id in card_ids]
    return MoveCardsResult(success=True, list_id=params.list_id, items=items)


async def _set_one_card_due_date(
    card_id: str,
    query: dict[str, Any],
    base_url: str,
) -> SetCardDueDateItem:
    """Set or clear the due date on a single Trello card."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.put(f"{base_url}/cards/{card_id}", params=query)
    except httpx.HTTPError as exc:
        return SetCardDueDateItem(card_id=card_id, success=False, error=_redact_error(exc))

    if not resp.is_success:
        return SetCardDueDateItem(
            card_id=card_id,
            success=False,
            error=f"Trello API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return SetCardDueDateItem(
        card_id=data.get("id", card_id),
        success=True,
        name=data.get("name", ""),
        due=data.get("due"),
        due_complete=data.get("dueComplete", False),
    )


@tool(
    scopes=SCOPES["trello_set_card_due_dates"],
    api_docs=f"{_API_DOCS}api-group-cards/#api-cards-id-put",
    provider="trello",
)
async def trello_set_card_due_dates(
    params: SetCardDueDatesParams,
    *,
    token: str,
    api_key: str,
    base_url: str = _BASE_URL,
) -> SetCardDueDatesResult:
    """Set or clear the due date on one or more Trello cards.

    ``due_date`` and ``mark_complete`` are applied to every card in the call.
    Per-card outcomes are returned in ``items`` so partial failures surface
    without aborting the whole bulk call.
    """
    card_ids = parse_csv_ids(params.card_ids)
    if not card_ids:
        return SetCardDueDatesResult(success=False, error="No card IDs provided.")

    query: dict[str, Any] = {
        **_auth_params(api_key, token),
        "due": params.due_date or "",
    }
    if params.mark_complete is not None:
        query["dueComplete"] = str(params.mark_complete).lower()

    items = [await _set_one_card_due_date(card_id, query, base_url) for card_id in card_ids]
    return SetCardDueDatesResult(success=True, items=items)
