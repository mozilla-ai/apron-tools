"""Pydantic models for Atlassian Confluence API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreSpacesParams(BaseModel):
    """Parameters for exploring Confluence spaces."""

    max_results: int = 25


class GetPageContentParams(BaseModel):
    """Parameters for retrieving a Confluence page by ID."""

    page_id: str


class CreatePageParams(BaseModel):
    """Parameters for creating a Confluence page."""

    space_id: str
    title: str
    body: str = ""
    parent_id: str | None = None
    status: str = "current"


class UpdatePageParams(BaseModel):
    """Parameters for updating a Confluence page."""

    page_id: str
    title: str
    body: str
    status: str = "current"


class SearchContentParams(BaseModel):
    """Parameters for searching Confluence content via CQL."""

    cql: str
    limit: int = 25


class GetChildPagesParams(BaseModel):
    """Parameters for listing direct child pages of a Confluence page."""

    page_id: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class SpaceSummary(BaseModel):
    """Lightweight Confluence space representation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    key: str
    name: str
    type: str = "global"
    status: str = "current"
    homepage_id: str | None = Field(default=None, alias="homepageId")


class PageVersion(BaseModel):
    """Version metadata for a Confluence page."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    number: int = 1
    message: str = ""
    created_at: str = Field(default="", alias="createdAt")
    author_id: str = Field(default="", alias="authorId")


class PageSummary(BaseModel):
    """Full Confluence page representation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    status: str = "current"
    title: str = "Untitled"
    space_id: str = Field(default="", alias="spaceId")
    parent_id: str | None = Field(default=None, alias="parentId")
    version: PageVersion = PageVersion()
    body_storage: str = ""

    @model_validator(mode="before")
    @classmethod
    def _extract_body(cls, data: Any) -> Any:
        """Extract the storage body value from nested API JSON."""
        if isinstance(data, dict) and "body" in data:
            body = data["body"]
            if isinstance(body, dict):
                storage = body.get("storage")
                if isinstance(storage, dict):
                    data["body_storage"] = storage.get("value", "")
        return data


class ChildPageSummary(BaseModel):
    """Lightweight child page representation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    status: str = "current"
    title: str = "Untitled"
    space_id: str = Field(default="", alias="spaceId")
    child_position: int | None = Field(default=None, alias="childPosition")


class SearchResultSpace(BaseModel):
    """Space information nested inside a search result."""

    model_config = ConfigDict(extra="ignore")

    key: str = ""
    name: str = ""
    type: str = "global"
    status: str = "current"


class SearchResultContent(BaseModel):
    """Content information nested inside a search result."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    type: str = ""
    status: str = ""
    title: str = ""
    space: SearchResultSpace = SearchResultSpace()


class SearchResult(BaseModel):
    """A single search result from the CQL search endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    content: SearchResultContent = SearchResultContent()
    title: str = ""
    excerpt: str = ""
    url: str = ""
    last_modified: str = Field(default="", alias="lastModified")
    entity_type: str = Field(default="", alias="entityType")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreSpacesResult(ToolResult):
    """Result of exploring Confluence spaces."""

    model_config = ConfigDict(extra="ignore")

    spaces: list[SpaceSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the spaces."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.spaces:
            return "No spaces found."
        lines = [f"Found {len(self.spaces)} space(s):"]
        for s in self.spaces:
            lines.append(f"  - {s.name} (key={s.key}, id={s.id}) type={s.type}")
        return "\n".join(lines)


class GetPageContentResult(ToolResult):
    """Result of retrieving a Confluence page."""

    model_config = ConfigDict(extra="ignore")

    page: PageSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the page."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.page:
            return "No page found."
        p = self.page
        return f"Page: {p.title} (id={p.id}, space={p.space_id}, version={p.version.number})\n{p.body_storage}"


class CreatePageResult(ToolResult):
    """Result of creating a Confluence page."""

    model_config = ConfigDict(extra="ignore")

    page: PageSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of page creation."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.page:
            return "Page created (no details returned)."
        return f"Page created: {self.page.title} (id={self.page.id})"


class UpdatePageResult(ToolResult):
    """Result of updating a Confluence page."""

    model_config = ConfigDict(extra="ignore")

    page: PageSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of page update."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.page:
            return "Page updated (no details returned)."
        return f"Page updated: {self.page.title} (id={self.page.id}, version={self.page.version.number})"


class SearchContentResult(ToolResult):
    """Result of searching Confluence content."""

    model_config = ConfigDict(extra="ignore")

    results: list[SearchResult] = []
    total_size: int = 0
    cql_query: str = ""

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
            return "No results found."
        lines = [f"Found {self.total_size} result(s) for CQL: {self.cql_query}"]
        for r in self.results:
            space_key = r.content.space.key if r.content.space.key else "?"
            lines.append(f"  - {r.title} (id={r.content.id}, space={space_key}) type={r.content.type}")
            if r.excerpt:
                lines.append(f"    {r.excerpt}")
        return "\n".join(lines)


class GetChildPagesResult(ToolResult):
    """Result of listing child pages."""

    model_config = ConfigDict(extra="ignore")

    children: list[ChildPageSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of child pages."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.children:
            return "No child pages found."
        lines = [f"Found {len(self.children)} child page(s):"]
        for c in self.children:
            lines.append(f"  - {c.title} (id={c.id}, space={c.space_id})")
        return "\n".join(lines)
