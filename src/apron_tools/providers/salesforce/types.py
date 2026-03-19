"""Pydantic models for Salesforce API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreOrgParams(BaseModel):
    """Parameters for exploring a Salesforce org."""


class QueryRecordsParams(BaseModel):
    """Parameters for querying Salesforce records via SOQL."""

    soql: str


class GetRecordParams(BaseModel):
    """Parameters for retrieving a single Salesforce record."""

    object_type: str
    record_id: str


class CreateRecordParams(BaseModel):
    """Parameters for creating a Salesforce record."""

    object_type: str
    fields: dict[str, Any]


class UpdateRecordParams(BaseModel):
    """Parameters for updating a Salesforce record."""

    object_type: str
    record_id: str
    fields: dict[str, Any]


class SearchRecordsParams(BaseModel):
    """Parameters for searching Salesforce records via SOSL."""

    sosl: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class SObjectSummary(BaseModel):
    """Lightweight summary of a Salesforce SObject type."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str
    label: str
    label_plural: str | None = Field(default=None, alias="labelPlural")
    key_prefix: str | None = Field(default=None, alias="keyPrefix")
    queryable: bool = False
    searchable: bool = False
    createable: bool = False
    updateable: bool = False
    deletable: bool = False
    custom: bool = False


class RecordAttributes(BaseModel):
    """Metadata attached to each Salesforce record."""

    model_config = ConfigDict(extra="ignore")

    type: str
    url: str | None = None


class QueryRecord(BaseModel):
    """A single record returned from a SOQL query."""

    model_config = ConfigDict(extra="ignore")

    attributes: RecordAttributes | None = None
    Id: str | None = None  # noqa: N815
    Name: str | None = None  # noqa: N815


class SearchRecord(BaseModel):
    """A single record returned from a SOSL search."""

    model_config = ConfigDict(extra="ignore")

    attributes: RecordAttributes | None = None
    Id: str | None = None  # noqa: N815


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreOrgResult(ToolResult):
    """Result of exploring the Salesforce org's available objects."""

    model_config = ConfigDict(extra="ignore")

    sobjects: list[SObjectSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of available SObjects."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.sobjects)} object(s):"]
        for obj in self.sobjects:
            flags = []
            if obj.queryable:
                flags.append("queryable")
            if obj.searchable:
                flags.append("searchable")
            if obj.createable:
                flags.append("createable")
            if obj.custom:
                flags.append("custom")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"  - {obj.label} [{obj.name}]{suffix}")
        return "\n".join(lines)


class QueryRecordsResult(ToolResult):
    """Result of a SOQL query."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    total_size: int = Field(default=0, alias="totalSize")
    done: bool = True
    records: list[dict[str, Any]] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of query results."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Query returned {self.total_size} record(s) (done={self.done}):"]
        for rec in self.records:
            parts = [f"{k}={v}" for k, v in rec.items() if k != "attributes"]
            lines.append(f"  - {', '.join(parts)}")
        return "\n".join(lines)


class GetRecordResult(ToolResult):
    """Result of retrieving a single Salesforce record."""

    model_config = ConfigDict(extra="ignore")

    record: dict[str, Any] = {}

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the record."""
        if not self.success:
            return f"Error: {self.error}"
        parts = [f"{k}={v}" for k, v in self.record.items() if k != "attributes"]
        return f"Record: {', '.join(parts)}"


class CreateRecordResult(ToolResult):
    """Result of creating a Salesforce record."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    errors: list[Any] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created record."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Created record: {self.id}"


class UpdateRecordResult(ToolResult):
    """Result of updating a Salesforce record."""

    model_config = ConfigDict(extra="ignore")

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
        return "Record updated successfully."


class SearchRecordsResult(ToolResult):
    """Result of a SOSL search."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    search_records: list[dict[str, Any]] = Field(default=[], alias="searchRecords")

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
        lines = [f"Found {len(self.search_records)} record(s):"]
        for rec in self.search_records:
            rec_id = rec.get("Id", "unknown")
            obj_type = rec.get("attributes", {}).get("type", "unknown")
            lines.append(f"  - {obj_type} (Id={rec_id})")
        return "\n".join(lines)
