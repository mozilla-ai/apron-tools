"""Pydantic models for Atlassian Jira API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreProjectsParams(BaseModel):
    """Parameters for exploring Jira projects."""

    max_results: int = 50


class ExploreIssuesParams(BaseModel):
    """Parameters for exploring issues in a Jira project."""

    project_key: str
    updated_after: str | None = None
    max_results: int = 50


class CreateIssueParams(BaseModel):
    """Parameters for creating a Jira issue."""

    project_key: str
    summary: str
    issue_type: str = "Task"
    description: str = ""
    priority: str = "Medium"


class EditIssueParams(BaseModel):
    """Parameters for editing a Jira issue."""

    issue_key: str
    summary: str | None = None
    description: str | None = None
    priority: str | None = None


class AssignIssueParams(BaseModel):
    """Parameters for assigning a Jira issue."""

    issue_key: str
    assign_to_me: bool = True


class AddCommentParams(BaseModel):
    """Parameters for adding a comment to a Jira issue."""

    issue_key: str
    comment: str


class ListVersionsParams(BaseModel):
    """Parameters for listing versions in a Jira project."""

    project_key: str
    status: str = ""


class ListBoardsParams(BaseModel):
    """Parameters for listing Jira boards."""

    project_key: str = ""


class ListSprintsParams(BaseModel):
    """Parameters for listing sprints on a Jira board."""

    board_id: int
    state: str = ""


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class ProjectLead(BaseModel):
    """A Jira user representing a project lead."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="Unknown", alias="displayName")
    account_id: str = Field(default="", alias="accountId")


class ProjectSummary(BaseModel):
    """Lightweight project representation returned by search endpoints."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    key: str
    name: str
    project_type_key: str = Field(default="software", alias="projectTypeKey")
    lead: ProjectLead | None = None


class IssuePriority(BaseModel):
    """Issue priority."""

    model_config = ConfigDict(extra="ignore")

    name: str = "None"


class IssueStatus(BaseModel):
    """Issue status."""

    model_config = ConfigDict(extra="ignore")

    name: str = "Unknown"


class IssueType(BaseModel):
    """Issue type."""

    model_config = ConfigDict(extra="ignore")

    name: str = "Unknown"


class IssueAssignee(BaseModel):
    """Issue assignee."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="Unassigned", alias="displayName")
    account_id: str = Field(default="", alias="accountId")


class IssueReporter(BaseModel):
    """Issue reporter."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="Unknown", alias="displayName")
    account_id: str = Field(default="", alias="accountId")


class IssueFields(BaseModel):
    """Fields on a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    summary: str = "Untitled"
    description: Any = None
    status: IssueStatus = IssueStatus()
    priority: IssuePriority = IssuePriority()
    issuetype: IssueType = IssueType()
    assignee: IssueAssignee | None = None
    reporter: IssueReporter | None = None
    created: str = ""
    updated: str = ""


class IssueSummary(BaseModel):
    """An issue as returned by the search endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    key: str = ""
    fields: IssueFields = IssueFields()


class CommentAuthor(BaseModel):
    """Author of a comment."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="Unknown", alias="displayName")
    account_id: str = Field(default="", alias="accountId")


class Comment(BaseModel):
    """A Jira issue comment."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    author: CommentAuthor = CommentAuthor()
    created: str = ""
    body: Any = None


class VersionSummary(BaseModel):
    """A Jira project version."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    released: bool = False
    overdue: bool = False
    start_date: str | None = Field(default=None, alias="startDate")
    release_date: str | None = Field(default=None, alias="releaseDate")


class BoardSummary(BaseModel):
    """A Jira board."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str = "Untitled"
    type: str = "unknown"


class SprintSummary(BaseModel):
    """A Jira sprint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int
    name: str = "Untitled"
    state: str = "unknown"
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    complete_date: str | None = Field(default=None, alias="completeDate")
    goal: str | None = None


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreProjectsResult(ToolResult):
    """Result of exploring Jira projects."""

    model_config = ConfigDict(extra="ignore")

    projects: list[ProjectSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the projects."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.projects)} project(s):"]
        for p in self.projects:
            lead = p.lead.display_name if p.lead else "Unknown"
            lines.append(f"  - {p.name} ({p.key}) type={p.project_type_key} lead={lead}")
        return "\n".join(lines)


