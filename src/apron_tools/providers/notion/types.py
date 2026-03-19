"""Pydantic models for Notion API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreTeamspaceParams(BaseModel):
    """Parameters for exploring a Notion teamspace."""

    page_size: int = 100


class CreatePageParams(BaseModel):
    """Parameters for creating a new Notion page."""

    parent_page_id: str
    title: str
    content: str = ""


class UpdatePageParams(BaseModel):
    """Parameters for appending content blocks to a Notion page."""

    page_id: str
    content: str


class ReadPageParams(BaseModel):
    """Parameters for reading a Notion page."""

    page_id: str


class GetDatabaseSchemaParams(BaseModel):
    """Parameters for retrieving a Notion database schema."""

    database_id: str


class QueryDatabaseParams(BaseModel):
    """Parameters for querying a Notion database via the data sources endpoint."""

    data_source_id: str
    filter: dict[str, Any] | None = None
    sorts: list[dict[str, Any]] | None = None
    page_size: int = 100


class GetDatabaseEntryParams(BaseModel):
    """Parameters for retrieving a single database entry."""

    page_id: str


class CreateOrUpdateDatabaseEntryParams(BaseModel):
    """Parameters for creating or updating a database entry."""

    database_id: str | None = None
    page_id: str | None = None
    properties: dict[str, Any] = {}


class CreateDatabaseParams(BaseModel):
    """Parameters for creating a new Notion database."""

    parent_page_id: str
    title: str
    properties: dict[str, Any] | None = None
    description: str = ""


class UpdateDatabaseSchemaParams(BaseModel):
    """Parameters for updating a Notion database schema."""

    database_id: str
    title: str | None = None
    properties: dict[str, Any] | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class RichTextItem(BaseModel):
    """A single rich text segment from the Notion API."""

    model_config = ConfigDict(extra="ignore")

    type: str = "text"
    plain_text: str = ""


class PageParent(BaseModel):
    """Parent reference for a Notion page."""

    model_config = ConfigDict(extra="ignore")

    type: str = ""
    workspace: bool | None = None
    page_id: str | None = None
    database_id: str | None = None


class UserRef(BaseModel):
    """Lightweight user reference."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    object: str = "user"


class PageObject(BaseModel):
    """A Notion page object returned by search, retrieve, or create endpoints."""

    model_config = ConfigDict(extra="ignore")

    object: str = "page"
    id: str = ""
    created_time: str = ""
    last_edited_time: str = ""
    in_trash: bool = False
    url: str = ""
    public_url: str | None = None
    parent: PageParent | None = None
    properties: dict[str, Any] = {}
    icon: dict[str, Any] | None = None
    cover: dict[str, Any] | None = None
    created_by: UserRef | None = None
    last_edited_by: UserRef | None = None

    @property
    def title(self) -> str:
        """Extract the page title from properties."""
        for prop_value in self.properties.values():
            if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                title_list = prop_value.get("title", [])
                if title_list:
                    return title_list[0].get("plain_text", "Untitled")
        return "Untitled"


class BlockObject(BaseModel):
    """A Notion block object returned by the block children endpoint."""

    model_config = ConfigDict(extra="ignore")

    object: str = "block"
    id: str = ""
    type: str = ""
    has_children: bool = False
    paragraph: dict[str, Any] | None = None
    heading_1: dict[str, Any] | None = None
    heading_2: dict[str, Any] | None = None
    heading_3: dict[str, Any] | None = None
    bulleted_list_item: dict[str, Any] | None = None
    numbered_list_item: dict[str, Any] | None = None
    code: dict[str, Any] | None = None
    quote: dict[str, Any] | None = None
    to_do: dict[str, Any] | None = None
    callout: dict[str, Any] | None = None
    divider: dict[str, Any] | None = None
    table: dict[str, Any] | None = None

    @property
    def text_content(self) -> str:
        """Extract plain text from the block based on its type."""
        if self.type == "divider":
            return "---"
        type_data = getattr(self, self.type, None)
        if type_data is None:
            return ""
        rich_text = type_data.get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in rich_text)


class DatabaseProperty(BaseModel):
    """A single property definition in a Notion database schema."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    type: str = ""
    name: str | None = None
    select: dict[str, Any] | None = None
    multi_select: dict[str, Any] | None = None
    relation: dict[str, Any] | None = None


class DataSource(BaseModel):
    """A data source reference attached to a database."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    type: str = "default"


class DatabaseObject(BaseModel):
    """A Notion database object."""

    model_config = ConfigDict(extra="ignore")

    object: str = "database"
    id: str = ""
    title: list[dict[str, Any]] = []
    description: list[dict[str, Any]] = []
    parent: PageParent | None = None
    is_inline: bool = False
    in_trash: bool = False
    created_time: str = ""
    last_edited_time: str = ""
    url: str = ""
    public_url: str | None = None
    properties: dict[str, Any] = {}
    icon: dict[str, Any] | None = None
    cover: dict[str, Any] | None = None
    data_sources: list[DataSource] = []

    @property
    def title_text(self) -> str:
        """Extract plain text from the title rich text array."""
        if self.title:
            return self.title[0].get("plain_text", "Untitled")
        return "Untitled"


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreTeamspaceResult(ToolResult):
    """Result of exploring a Notion teamspace."""

    model_config = ConfigDict(extra="ignore")

    pages: list[PageObject] = []
    databases: list[DatabaseObject] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the teamspace."""
        if not self.success:
            return f"Error: {self.error}"
        lines = ["# Notion Workspace"]
        if self.pages:
            lines.append("## Pages")
            for page in self.pages:
                lines.append(f"  - {page.title} (id={page.id})")
        if self.databases:
            lines.append("## Databases")
            for db in self.databases:
                lines.append(f"  - {db.title_text} (id={db.id})")
        return "\n".join(lines)


class CreatePageResult(ToolResult):
    """Result of creating a Notion page."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    url: str = ""
    created_time: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created page."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Page created (id={self.id}, url={self.url})"


