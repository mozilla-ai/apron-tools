"""Pydantic models for Typeform API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreWorkspaceParams(BaseModel):
    """Parameters for exploring a Typeform workspace."""

    page: int = 1
    page_size: int = 10
    search: str | None = None
    workspace_id: str | None = None


class GetFormDetailsParams(BaseModel):
    """Parameters for retrieving details of a single Typeform form."""

    form_id: str


class CreateFormParams(BaseModel):
    """Parameters for creating a new Typeform form."""

    title: str
    fields: list[dict[str, Any]]
    workspace_id: str | None = None
    language: str = "en"
    welcome_screens: list[dict[str, Any]] | None = None
    thankyou_screens: list[dict[str, Any]] | None = None
    settings: dict[str, Any] | None = None


class UpdateFormParams(BaseModel):
    """Parameters for updating an existing Typeform form.

    Uses a read-modify-write pattern: the existing form is fetched,
    then the provided fields are merged on top before sending the
    full payload via PUT.
    """

    form_id: str
    title: str | None = None
    fields: list[dict[str, Any]] | None = None
    workspace_id: str | None = None
    language: str | None = None
    welcome_screens: list[dict[str, Any]] | None = None
    thankyou_screens: list[dict[str, Any]] | None = None
    settings: dict[str, Any] | None = None


class GetFormResponsesParams(BaseModel):
    """Parameters for retrieving responses to a Typeform form."""

    form_id: str
    page_size: int = 25
    since: str | None = None
    until: str | None = None
    after: str | None = None
    before: str | None = None
    completed: bool | None = None


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class FormSummary(BaseModel):
    """Lightweight form representation returned by list endpoints."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    created_at: str | None = None
    last_updated_at: str | None = None


class FormField(BaseModel):
    """A single field definition within a form."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    ref: str | None = None
    title: str | None = None
    type: str | None = None


class AnswerField(BaseModel):
    """Reference to the field an answer belongs to."""

    model_config = ConfigDict(extra="ignore")

    id: str
    ref: str | None = None
    type: str


class AnswerChoice(BaseModel):
    """A single selected choice."""

    model_config = ConfigDict(extra="ignore")

    label: str | None = None
    id: str | None = None
    ref: str | None = None


class AnswerChoices(BaseModel):
    """Multiple selected choices."""

    model_config = ConfigDict(extra="ignore")

    labels: list[str] | None = None
    ids: list[str] | None = None
    refs: list[str] | None = None


class Answer(BaseModel):
    """A single answer within a response."""

    model_config = ConfigDict(extra="ignore")

    field: AnswerField
    type: str
    text: str | None = None
    number: int | float | None = None
    boolean: bool | None = None
    email: str | None = None
    date: str | None = None
    choice: AnswerChoice | None = None
    choices: AnswerChoices | None = None
    file_url: str | None = None
    url: str | None = None

    @property
    def value(self) -> Any:
        """Return the concrete answer value regardless of type."""
        if self.text is not None:
            return self.text
        if self.number is not None:
            return self.number
        if self.boolean is not None:
            return self.boolean
        if self.email is not None:
            return self.email
        if self.date is not None:
            return self.date
        if self.choice is not None:
            return self.choice.label
        if self.choices is not None:
            return self.choices.labels
        if self.file_url is not None:
            return self.file_url
        if self.url is not None:
            return self.url
        return None


class FormResponse(BaseModel):
    """A single form response (submission)."""

    model_config = ConfigDict(extra="ignore")

    response_id: str | None = None
    token: str | None = None
    landed_at: str | None = None
    submitted_at: str | None = None
    answers: list[Answer] = []
    calculated: dict[str, Any] | None = None
    hidden: dict[str, Any] | None = None
    variables: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreWorkspaceResult(ToolResult):
    """Result of listing Typeform forms."""

    model_config = ConfigDict(extra="ignore")

    total_items: int = 0
    page_count: int = 0
    items: list[FormSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed forms."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {self.total_items} form(s):"]
        for form in self.items:
            lines.append(f"  - {form.title} (id={form.id})")
        return "\n".join(lines)


class GetFormDetailsResult(ToolResult):
    """Result of retrieving a single Typeform form."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    language: str | None = None
    fields: list[dict[str, Any]] = []
    welcome_screens: list[dict[str, Any]] | None = None
    thankyou_screens: list[dict[str, Any]] | None = None
    settings: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    hidden: list[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the form."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Form: {self.title} (id={self.id})"]
        if self.language:
            lines.append(f"Language: {self.language}")
        lines.append(f"Fields: {len(self.fields)}")
        if self.hidden:
            lines.append(f"Hidden fields: {', '.join(self.hidden)}")
        return "\n".join(lines)


class GetFormResponsesResult(ToolResult):
    """Result of retrieving responses to a Typeform form."""

    model_config = ConfigDict(extra="ignore")

    total_items: int = 0
    page_count: int = 0
    items: list[FormResponse] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of form responses."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Received {self.total_items} response(s):"]
        for resp in self.items:
            submitted = resp.submitted_at or "unknown"
            answer_count = len(resp.answers)
            ident = resp.response_id or resp.token or "unknown"
            lines.append(f"  - Response {ident}: {answer_count} answer(s), submitted {submitted}")
        return "\n".join(lines)


def _extract_form_url(links: dict[str, Any]) -> str:
    """Extract the display URL from a Typeform _links object."""
    display = links.get("display")
    if isinstance(display, str):
        return display
    self_link = links.get("self", "")
    if isinstance(self_link, dict):
        return self_link.get("href", "")
    return str(self_link) if self_link else ""


class CreateFormResult(ToolResult):
    """Result of creating a new Typeform form."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            links = data.get("_links", {})
            data["url"] = _extract_form_url(links)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created form."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Form '{self.title}' created.\nID: {self.id}\nURL: {self.url}"


class UpdateFormResult(ToolResult):
    """Result of updating an existing Typeform form."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            links = data.get("_links", {})
            data["url"] = _extract_form_url(links)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated form."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Form '{self.title}' updated.\nID: {self.id}\nURL: {self.url}"
