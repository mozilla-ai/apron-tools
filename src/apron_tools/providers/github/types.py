"""Pydantic models for GitHub API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListRepositoriesParams(BaseModel):
    """Parameters for listing repositories for the authenticated user."""

    visibility: str = "all"
    sort: str = "updated"
    limit: int = 30


class GetRepositoryParams(BaseModel):
    """Parameters for retrieving a single repository."""

    owner: str
    repo: str


class ListIssuesParams(BaseModel):
    """Parameters for listing issues in a repository."""

    owner: str
    repo: str
    state: str = "open"
    labels: str = ""
    milestone: str | None = None
    limit: int = 30
    since: str | None = None


class GetIssueParams(BaseModel):
    """Parameters for retrieving a single issue."""

    owner: str
    repo: str
    issue_number: int


class CreateIssueParams(BaseModel):
    """Parameters for creating an issue."""

    owner: str
    repo: str
    title: str
    body: str = ""
    labels: str = ""
    assignees: str = ""


class AddIssueCommentsParams(BaseModel):
    """Parameters for adding the same comment to one or more issues.

    ``issue_numbers`` accepts a comma-separated list to support bulk operations.
    """

    owner: str
    repo: str
    issue_numbers: str
    body: str


class ListPullRequestsParams(BaseModel):
    """Parameters for listing pull requests in a repository."""

    owner: str
    repo: str
    state: str = "open"
    base: str | None = None
    sort: str = "created"
    limit: int = 30


class GetPullRequestParams(BaseModel):
    """Parameters for retrieving a single pull request."""

    owner: str
    repo: str
    pr_number: int


class ListMilestonesParams(BaseModel):
    """Parameters for listing milestones in a repository."""

    owner: str
    repo: str
    state: str = "open"


class GetFileContentParams(BaseModel):
    """Parameters for retrieving file content from a repository."""

    owner: str
    repo: str
    path: str
    ref: str | None = None


class ListBranchesParams(BaseModel):
    """Parameters for listing branches in a repository."""

    owner: str
    repo: str


class ExploreReleasesParams(BaseModel):
    """Parameters for exploring releases of a repository."""

    owner: str
    repo: str
    tag: str | None = None
    limit: int = 30


class CreateBranchParams(BaseModel):
    """Parameters for creating a new branch from an existing source branch."""

    owner: str
    repo: str
    branch_name: str
    source_branch: str = "main"


class UpdateFileParams(BaseModel):
    """Parameters for creating or updating a file in a repository."""

    owner: str
    repo: str
    path: str
    content: str
    commit_message: str
    branch: str = "main"


class CreatePullRequestParams(BaseModel):
    """Parameters for creating a pull request."""

    owner: str
    repo: str
    title: str
    head: str
    base: str = "main"
    body: str = ""
    draft: bool = False


class CreateReleaseParams(BaseModel):
    """Parameters for creating a release.

    When ``release_notes`` and ``generate_release_notes=True`` are both
    provided, GitHub prepends the manual notes to the auto-generated notes.
    """

    owner: str
    repo: str
    tag_name: str
    release_title: str = ""
    target_commitish: str = ""
    release_notes: str = ""
    draft: bool = False
    prerelease: bool = False
    generate_release_notes: bool = False


class GenerateReleaseNotesParams(BaseModel):
    """Parameters for previewing auto-generated release notes."""

    owner: str
    repo: str
    tag_name: str
    target_commitish: str = ""
    previous_tag_name: str = ""
    configuration_file_path: str = ""


class ForkRepositoryParams(BaseModel):
    """Parameters for forking a repository.

    ``organization`` forks into that org; leave empty to fork into the
    authenticated user's account. ``name`` overrides the fork's name.
    """

    owner: str
    repo: str
    organization: str = ""
    name: str = ""
    default_branch_only: bool = False


class GetRepoTreeParams(BaseModel):
    """Parameters for retrieving the recursive file tree of a repository."""

    owner: str
    repo: str
    ref: str = ""
    path_filter: str = ""


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class UserSummary(BaseModel):
    """Lightweight GitHub user representation."""

    model_config = ConfigDict(extra="ignore")

    login: str
    id: int


class LabelSummary(BaseModel):
    """Lightweight label representation."""

    model_config = ConfigDict(extra="ignore")

    name: str
    color: str | None = None
    description: str | None = None


class MilestoneSummary(BaseModel):
    """Lightweight milestone representation."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    state: str
    open_issues: int = 0
    closed_issues: int = 0
    description: str | None = None