class ExploreIssuesResult(ToolResult):
    """Result of exploring issues in a Jira project."""

    model_config = ConfigDict(extra="ignore")

    project_key: str = ""
    total: int = 0
    issues: list[IssueSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of project issues."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Project {self.project_key}: {self.total} issue(s)"]
        for issue in self.issues:
            assignee = issue.fields.assignee.display_name if issue.fields.assignee else "Unassigned"
            lines.append(
                f"  - {issue.key}: {issue.fields.summary} "
                f"[{issue.fields.status.name}] priority={issue.fields.priority.name} "
                f"assignee={assignee}"
            )
        return "\n".join(lines)


class CreateIssueResult(ToolResult):
    """Result of creating a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    key: str = ""
    self_url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            if "self" in data:
                data["self_url"] = data["self"]
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created issue."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Issue created: {self.key} (id={self.id})"


class EditIssueResult(ToolResult):
    """Result of editing a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    issue_key: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the edit."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Issue {self.issue_key} updated successfully."


class AssignIssueResult(ToolResult):
    """Result of assigning a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    issue_key: str = ""
    assigned: bool = True

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the assignment."""
        if not self.success:
            return f"Error: {self.error}"
        if self.assigned:
            return f"Issue {self.issue_key} assigned to you."
        return f"Issue {self.issue_key} unassigned."


class AddCommentResult(ToolResult):
    """Result of adding a comment to a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    issue_key: str = ""
    comment_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the comment."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Comment {self.comment_id} added to {self.issue_key}."


class ListVersionsResult(ToolResult):
    """Result of listing versions for a Jira project."""

    model_config = ConfigDict(extra="ignore")

    versions: list[VersionSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of versions."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.versions:
            return "No versions found."
        lines = [f"Found {len(self.versions)} version(s):"]
        for v in self.versions:
            released = "released" if v.released else "unreleased"
            overdue = " (overdue)" if v.overdue else ""
            dates = ""
            if v.start_date:
                dates += f" start={v.start_date}"
            if v.release_date:
                dates += f" release={v.release_date}"
            lines.append(f"  - {v.name} (id={v.id}) [{released}{overdue}]{dates}")
        return "\n".join(lines)


class ListBoardsResult(ToolResult):
    """Result of listing Jira boards."""

    model_config = ConfigDict(extra="ignore")

    boards: list[BoardSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of boards."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.boards:
            return "No boards found."
        lines = [f"Found {len(self.boards)} board(s):"]
        for b in self.boards:
            lines.append(f"  - {b.name} (id={b.id}) type={b.type}")
        return "\n".join(lines)


class ListSprintsResult(ToolResult):
    """Result of listing sprints on a Jira board."""

    model_config = ConfigDict(extra="ignore")

    sprints: list[SprintSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of sprints."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.sprints:
            return "No sprints found."
        lines = [f"Found {len(self.sprints)} sprint(s):"]
        for s in self.sprints:
            dates = ""
            if s.start_date:
                dates += f" start={s.start_date}"
            if s.end_date:
                dates += f" end={s.end_date}"
            if s.complete_date:
                dates += f" completed={s.complete_date}"
            goal = f" goal={s.goal!r}" if s.goal else ""
            lines.append(f"  - {s.name} (id={s.id}) [{s.state}]{dates}{goal}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# atlassian_jira_upload_attachment
# ---------------------------------------------------------------------------


class UploadAttachmentParams(BaseModel):
    """Parameters for uploading an attachment to a Jira issue."""

    issue_key: str
    """The issue key (e.g. "PROJ-123") or issue ID."""

    file: FileInput
    """File to upload — either a URL to fetch or raw bytes."""


class UploadAttachmentResult(ToolResult):
    """Result of uploading an attachment to a Jira issue."""

    model_config = ConfigDict(extra="ignore")

    attachment_id: str = ""
    filename: str = ""
    issue_key: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Attachment '{self.filename}' uploaded to {self.issue_key} (id={self.attachment_id})."
