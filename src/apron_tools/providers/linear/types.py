"""Pydantic models for Linear GraphQL API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class WhoamiParams(BaseModel):
    """Parameters for retrieving the authenticated user."""


class ListTeamsParams(BaseModel):
    """Parameters for listing teams."""


class ListUsersParams(BaseModel):
    """Parameters for listing users."""


class ListIssuesParams(BaseModel):
    """Parameters for listing issues with optional filters."""

    team_id: str | None = None
    assignee_id: str | None = None
    state: str | None = None
    project_id: str | None = None
    limit: int = 50
    created_after: str | None = None
    updated_after: str | None = None


class ReadIssueParams(BaseModel):
    """Parameters for reading a single issue."""

    issue_id: str


class CreateIssueParams(BaseModel):
    """Parameters for creating an issue."""

    title: str
    team_id: str
    description: str | None = None
    project_id: str | None = None
    assignee_id: str | None = None
    priority: int | None = None
    state_id: str | None = None


class UpdateIssueParams(BaseModel):
    """Parameters for updating an issue."""

    issue_id: str
    title: str | None = None
    description: str | None = None
    state_id: str | None = None
    assignee_id: str | None = None
    priority: int | None = None
    project_id: str | None = None


class ListProjectsParams(BaseModel):
    """Parameters for listing projects."""

    team_id: str | None = None


class CreateProjectParams(BaseModel):
    """Parameters for creating a project."""

    name: str
    team_ids: list[str]
    description: str | None = None
    lead_id: str | None = None
    state: str | None = None


class UpdateProjectParams(BaseModel):
    """Parameters for updating a project."""

    project_id: str
    name: str | None = None
    description: str | None = None
    lead_id: str | None = None
    state: str | None = None


class ListCyclesParams(BaseModel):
    """Parameters for listing cycles."""

    team_id: str | None = None


class UploadFileToIssueParams(BaseModel):
    """Parameters for uploading a file and attaching it to a Linear issue."""

    issue_id: str
    file: FileInput
    title: str | None = None


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class LinearUser(BaseModel):
    """A Linear user summary."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    email: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    active: bool | None = None


class LinearTeam(BaseModel):
    """A Linear team summary."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    key: str | None = None
    description: str | None = None


class LinearState(BaseModel):
    """A Linear workflow state."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str | None = None
    name: str
    type: str | None = None


class LinearLabel(BaseModel):
    """A Linear label."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str


class LinearProject(BaseModel):
    """A Linear project summary."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str


class LinearCycle(BaseModel):
    """A Linear cycle summary."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str | None = None


class LinearComment(BaseModel):
    """A Linear issue comment."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    body: str
    user: LinearUser | None = None
    created_at: str | None = Field(default=None, alias="createdAt")


class IssueSummary(BaseModel):
    """An issue as returned by list endpoints."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    identifier: str
    title: str
    description: str | None = None
    priority: int | None = None
    state: LinearState | None = None
    assignee: LinearUser | None = None
    team: LinearTeam | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class IssueDetail(BaseModel):
    """A full issue as returned by read endpoints."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    identifier: str
    title: str
    description: str | None = None
    priority: int | None = None
    priority_label: str | None = Field(default=None, alias="priorityLabel")
    estimate: int | None = None
    state: LinearState | None = None
    assignee: LinearUser | None = None
    team: LinearTeam | None = None
    labels: list[LinearLabel] = []
    project: LinearProject | None = None
    cycle: LinearCycle | None = None
    comments: list[LinearComment] = []
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    url: str | None = None


class MutationIssue(BaseModel):
    """Issue fields returned from create/update mutations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    identifier: str
    title: str
    url: str | None = None


class ProjectDetail(BaseModel):
    """A project as returned by list endpoints."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    description: str | None = None
    state: str | None = None
    progress: float | None = None
    start_date: str | None = Field(default=None, alias="startDate")
    target_date: str | None = Field(default=None, alias="targetDate")
    teams: list[LinearTeam] = []
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class MutationProject(BaseModel):
    """Project fields returned from create/update mutations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    url: str | None = None


class CycleDetail(BaseModel):
    """A cycle as returned by list endpoints."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str | None = None
    number: int | None = None
    starts_at: str | None = Field(default=None, alias="startsAt")
    ends_at: str | None = Field(default=None, alias="endsAt")
    progress: float | None = None
    completed_at: str | None = Field(default=None, alias="completedAt")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class WhoamiResult(ToolResult):
    """Result of retrieving the authenticated user."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    name: str = ""
    email: str = ""
    display_name: str | None = Field(default=None, alias="displayName")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the authenticated user."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Authenticated as {self.name} ({self.email})"]
        if self.display_name and self.display_name != self.name:
            lines.append(f"Display name: {self.display_name}")
        lines.append(f"User ID: {self.id}")
        return "\n".join(lines)


class ListTeamsResult(ToolResult):
    """Result of listing teams."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    teams: list[LinearTeam] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed teams."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.teams)} team(s):"]
        for team in self.teams:
            desc = f" - {team.description}" if team.description else ""
            lines.append(f"  - {team.name} (key={team.key}, id={team.id}){desc}")
        return "\n".join(lines)


