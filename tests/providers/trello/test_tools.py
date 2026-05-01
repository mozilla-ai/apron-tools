"""Tests for Trello tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.trello.tools import (
    trello_create_card,
    trello_get_card,
    trello_list_boards,
    trello_list_cards,
    trello_list_lists,
    trello_move_cards,
    trello_set_card_due_dates,
)
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
    MoveCardsParams,
    MoveCardsResult,
    SetCardDueDatesParams,
    SetCardDueDatesResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "trello-token-abc123"
_API_KEY = "trello-api-key-001"  # pragma: allowlist secret


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_boards
# ---------------------------------------------------------------------------


class TestListBoards:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_boards.json"))

        result = await trello_list_boards(ListBoardsParams(), token=_TOKEN, api_key=_API_KEY)

        assert isinstance(result, ListBoardsResult)
        assert result.success is True
        assert len(result.boards) == 2
        assert result.boards[0].name == "Project Alpha"
        assert result.boards[0].permission_level == "org"
        assert result.boards[1].closed is True
        assert "Project Alpha" in str(result)

    async def test_auth_params_in_url(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[])

        await trello_list_boards(ListBoardsParams(), token=_TOKEN, api_key=_API_KEY)

        request = httpx_mock.get_request()
        assert request is not None
        assert f"key={_API_KEY}" in str(request.url)
        assert f"token={_TOKEN}" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await trello_list_boards(ListBoardsParams(), token=_TOKEN, api_key=_API_KEY)

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = trello_list_boards._tool_definition
        assert defn.name == "trello_list_boards"
        assert defn.provider == "trello"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# list_lists
# ---------------------------------------------------------------------------


class TestListLists:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_lists.json"))

        result = await trello_list_lists(ListListsParams(board_id="board-001"), token=_TOKEN, api_key=_API_KEY)

        assert isinstance(result, ListListsResult)
        assert result.success is True
        assert len(result.lists) == 3
        assert result.lists[0].name == "To Do"
        assert result.lists[2].name == "Done"

    async def test_board_id_in_url(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[])

        await trello_list_lists(ListListsParams(board_id="board-xyz"), token=_TOKEN, api_key=_API_KEY)

        request = httpx_mock.get_request()
        assert request is not None
        assert "/boards/board-xyz/lists" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await trello_list_lists(ListListsParams(board_id="missing"), token=_TOKEN, api_key=_API_KEY)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = trello_list_lists._tool_definition
        assert defn.name == "trello_list_lists"
        assert defn.provider == "trello"


# ---------------------------------------------------------------------------
# list_cards
# ---------------------------------------------------------------------------


class TestListCards:
    async def test_success_by_list(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_cards.json"))

        result = await trello_list_cards(ListCardsParams(list_id="list-001"), token=_TOKEN, api_key=_API_KEY)

        assert isinstance(result, ListCardsResult)
        assert result.success is True
        assert len(result.cards) == 2
        assert result.cards[0].name == "Implement login page"
        assert result.cards[0].due == "2026-04-01T12:00:00.000Z"

    async def test_uses_list_endpoint(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[])

        await trello_list_cards(ListCardsParams(list_id="list-001"), token=_TOKEN, api_key=_API_KEY)

        request = httpx_mock.get_request()
        assert request is not None
        assert "/lists/list-001/cards" in str(request.url)

    async def test_uses_board_endpoint(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[])

        await trello_list_cards(ListCardsParams(board_id="board-001"), token=_TOKEN, api_key=_API_KEY)

        request = httpx_mock.get_request()
        assert request is not None
        assert "/boards/board-001/cards" in str(request.url)

    async def test_requires_board_or_list(self, httpx_mock: HTTPXMock) -> None:
        result = await trello_list_cards(ListCardsParams(), token=_TOKEN, api_key=_API_KEY)

        assert result.success is False
        assert "board_id or list_id" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = trello_list_cards._tool_definition
        assert defn.name == "trello_list_cards"
        assert defn.provider == "trello"


# ---------------------------------------------------------------------------
# get_card
# ---------------------------------------------------------------------------


class TestGetCard:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_card.json"))

        result = await trello_get_card(GetCardParams(card_id="card-001"), token=_TOKEN, api_key=_API_KEY)

        assert isinstance(result, GetCardResult)
        assert result.success is True
        assert result.card is not None
        assert result.card.name == "Implement login page"
        assert result.card.board_name == "Project Alpha"
        assert result.card.list_name == "To Do"
        assert result.card.desc == "Build the authentication UI with email and password fields."
        assert "Project Alpha" in str(result)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await trello_get_card(GetCardParams(card_id="missing"), token=_TOKEN, api_key=_API_KEY)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = trello_get_card._tool_definition
        assert defn.name == "trello_get_card"
        assert defn.provider == "trello"


# ---------------------------------------------------------------------------
# create_card
# ---------------------------------------------------------------------------


class TestCreateCard:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_card.json"))

        params = CreateCardParams(list_id="list-001", name="New task", description="Task description")
        result = await trello_create_card(params, token=_TOKEN, api_key=_API_KEY)

        assert isinstance(result, CreateCardResult)
        assert result.success is True
        assert result.id == "card-new-001"
        assert result.name == "New task"
        assert result.short_url == "https://trello.com/c/xyz001"
        assert "New task" in str(result)

    async def test_sends_correct_params(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_card.json"))

        params = CreateCardParams(list_id="list-001", name="Test", due_date="2026-04-15T17:00:00Z")
        await trello_create_card(params, token=_TOKEN, api_key=_API_KEY)

        request = httpx_mock.get_request()
        assert request is not None
        assert "idList=list-001" in str(request.url)
        assert "due=" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await trello_create_card(
            CreateCardParams(list_id="list-001", name="Fail"), token=_TOKEN, api_key=_API_KEY
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = trello_create_card._tool_definition
        assert defn.name == "trello_create_card"
        assert defn.provider == "trello"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# move_card
# ---------------------------------------------------------------------------


class TestMoveCards:
    async def test_single_card(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_card.json"))

        result = await trello_move_cards(
            MoveCardsParams(card_ids="card-001", list_id="list-002"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert isinstance(result, MoveCardsResult)
        assert result.success is True
        assert result.list_id == "list-002"
        assert len(result.items) == 1
        assert result.items[0].name == "Implement login page"
        assert result.items[0].success is True

    async def test_multiple_cards(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_card.json"))
        httpx_mock.add_response(json=_load_json("move_card.json"))

        result = await trello_move_cards(
            MoveCardsParams(card_ids="card-001, card-002", list_id="list-002"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is True
        assert len(result.items) == 2
        assert all(item.success for item in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_card.json"))
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await trello_move_cards(
            MoveCardsParams(card_ids="card-001,bad-card", list_id="list-002"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "403" in result.items[1].error

    async def test_empty_card_ids(self) -> None:
        result = await trello_move_cards(
            MoveCardsParams(card_ids=" , ", list_id="list-002"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is False
        assert result.error == "No card IDs provided."

    async def test_has_tool_definition(self) -> None:
        defn = trello_move_cards._tool_definition
        assert defn.name == "trello_move_cards"
        assert defn.provider == "trello"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# set_card_due_dates
# ---------------------------------------------------------------------------


class TestSetCardDueDates:
    async def test_set_single_due_date(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("set_due_date.json"))

        result = await trello_set_card_due_dates(
            SetCardDueDatesParams(card_ids="card-001", due_date="2026-04-15T17:00:00.000Z"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert isinstance(result, SetCardDueDatesResult)
        assert result.success is True
        assert result.items[0].due == "2026-04-15T17:00:00.000Z"
        assert "Due date set" in str(result)

    async def test_multiple_cards(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("set_due_date.json"))
        httpx_mock.add_response(json=_load_json("set_due_date.json"))

        result = await trello_set_card_due_dates(
            SetCardDueDatesParams(card_ids="card-001,card-002", due_date="2026-04-15T17:00:00.000Z"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is True
        assert len(result.items) == 2
        assert all(item.success for item in result.items)

    async def test_clear_due_date(self, httpx_mock: HTTPXMock) -> None:
        resp = _load_json("set_due_date.json")
        resp["due"] = None
        httpx_mock.add_response(json=resp)

        result = await trello_set_card_due_dates(
            SetCardDueDatesParams(card_ids="card-001", due_date=None),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is True
        assert "cleared" in str(result).lower()

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("set_due_date.json"))
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await trello_set_card_due_dates(
            SetCardDueDatesParams(card_ids="card-001,bad", due_date="2026-04-15T17:00:00.000Z"),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "400" in result.items[1].error

    async def test_empty_card_ids(self) -> None:
        result = await trello_set_card_due_dates(
            SetCardDueDatesParams(card_ids=" , ", due_date=None),
            token=_TOKEN,
            api_key=_API_KEY,
        )

        assert result.success is False
        assert result.error == "No card IDs provided."

    async def test_has_tool_definition(self) -> None:
        defn = trello_set_card_due_dates._tool_definition
        assert defn.name == "trello_set_card_due_dates"
        assert defn.provider == "trello"
        assert defn.scopes == ["write"]
