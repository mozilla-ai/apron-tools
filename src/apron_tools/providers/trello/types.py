"""Pydantic models for Trello API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListBoardsParams(BaseModel):
    """Parameters for listing boards the authenticated member belongs to."""

    filter: str = "open"
    limit: int = Field(default=20, gt=0, le=1000)


class ListListsParams(BaseModel):
    """Parameters for listing lists on a Trello board."""

    board_id: str


class ListCardsParams(BaseModel):
    """Parameters for listing cards on a board or in a list."""

    board_id: str | None = None
    list_id: str | None = None
    filter: str = "open"
    limit: int = Field(default=50, gt=0, le=1000)


class GetCardParams(BaseModel):
    """Parameters for retrieving a single Trello card."""

    card_id: str


class CreateCardParams(BaseModel):
    """Parameters for creating a new Trello card."""

    list_id: str
    name: str
    description: str = ""
    due_date: str | None = None
    position: str = "bottom"


class MoveCardParams(BaseModel):
    """Parameters for moving a card to a different list."""

    card_id: str
    list_id: str
    position: str = "bottom"


class SetCardDueDateParams(BaseModel):
    """Parameters for setting or clearing a card's due date.

    If ``mark_complete`` is not provided, the existing completion status
    is left unchanged.
    """

    card_id: str
    due_date: str | None = None
    mark_complete: bool | None = None


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TrelloBoard(BaseModel):
    """A Trello board summary."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    closed: bool = False
    url: str = ""
    short_url: str = Field(default="", alias="shortUrl")
    permission_level: str = ""

    @model_validator(mode="before")
    @classmethod
    def _extract_prefs(cls, data: Any) -> Any:
        """Extract permission level from nested prefs object."""
        if isinstance(data, dict) and "prefs" in data:
            prefs = data.get("prefs") or {}
            if isinstance(prefs, dict):
                data["permission_level"] = prefs.get("permissionLevel", "")
        return data


class TrelloList(BaseModel):
    """A Trello list summary."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    closed: bool = False
    pos: float = 0


class TrelloCard(BaseModel):
    """A Trello card summary."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    closed: bool = False
    id_list: str = Field(default="", alias="idList")
    due: str | None = None
    due_complete: bool = Field(default=False, alias="dueComplete")
    short_url: str = Field(default="", alias="shortUrl")


class TrelloCardDetail(BaseModel):
    """A Trello card with full details."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    desc: str = ""
    closed: bool = False
    id_list: str = Field(default="", alias="idList")
    id_board: str = Field(default="", alias="idBoard")
    due: str | None = None
    due_complete: bool = Field(default=False, alias="dueComplete")
    short_url: str = Field(default="", alias="shortUrl")
    url: str = ""
    list_name: str = ""
    board_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _extract_nested(cls, data: Any) -> Any:
        """Extract list and board names from nested objects."""
        if isinstance(data, dict):
            board = data.get("board")
            if isinstance(board, dict):
                data["board_name"] = board.get("name", "")
            lst = data.get("list")
            if isinstance(lst, dict):
                data["list_name"] = lst.get("name", "")
        return data


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListBoardsResult(ToolResult):
    """Result of listing Trello boards."""

    boards: list[TrelloBoard] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the boards."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.boards)} board(s):"]
        for b in self.boards:
            status = "Closed" if b.closed else "Open"
            lines.append(f"  - {b.name} (id={b.id}, {status}, {b.permission_level})")
        return "\n".join(lines)


class ListListsResult(ToolResult):
    """Result of listing Trello lists on a board."""

    lists: list[TrelloList] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the lists."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.lists)} list(s):"]
        for lst in self.lists:
            status = "Closed" if lst.closed else "Open"
            lines.append(f"  - {lst.name} (id={lst.id}, {status})")
        return "\n".join(lines)


class ListCardsResult(ToolResult):
    """Result of listing Trello cards."""

    cards: list[TrelloCard] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the cards."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.cards)} card(s):"]
        for c in self.cards:
            due_info = f", due={c.due}" if c.due else ""
            lines.append(f"  - {c.name} (id={c.id}{due_info})")
        return "\n".join(lines)


class GetCardResult(ToolResult):
    """Result of retrieving a single Trello card."""

    card: TrelloCardDetail | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the card."""
        if not self.success:
            return f"Error: {self.error}"
        if self.card is None:
            return "Card not found."
        c = self.card
        status = "Closed" if c.closed else "Open"
        lines = [
            f"{c.name}",
            f"ID: {c.id} | Status: {status}",
            f"Board: {c.board_name} | List: {c.list_name}",
        ]
        if c.due:
            complete = "complete" if c.due_complete else "incomplete"
            lines.append(f"Due: {c.due} ({complete})")
        if c.desc:
            lines.append(f"Description: {c.desc}")
        if c.short_url:
            lines.append(f"URL: {c.short_url}")
        return "\n".join(lines)


class CreateCardResult(ToolResult):
    """Result of creating a new Trello card."""

    id: str = ""
    name: str = ""
    short_url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            data["short_url"] = data.get("shortUrl", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created card."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Card '{self.name}' created.\nID: {self.id}\nURL: {self.short_url}"


class MoveCardResult(ToolResult):
    """Result of moving a Trello card."""

    id: str = ""
    name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the moved card."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Card '{self.name}' moved.\nID: {self.id}"


class SetCardDueDateResult(ToolResult):
    """Result of setting or clearing a card's due date."""

    id: str = ""
    name: str = ""
    due: str | None = None
    due_complete: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            data["due_complete"] = data.get("dueComplete", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the due date change."""
        if not self.success:
            return f"Error: {self.error}"
        if self.due:
            complete = "complete" if self.due_complete else "incomplete"
            return f"Due date set to {self.due} ({complete}) for card '{self.name}'."
        return f"Due date cleared for card '{self.name}'."
