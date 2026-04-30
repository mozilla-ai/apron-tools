"""Pydantic models for Microsoft SharePoint Graph API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListSitesParams(BaseModel):
    """Parameters for listing SharePoint sites."""

    query: str = ""
    limit: int = 25


class ListDrivesParams(BaseModel):
    """Parameters for listing drives in a SharePoint site."""

    site_id: str


class ExploreDriveParams(BaseModel):
    """Parameters for exploring files and folders in a drive."""

    drive_id: str
    folder_path: str = ""
    limit: int = 25


class CreateFolderParams(BaseModel):
    """Parameters for creating a folder in a drive."""

    drive_id: str
    folder_name: str
    parent_path: str = ""


class SearchParams(BaseModel):
    """Parameters for searching files in a drive."""

    drive_id: str
    query: str
    limit: int = 25


class MoveFilesParams(BaseModel):
    """Parameters for moving one or more files or folders within a drive.

    ``item_ids`` accepts a comma-separated list of item IDs to support bulk
    operations. ``destination_folder_id`` is applied to every item.
    """

    drive_id: str
    item_ids: str
    destination_folder_id: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class SiteCollectionInfo(BaseModel):
    """Site collection metadata from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    hostname: str = ""
    data_location_code: str | None = Field(default=None, alias="dataLocationCode")


class SiteInfo(BaseModel):
    """A SharePoint site from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    web_url: str = Field(default="", alias="webUrl")
    is_personal_site: bool = Field(default=False, alias="isPersonalSite")
    site_collection: SiteCollectionInfo | None = Field(default=None, alias="siteCollection")


class DriveOwnerGroup(BaseModel):
    """Owner group information for a drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="", alias="displayName")


class DriveOwner(BaseModel):
    """Owner information for a drive."""

    model_config = ConfigDict(extra="ignore")

    group: DriveOwnerGroup | None = None


class DriveQuota(BaseModel):
    """Quota information for a drive."""

    model_config = ConfigDict(extra="ignore")

    total: int = 0
    used: int = 0


class DriveInfo(BaseModel):
    """A document library (drive) from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    drive_type: str = Field(default="", alias="driveType")
    web_url: str = Field(default="", alias="webUrl")
    owner: DriveOwner | None = None
    quota: DriveQuota | None = None


class DriveItemUser(BaseModel):
    """User information within a drive item's lastModifiedBy."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="", alias="displayName")


class DriveItemLastModifiedBy(BaseModel):
    """Last-modified-by information for a drive item."""

    model_config = ConfigDict(extra="ignore")

    user: DriveItemUser | None = None


class DriveItemFolder(BaseModel):
    """Folder facet for a drive item."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    child_count: int = Field(default=0, alias="childCount")


class DriveItemFile(BaseModel):
    """File facet for a drive item."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    mime_type: str = Field(default="", alias="mimeType")


class ParentReference(BaseModel):
    """Parent reference for a drive item."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    path: str = ""


class DriveItem(BaseModel):
    """A file or folder within a drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    web_url: str = Field(default="", alias="webUrl")
    size: int = 0
    last_modified_date_time: str | None = Field(default=None, alias="lastModifiedDateTime")
    last_modified_by: DriveItemLastModifiedBy | None = Field(default=None, alias="lastModifiedBy")
    folder: DriveItemFolder | None = None
    file: DriveItemFile | None = None
    parent_reference: ParentReference | None = Field(default=None, alias="parentReference")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListSitesResult(ToolResult):
    """Result of listing SharePoint sites."""

    model_config = ConfigDict(extra="ignore")

    sites: list[SiteInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of SharePoint sites."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.sites:
            return "No sites found."
        lines = [f"Found {len(self.sites)} site(s):"]
        for site in self.sites:
            lines.append(f"  - {site.name} (id={site.id}, url={site.web_url})")
        return "\n".join(lines)


class ListDrivesResult(ToolResult):
    """Result of listing drives in a SharePoint site."""

    model_config = ConfigDict(extra="ignore")

    drives: list[DriveInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of drives."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.drives:
            return "No drives found."
        lines = [f"Found {len(self.drives)} drive(s):"]
        for drive in self.drives:
            lines.append(f"  - {drive.name} (id={drive.id}, type={drive.drive_type})")
        return "\n".join(lines)


class ExploreDriveResult(ToolResult):
    """Result of exploring a drive's contents."""

    model_config = ConfigDict(extra="ignore")

    items: list[DriveItem] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of drive contents."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No items found."
        lines = [f"Found {len(self.items)} item(s):"]
        for item in self.items:
            if item.folder is not None:
                lines.append(f"  - [folder] {item.name} (id={item.id}, children={item.folder.child_count})")
            else:
                mime = item.file.mime_type if item.file else ""
                lines.append(f"  - [file] {item.name} (id={item.id}, mime={mime})")
        return "\n".join(lines)


class CreateFolderResult(ToolResult):
    """Result of creating a folder."""

    model_config = ConfigDict(extra="ignore")

    folder: DriveItem | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of folder creation."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.folder:
            return "Folder created but no details returned."
        return f"Folder '{self.folder.name}' created successfully. ID: {self.folder.id}, URL: {self.folder.web_url}"


class SearchResult(ToolResult):
    """Result of searching files in a drive."""

    model_config = ConfigDict(extra="ignore")

    items: list[DriveItem] = []

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
        if not self.items:
            return "No items found."
        lines = [f"Found {len(self.items)} item(s):"]
        for item in self.items:
            if item.folder is not None:
                lines.append(f"  - [folder] {item.name} (id={item.id})")
            else:
                lines.append(f"  - [file] {item.name} (id={item.id})")
        return "\n".join(lines)


class MoveFileItem(BaseModel):
    """Per-item outcome of a bulk SharePoint move call."""

    model_config = ConfigDict(extra="ignore")

    item_id: str
    success: bool = True
    error: str | None = None
    item: DriveItem | None = None


class MoveFilesResult(ToolResult):
    """Result of moving one or more files or folders."""

    model_config = ConfigDict(extra="ignore")

    destination_folder_id: str = ""
    items: list[MoveFileItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk move."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No items processed."
        lines: list[str] = []
        for entry in self.items:
            if entry.success:
                name = entry.item.name if entry.item else entry.item_id
                lines.append(f"- Moved '{name}' to folder {self.destination_folder_id}.")
            else:
                lines.append(f"- {entry.item_id}: Failed: {entry.error}")
        return "\n".join(lines)