class RepositorySummary(BaseModel):
    """Lightweight repository representation for list endpoints."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    full_name: str
    private: bool = False
    description: str | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    default_branch: str = "main"
    topics: list[str] = []
    owner: UserSummary | None = None
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IssueSummary(BaseModel):
    """Issue representation for list endpoints."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    state: str
    body: str | None = None
    user: UserSummary | None = None
    labels: list[LabelSummary] = []
    assignees: list[UserSummary] = []
    milestone: MilestoneSummary | None = None
    comments: int = 0
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None
    pull_request: dict[str, Any] | None = None


class IssueCommentSummary(BaseModel):
    """Issue comment representation."""

    model_config = ConfigDict(extra="ignore")

    id: int
    body: str
    user: UserSummary | None = None
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class BranchRef(BaseModel):
    """A PR head or base branch reference."""

    model_config = ConfigDict(extra="ignore")

    ref: str
    sha: str | None = None


class PullRequestSummary(BaseModel):
    """Pull request representation for list endpoints."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    state: str
    body: str | None = None
    user: UserSummary | None = None
    labels: list[LabelSummary] = []
    head: BranchRef | None = None
    base: BranchRef | None = None
    merged_at: str | None = None
    draft: bool = False
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


class PullRequestDetail(BaseModel):
    """Detailed pull request with merge statistics."""

    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    state: str
    body: str | None = None
    user: UserSummary | None = None
    labels: list[LabelSummary] = []
    head: BranchRef | None = None
    base: BranchRef | None = None
    merged_at: str | None = None
    merged: bool = False
    mergeable: bool | None = None
    draft: bool = False
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    commits: int = 0
    comments: int = 0
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


class BranchSummary(BaseModel):
    """Branch representation."""

    model_config = ConfigDict(extra="ignore")

    name: str
    protected: bool = False


class ReleaseAsset(BaseModel):
    """A single release asset."""

    model_config = ConfigDict(extra="ignore")

    name: str
    size: int = 0
    download_count: int = 0
    browser_download_url: str | None = None


class ReleaseSummary(BaseModel):
    """Release representation."""

    model_config = ConfigDict(extra="ignore")

    tag_name: str
    name: str | None = None
    body: str | None = None
    draft: bool = False
    prerelease: bool = False
    published_at: str | None = None
    author: UserSummary | None = None
    assets: list[ReleaseAsset] = []
    html_url: str | None = None


class FileContentEntry(BaseModel):
    """A file or directory entry from the contents API."""

    model_config = ConfigDict(extra="ignore")

    name: str
    path: str
    type: str
    size: int = 0
    content: str | None = None
    encoding: str | None = None
    sha: str | None = None
    html_url: str | None = None


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListRepositoriesResult(ToolResult):
    """Result of listing repositories."""

    model_config = ConfigDict(extra="ignore")

    repositories: list[RepositorySummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed repositories."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.repositories)} repository(ies):"]
        for repo in self.repositories:
            visibility = "Private" if repo.private else "Public"
            language = repo.language or "No language"
            lines.append(f"  - {repo.name} ({repo.full_name})")
            lines.append(f"    Stars: {repo.stargazers_count} | Forks: {repo.forks_count} | {visibility} | {language}")
        return "\n".join(lines)


class GetRepositoryResult(ToolResult):
    """Result of retrieving a single repository."""

    model_config = ConfigDict(extra="ignore")

    repository: RepositorySummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the repository."""
        if not self.success:
            return f"Error: {self.error}"
        if self.repository is None:
            return "No repository data."
        r = self.repository
        visibility = "Private" if r.private else "Public"
        language = r.language or "Not specified"
        description = r.description or "No description"
        lines = [
            f"Repository: {r.full_name}",
            f"Description: {description}",
            f"Visibility: {visibility}",
            f"Language: {language}",
            f"Stars: {r.stargazers_count} | Forks: {r.forks_count}",
            f"Open issues: {r.open_issues_count}",
            f"Default branch: {r.default_branch}",
        ]
        if r.topics:
            lines.append(f"Topics: {', '.join(r.topics)}")
        return "\n".join(lines)


class ListIssuesResult(ToolResult):
    """Result of listing issues."""

    model_config = ConfigDict(extra="ignore")

    issues: list[IssueSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed issues."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.issues)} issue(s):"]
        for issue in self.issues:
            author = issue.user.login if issue.user else "unknown"
            label_names = [lb.name for lb in issue.labels]
            labels_str = ", ".join(label_names) if label_names else "none"
            milestone_str = issue.milestone.title if issue.milestone else "none"
            lines.append(f"  - #{issue.number}: {issue.title}")
            lines.append(
                f"    State: {issue.state} | Labels: {labels_str} | Author: {author} | Milestone: {milestone_str}"
            )
        return "\n".join(lines)