class UpdatePageResult(ToolResult):
    """Result of appending content blocks to a Notion page."""

    model_config = ConfigDict(extra="ignore")

    page_id: str = ""
    blocks_appended: int = 0

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Page {self.page_id} updated ({self.blocks_appended} block(s) appended)"


class ReadPageResult(ToolResult):
    """Result of reading a Notion page."""

    model_config = ConfigDict(extra="ignore")

    page: PageObject | None = None
    blocks: list[BlockObject] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the page content."""
        if not self.success:
            return f"Error: {self.error}"
        if self.page is None:
            return "No page data."
        lines = [f"# {self.page.title}", ""]
        for block in self.blocks:
            text = block.text_content
            if text:
                lines.append(text)
        return "\n".join(lines)


class GetDatabaseSchemaResult(ToolResult):
    """Result of retrieving a Notion database schema."""

    model_config = ConfigDict(extra="ignore")

    database: DatabaseObject | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the database schema."""
        if not self.success:
            return f"Error: {self.error}"
        if self.database is None:
            return "No database data."
        lines = [
            f"# Database: {self.database.title_text}",
            f"Database ID: {self.database.id}",
            "",
            "## Properties:",
        ]
        for prop_name, prop_config in self.database.properties.items():
            prop_type = prop_config.get("type", "unknown") if isinstance(prop_config, dict) else "unknown"
            lines.append(f"  - {prop_name} (type: {prop_type})")
        return "\n".join(lines)


class QueryDatabaseResult(ToolResult):
    """Result of querying a Notion database."""

    model_config = ConfigDict(extra="ignore")

    results: list[PageObject] = []
    has_more: bool = False
    next_cursor: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the query results."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.results)} entry/entries:"]
        for page in self.results:
            lines.append(f"  - {page.title} (id={page.id})")
        if self.has_more:
            lines.append(f"More results available (next_cursor={self.next_cursor})")
        return "\n".join(lines)


class GetDatabaseEntryResult(ToolResult):
    """Result of retrieving a single database entry."""

    model_config = ConfigDict(extra="ignore")

    page: PageObject | None = None
    blocks: list[BlockObject] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the database entry."""
        if not self.success:
            return f"Error: {self.error}"
        if self.page is None:
            return "No entry data."
        lines = [f"Entry: {self.page.title} (id={self.page.id})"]
        for prop_name, prop_value in self.page.properties.items():
            if isinstance(prop_value, dict):
                lines.append(f"  - {prop_name}: {prop_value.get('type', 'unknown')}")
        if self.blocks:
            lines.append("Content:")
            for block in self.blocks:
                text = block.text_content
                if text:
                    lines.append(f"  {text}")
        return "\n".join(lines)


class CreateOrUpdateDatabaseEntryResult(ToolResult):
    """Result of creating or updating a database entry."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    url: str = ""
    created_time: str = ""
    last_edited_time: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the database entry."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Database entry saved (id={self.id}, url={self.url})"


class CreateDatabaseResult(ToolResult):
    """Result of creating a Notion database."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    url: str = ""
    title: list[dict[str, Any]] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    @property
    def title_text(self) -> str:
        """Extract plain text from the title."""
        if self.title:
            return self.title[0].get("plain_text", "Untitled")
        return "Untitled"

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created database."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Database created: {self.title_text} (id={self.id}, url={self.url})"


class UpdateDatabaseSchemaResult(ToolResult):
    """Result of updating a Notion database schema."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    url: str = ""
    title: list[dict[str, Any]] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    @property
    def title_text(self) -> str:
        """Extract plain text from the title."""
        if self.title:
            return self.title[0].get("plain_text", "Untitled")
        return "Untitled"

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated database."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Database updated: {self.title_text} (id={self.id}, url={self.url})"


# ---------------------------------------------------------------------------
# notion_embed_external_file
# ---------------------------------------------------------------------------


class EmbedExternalFileParams(BaseModel):
    """Parameters for embedding an external file or image on a Notion page."""

    page_id: str
    url: str
    caption: str = ""
    file_type: str = "auto"


class EmbedExternalFileResult(ToolResult):
    """Result of embedding an external file on a Notion page."""

    model_config = ConfigDict(extra="ignore")

    block_type: str = ""
    file_url: str = ""
    page_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary."""
        if not self.success:
            return f"Error: {self.error}"
        return f"File embedded as {self.block_type} block on page {self.page_id}.\nURL: {self.file_url}"
