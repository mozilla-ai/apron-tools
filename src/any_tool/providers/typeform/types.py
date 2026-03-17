"""Pydantic models for Typeform API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListFormsParams(BaseModel):
    """Parameters for listing Typeform forms."""

    page: int = 1
    page_size: int = 10
    search: str | None = None
    workspace_id: str | None = None


class GetFormParams(BaseModel):
    """Parameters for retrieving a single Typeform form."""

    form_id: str


class GetResponsesParams(BaseModel):
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


class ListFormsResult(ToolResult):
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


class GetFormResult(ToolResult):
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


class GetResponsesResult(ToolResult):
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