class GetIssueResult(ToolResult):
    """Result of retrieving a single issue."""

    model_config = ConfigDict(extra="ignore")

    issue: IssueSummary | None = None
    comments_list: list[IssueCommentSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the issue."""
        if not self.success:
            return f"Error: {self.error}"
        if self.issue is None:
            return "No issue data."
        i = self.issue
        author = i.user.login if i.user else "unknown"
        label_names = [lb.name for lb in i.labels]
        labels_str = ", ".join(label_names) if label_names else "none"
        assignee_names = [a.login for a in i.assignees]
        assignees_str = ", ".join(assignee_names) if assignee_names else "unassigned"
        body = i.body or "No description provided."
        lines = [
            f"Issue #{i.number}: {i.title}",
            f"State: {i.state}",
            f"Author: {author}",
            f"Labels: {labels_str}",
            f"Assignees: {assignees_str}",
            f"Created: {i.created_at}",
            "",
            "Description:",
            body,
        ]
        if self.comments_list:
            lines.extend(["", f"Comments ({len(self.comments_list)}):"])
            for c in self.comments_list:
                c_author = c.user.login if c.user else "unknown"
                lines.append(f"  {c_author} ({c.created_at}): {c.body}")
        return "\n".join(lines)


class CreateIssueResult(ToolResult):
    """Result of creating an issue."""

    model_config = ConfigDict(extra="ignore")

    issue: IssueSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created issue."""
        if not self.success:
            return f"Error: {self.error}"
        if self.issue is None:
            return "Issue created but no details available."
        i = self.issue
        lines = [
            "Issue created successfully!",
            f"  Issue #{i.number}: {i.title}",
            f"  URL: {i.html_url}",
        ]
        return "\n".join(lines)


class AddIssueCommentItem(BaseModel):
    """Per-issue outcome of a bulk add-issue-comments call."""

    model_config = ConfigDict(extra="ignore")

    issue_number: int
    success: bool = True
    error: str | None = None
    comment: IssueCommentSummary | None = None


class AddIssueCommentsResult(ToolResult):
    """Result of adding the same comment across one or more issues."""

    model_config = ConfigDict(extra="ignore")

    items: list[AddIssueCommentItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk comment add."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No issues processed."
        lines: list[str] = []
        for item in self.items:
            if item.success and item.comment is not None:
                lines.append(f"- Issue #{item.issue_number}: Comment added. URL: {item.comment.html_url}")
            elif item.success:
                lines.append(f"- Issue #{item.issue_number}: Comment added.")
            else:
                lines.append(f"- Issue #{item.issue_number}: Failed: {item.error}")
        return "\n".join(lines)


class ListPullRequestsResult(ToolResult):
    """Result of listing pull requests."""

    model_config = ConfigDict(extra="ignore")

    pull_requests: list[PullRequestSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed pull requests."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.pull_requests)} pull request(s):"]
        for pr in self.pull_requests:
            author = pr.user.login if pr.user else "unknown"
            base_ref = pr.base.ref if pr.base else "unknown"
            head_ref = pr.head.ref if pr.head else "unknown"
            info = f"    State: {pr.state} | Author: {author} | Base: {base_ref} <- {head_ref}"
            if pr.merged_at:
                info += f" | Merged: {pr.merged_at}"
            lines.append(f"  - #{pr.number}: {pr.title}")
            lines.append(info)
        return "\n".join(lines)


class GetPullRequestResult(ToolResult):
    """Result of retrieving a single pull request."""

    model_config = ConfigDict(extra="ignore")

    pull_request: PullRequestDetail | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the pull request."""
        if not self.success:
            return f"Error: {self.error}"
        if self.pull_request is None:
            return "No pull request data."
        pr = self.pull_request
        author = pr.user.login if pr.user else "unknown"
        base_ref = pr.base.ref if pr.base else "unknown"
        head_ref = pr.head.ref if pr.head else "unknown"
        merged_str = pr.merged_at if pr.merged_at else "Not merged"
        mergeable_str = "Yes" if pr.mergeable else ("No" if pr.mergeable is False else "Checking...")
        lines = [
            f"Pull Request #{pr.number}: {pr.title}",
            f"State: {pr.state}",
            f"Author: {author}",
            f"Base: {base_ref} <- {head_ref}",
            f"Merged: {merged_str}",
            f"Mergeable: {mergeable_str}",
            f"Changed files: {pr.changed_files} (+{pr.additions} -{pr.deletions})",
        ]
        if pr.body:
            lines.extend(["", "Description:", pr.body])
        return "\n".join(lines)


class ListMilestonesResult(ToolResult):
    """Result of listing milestones."""

    model_config = ConfigDict(extra="ignore")

    milestones: list[MilestoneSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed milestones."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.milestones)} milestone(s):"]
        for ms in self.milestones:
            lines.append(f"  - #{ms.number}: {ms.title}")
            lines.append(f"    State: {ms.state} | Open issues: {ms.open_issues} | Closed issues: {ms.closed_issues}")
        return "\n".join(lines)


class GetFileContentResult(ToolResult):
    """Result of retrieving file content."""

    model_config = ConfigDict(extra="ignore")

    file: FileContentEntry | None = None
    decoded_content: str | None = None
    directory_entries: list[FileContentEntry] = []
    is_directory: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the file content."""
        if not self.success:
            return f"Error: {self.error}"
        if self.is_directory:
            lines = [f"Directory: {self.file.path}/" if self.file else "Directory:"]
            for entry in self.directory_entries:
                suffix = "/" if entry.type == "dir" else ""
                lines.append(f"  - {entry.name}{suffix} ({entry.type})")
            return "\n".join(lines)
        if self.file is None:
            return "No file data."
        content = self.decoded_content or "(empty file)"
        return f"File: {self.file.path}\n\n{content}"


class ListBranchesResult(ToolResult):
    """Result of listing branches."""

    model_config = ConfigDict(extra="ignore")

    branches: list[BranchSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the listed branches."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Found {len(self.branches)} branch(es):"]
        for branch in self.branches:
            suffix = " (protected)" if branch.protected else ""
            lines.append(f"  - {branch.name}{suffix}")
        return "\n".join(lines)


class ExploreReleasesResult(ToolResult):
    """Result of exploring releases."""

    model_config = ConfigDict(extra="ignore")

    releases: list[ReleaseSummary] = []
    single_release: ReleaseSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the releases."""
        if not self.success:
            return f"Error: {self.error}"
        if self.single_release:
            r = self.single_release
            author = r.author.login if r.author else "unknown"
            is_draft = "Yes" if r.draft else "No"
            is_prerelease = "Yes" if r.prerelease else "No"
            body = r.body or "No description provided."
            lines = [
                f"Release: {r.name or r.tag_name}",
                f"Tag: {r.tag_name}",
                f"Published: {r.published_at}",
                f"Author: {author}",
                f"Draft: {is_draft} | Prerelease: {is_prerelease}",
                "",
                "Release notes:",
                body,
            ]
            if r.assets:
                lines.extend(["", f"Assets ({len(r.assets)}):"])
                for asset in r.assets:
                    size_mb = asset.size / (1024 * 1024)
                    lines.append(f"  - {asset.name} ({size_mb:.1f} MB)")
            return "\n".join(lines)
        lines = [f"Found {len(self.releases)} release(s):"]
        for r in self.releases:
            author = r.author.login if r.author else "unknown"
            is_draft = "Yes" if r.draft else "No"
            is_prerelease = "Yes" if r.prerelease else "No"
            published = r.published_at[:10] if r.published_at else "unknown"
            assets_count = len(r.assets)
            lines.append(f"  - {r.name or r.tag_name} (tag: {r.tag_name})")
            lines.append(
                f"    Published: {published} | Author: {author}"
                f" | Draft: {is_draft} | Prerelease: {is_prerelease}"
                f" | Assets: {assets_count}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Results for branch, file, PR, release, fork, and tree write/read operations
# ---------------------------------------------------------------------------


class CreateBranchResult(ToolResult):
    """Result of creating a new branch."""

    model_config = ConfigDict(extra="ignore")

    branch_name: str | None = None
    source_branch: str | None = None
    sha: str | None = None
    url: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created branch."""
        if not self.success:
            return f"Error: {self.error}"
        return "\n".join(
            [
                "Branch created successfully!",
                f"- Branch: {self.branch_name}",
                f"- Source: {self.source_branch}",
                f"- URL: {self.url}",
            ]
        )


class UpdateFileResult(ToolResult):
    """Result of creating or updating a file."""

    model_config = ConfigDict(extra="ignore")

    path: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    url: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated file."""
        if not self.success:
            return f"Error: {self.error}"
        short_sha = (self.commit_sha or "")[:8]
        return "\n".join(
            [
                "File updated successfully!",
                f"- Path: {self.path}",
                f"- Branch: {self.branch}",
                f"- Commit: {short_sha}",
                f"- URL: {self.url}",
            ]
        )


class CreatePullRequestResult(ToolResult):
    """Result of creating a pull request."""

    model_config = ConfigDict(extra="ignore")

    pull_request: PullRequestDetail | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created pull request."""
        if not self.success:
            return f"Error: {self.error}"
        if self.pull_request is None:
            return "Pull request created but no details available."
        pr = self.pull_request
        head_ref = pr.head.ref if pr.head else "unknown"
        base_ref = pr.base.ref if pr.base else "unknown"
        return "\n".join(
            [
                "Pull request created successfully!",
                f"- PR #{pr.number}: {pr.title}",
                f"- Head: {head_ref} -> Base: {base_ref}",
                f"- URL: {pr.html_url}",
            ]
        )


class CreateReleaseResult(ToolResult):
    """Result of creating a release."""

    model_config = ConfigDict(extra="ignore")

    release: ReleaseSummary | None = None
    target_commitish: str | None = None
    notes_mode: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created release."""
        if not self.success:
            return f"Error: {self.error}"
        if self.release is None:
            return "Release created but no details available."
        r = self.release
        title = r.name or r.tag_name
        target = self.target_commitish or "default branch"
        is_draft = "Yes" if r.draft else "No"
        is_prerelease = "Yes" if r.prerelease else "No"
        return "\n".join(
            [
                "Release created successfully!",
                f"- Release: {title}",
                f"- Tag: {r.tag_name}",
                f"- Target: {target}",
                f"- Draft: {is_draft} | Prerelease: {is_prerelease}",
                f"- Notes: {self.notes_mode or 'none'}",
                f"- URL: {r.html_url}",
            ]
        )


class GenerateReleaseNotesResult(ToolResult):
    """Result of previewing auto-generated release notes."""

    model_config = ConfigDict(extra="ignore")

    owner: str | None = None
    repo: str | None = None
    tag_name: str | None = None
    release_title: str | None = None
    target_commitish: str | None = None
    previous_tag_name: str | None = None
    notes: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the generated release notes."""
        if not self.success:
            return f"Error: {self.error}"
        title = self.release_title or (self.tag_name or "")
        lines = [
            f"# Generated Release Notes for {self.owner}/{self.repo}",
            f"**Tag:** {self.tag_name}",
            f"**Release Title:** {title}",
        ]
        if self.target_commitish:
            lines.append(f"**Target:** {self.target_commitish}")
        if self.previous_tag_name:
            lines.append(f"**Previous Tag:** {self.previous_tag_name}")
        lines.extend(["", "## Release Notes", self.notes or "No release notes generated."])
        return "\n".join(lines)


class ForkRepositoryResult(ToolResult):
    """Result of forking a repository."""

    model_config = ConfigDict(extra="ignore")

    fork_full_name: str | None = None
    source_full_name: str | None = None
    html_url: str | None = None

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created fork."""
        if not self.success:
            return f"Error: {self.error}"
        return "\n".join(
            [
                "Repository forked successfully!",
                f"- Fork: {self.fork_full_name}",
                f"- Source: {self.source_full_name}",
                f"- URL: {self.html_url}",
            ]
        )


class RepoTreeEntry(BaseModel):
    """A single file entry in a repository tree listing."""

    model_config = ConfigDict(extra="ignore")

    path: str
    size: int = 0
    sha: str | None = None


class GetRepoTreeResult(ToolResult):
    """Result of retrieving the recursive file tree of a repository."""

    model_config = ConfigDict(extra="ignore")

    owner: str | None = None
    repo: str | None = None
    ref: str | None = None
    path_filter: str | None = None
    files: list[RepoTreeEntry] = []
    truncated: bool = False

    @staticmethod
    def _fmt_size(size: int) -> str:
        """Format a byte count as a short human-readable string."""
        if size >= 1_048_576:
            return f"{size / 1_048_576:.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def __str__(self) -> str:
        """Return an LLM-readable summary of the repository tree."""
        if not self.success:
            return f"Error: {self.error}"
        ref_label = self.ref or "default branch"
        lines = [f"# Repository tree: {self.owner}/{self.repo} (ref: {ref_label})"]
        if self.path_filter:
            lines.append(f"Filtered to: {self.path_filter}/")
        lines.append(f"Found {len(self.files)} files.")
        if self.truncated:
            lines.append("Note: tree was truncated by GitHub (repo is very large). Not all files may be listed.")
        lines.append("")
        for entry in self.files:
            lines.append(f"{entry.path} ({self._fmt_size(entry.size)})")
        return "\n".join(lines)