class ListUsersResult(ToolResult):
    """Result of listing users."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    users: list[LinearUser] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed users."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.users)} user(s):"]
        for user in self.users:
            active = "active" if user.active else "inactive"
            lines.append(f"  - {user.name} ({user.email}, {active}, id={user.id})")
        return "\n".join(lines)


class ListIssuesResult(ToolResult):
    """Result of listing issues."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    issues: list[IssueSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed issues."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.issues)} issue(s):"]
        for issue in self.issues:
            state_name = issue.state.name if issue.state else "Unknown"
            assignee_name = issue.assignee.name if issue.assignee else "Unassigned"
            lines.append(f"  - [{issue.identifier}] {issue.title} (state={state_name}, assignee={assignee_name})")
        return "\n".join(lines)


class ReadIssueResult(ToolResult):
    """Result of reading a single issue."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    issue: IssueDetail | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the issue."""
        if not self.success:
            return f"Error: {self.error}"
        if self.issue is None:
            return "Issue not found."
        i = self.issue
        state_name = i.state.name if i.state else "Unknown"
        assignee_name = i.assignee.name if i.assignee else "Unassigned"
        lines = [
            f"[{i.identifier}] {i.title}",
            f"State: {state_name} | Priority: {i.priority_label or 'None'}",
            f"Assignee: {assignee_name}",
        ]
        if i.labels:
            label_names = ", ".join(lb.name for lb in i.labels)
            lines.append(f"Labels: {label_names}")
        if i.project:
            lines.append(f"Project: {i.project.name}")
        if i.cycle:
            lines.append(f"Cycle: {i.cycle.name}")
        if i.description:
            lines.append(f"Description: {i.description}")
        if i.url:
            lines.append(f"URL: {i.url}")
        return "\n".join(lines)


class CreateIssueResult(ToolResult):
    """Result of creating an issue."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    issue: MutationIssue | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Derive success from the mutation response."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created issue."""
        if not self.success:
            return f"Error: {self.error}"
        if self.issue is None:
            return "Issue created but no details returned."
        return f"Created [{self.issue.identifier}] {self.issue.title} (id={self.issue.id}, url={self.issue.url})"


class UpdateIssueResult(ToolResult):
    """Result of updating an issue."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    issue: MutationIssue | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Derive success from the mutation response."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated issue."""
        if not self.success:
            return f"Error: {self.error}"
        if self.issue is None:
            return "Issue updated but no details returned."
        return f"Updated [{self.issue.identifier}] {self.issue.title}"


class ListProjectsResult(ToolResult):
    """Result of listing projects."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    projects: list[ProjectDetail] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed projects."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.projects)} project(s):"]
        for project in self.projects:
            team_names = ", ".join(t.name for t in project.teams) if project.teams else "None"
            lines.append(f"  - {project.name} (state={project.state}, teams={team_names}, id={project.id})")
        return "\n".join(lines)


class CreateProjectResult(ToolResult):
    """Result of creating a project."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    project: MutationProject | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Derive success from the mutation response."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created project."""
        if not self.success:
            return f"Error: {self.error}"
        if self.project is None:
            return "Project created but no details returned."
        return f"Created project {self.project.name} (id={self.project.id}, url={self.project.url})"


class UpdateProjectResult(ToolResult):
    """Result of updating a project."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    project: MutationProject | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Derive success from the mutation response."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated project."""
        if not self.success:
            return f"Error: {self.error}"
        if self.project is None:
            return "Project updated but no details returned."
        return f"Updated project {self.project.name}"


class ListCyclesResult(ToolResult):
    """Result of listing cycles."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    cycles: list[CycleDetail] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when constructing from API data."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed cycles."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.cycles)} cycle(s):"]
        for cycle in self.cycles:
            display = cycle.name or f"Cycle {cycle.number}"
            progress = f"{round(cycle.progress * 100)}%" if cycle.progress is not None else "N/A"
            lines.append(f"  - {display} (progress={progress}, id={cycle.id})")
        return "\n".join(lines)


class UploadFileToIssueResult(ToolResult):
    """Result of uploading a file and attaching it to a Linear issue."""

    attachment_id: str | None = None
    asset_url: str | None = None
    filename: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the uploaded file."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Uploaded '{self.filename}' to issue."]
        if self.attachment_id:
            lines.append(f"Attachment ID: {self.attachment_id}")
        if self.asset_url:
            lines.append(f"Asset URL: {self.asset_url}")
        return "\n".join(lines)
