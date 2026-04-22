"""Pydantic models for HubSpot CRM API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Shared record/search types
# ---------------------------------------------------------------------------


class CrmRecord(BaseModel):
    """A single CRM record as returned by the HubSpot v3 objects API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    archived: bool = False


class Association(BaseModel):
    """Association payload used when creating engagement records.

    Maps to HubSpot's ``associations`` array on POST /crm/v3/objects/{type}.
    The ``types`` list describes the association category and typeId; see
    https://developers.hubspot.com/docs/api/crm/associations for IDs.
    """

    to: dict[str, Any]
    types: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


class SearchContactsParams(BaseModel):
    """Parameters for searching HubSpot contacts by text query."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["firstname", "lastname", "email"],
    )


class CreateContactParams(BaseModel):
    """Parameters for creating a HubSpot contact."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class UpdateContactParams(BaseModel):
    """Parameters for updating a HubSpot contact."""

    record_id: str
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


class SearchCompaniesParams(BaseModel):
    """Parameters for searching HubSpot companies by text query."""

    query: str
    limit: int = 10
    properties: list[str] = Field(default_factory=lambda: ["name", "domain"])


class CreateCompanyParams(BaseModel):
    """Parameters for creating a HubSpot company."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class UpdateCompanyParams(BaseModel):
    """Parameters for updating a HubSpot company."""

    record_id: str
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


class SearchDealsParams(BaseModel):
    """Parameters for searching HubSpot deals by text query."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["dealname", "dealstage", "amount"],
    )


class CreateDealParams(BaseModel):
    """Parameters for creating a HubSpot deal."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class UpdateDealParams(BaseModel):
    """Parameters for updating a HubSpot deal."""

    record_id: str
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class SearchNotesParams(BaseModel):
    """Parameters for searching HubSpot note engagements."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["hs_note_body", "hs_timestamp"],
    )


class CreateNoteParams(BaseModel):
    """Parameters for creating a HubSpot note engagement."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class UpdateNoteParams(BaseModel):
    """Parameters for updating a HubSpot note engagement."""

    record_id: str
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class SearchTasksParams(BaseModel):
    """Parameters for searching HubSpot task engagements."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["hs_task_subject", "hs_task_status"],
    )


class CreateTaskParams(BaseModel):
    """Parameters for creating a HubSpot task engagement."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class UpdateTaskParams(BaseModel):
    """Parameters for updating a HubSpot task engagement."""

    record_id: str
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Calls / Emails / Meetings / Activity / Pipelines / Owners
# ---------------------------------------------------------------------------


class SearchCallsParams(BaseModel):
    """Parameters for searching HubSpot call engagements."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["hs_call_title", "hs_timestamp"],
    )


class SearchEmailsParams(BaseModel):
    """Parameters for searching HubSpot email engagements."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["hs_email_subject", "hs_timestamp"],
    )


class SearchMeetingsParams(BaseModel):
    """Parameters for searching HubSpot meeting engagements."""

    query: str
    limit: int = 10
    properties: list[str] = Field(
        default_factory=lambda: ["hs_meeting_title", "hs_timestamp"],
    )


class LogActivityParams(BaseModel):
    """Parameters for logging an activity engagement (call, email, or meeting)."""

    activity_type: str
    """One of ``calls``, ``emails``, or ``meetings``."""

    properties: dict[str, Any]
    associations: list[Association] | None = None


class ListPipelinesParams(BaseModel):
    """Parameters for listing CRM pipelines for an object type."""

    object_type: str = "deals"


class ListOwnersParams(BaseModel):
    """Parameters for listing HubSpot owners (users)."""

    query: str = ""


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class SearchResult(ToolResult):
    """Generic result for HubSpot CRM search tools."""

    model_config = ConfigDict(extra="ignore")

    results: list[CrmRecord] = Field(default_factory=list)
    total: int | None = None
    has_more: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of search results."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.results:
            return "No records found."
        lines = [f"Found {len(self.results)} record(s):"]
        for record in self.results:
            props = ", ".join(f"{k}={v}" for k, v in record.properties.items() if v not in (None, ""))
            suffix = f" — {props}" if props else ""
            lines.append(f"  - {record.id}{suffix}")
        if self.has_more:
            lines.append("(more records available)")
        return "\n".join(lines)


class CreateResult(ToolResult):
    """Result of creating a CRM record."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the created record."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Created record: {self.id}"


class UpdateResult(ToolResult):
    """Result of updating a CRM record."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Updated record: {self.id}" if self.id else "Record updated successfully."


class PipelineStage(BaseModel):
    """A single stage within a CRM pipeline."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str | None = None
    display_order: int | None = Field(default=None, alias="displayOrder")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    """A HubSpot CRM pipeline and its ordered stages."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    label: str | None = None
    display_order: int | None = Field(default=None, alias="displayOrder")
    stages: list[PipelineStage] = Field(default_factory=list)


class ListPipelinesResult(ToolResult):
    """Result of listing CRM pipelines."""

    model_config = ConfigDict(extra="ignore")

    object_type: str = ""
    pipelines: list[Pipeline] = Field(default_factory=list)

    def __str__(self) -> str:
        """Return an LLM-readable summary of pipelines and stages."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.pipelines)} {self.object_type} pipeline(s):"]
        for pipeline in self.pipelines:
            lines.append(f"- {pipeline.label or pipeline.id} (ID: {pipeline.id})")
            for stage in pipeline.stages:
                lines.append(f"    * {stage.label or stage.id} (ID: {stage.id})")
        return "\n".join(lines)


class OwnerTeam(BaseModel):
    """A team membership entry on a HubSpot owner."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    name: str | None = None


class Owner(BaseModel):
    """A HubSpot owner (user)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    user_id: int | None = Field(default=None, alias="userId")
    teams: list[OwnerTeam] = Field(default_factory=list)
    archived: bool = False


class ListOwnersResult(ToolResult):
    """Result of listing HubSpot owners."""

    model_config = ConfigDict(extra="ignore")

    owners: list[Owner] = Field(default_factory=list)

    def __str__(self) -> str:
        """Return an LLM-readable summary of owners."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.owners:
            return "No owners found."
        lines = [f"Found {len(self.owners)} owner(s):"]
        for owner in self.owners:
            name = " ".join(filter(None, [owner.first_name, owner.last_name])).strip()
            display = name or owner.email or owner.id
            lines.append(f"  - {display} (ID: {owner.id})")
        return "\n".join(lines)
