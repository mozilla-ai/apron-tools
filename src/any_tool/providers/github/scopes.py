"""OAuth scope definitions for GitHub tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GitHubScope(StrEnum):
    """OAuth scopes for GitHub API access."""

    REPO = "repo"
    PUBLIC_REPO = "public_repo"


SCOPES: dict[str, list[GitHubScope]] = {
    "github_list_repositories": [GitHubScope.REPO],
    "github_get_repository": [GitHubScope.REPO],
    "github_list_issues": [GitHubScope.REPO],
    "github_get_issue": [GitHubScope.REPO],
    "github_create_issue": [GitHubScope.REPO],
    "github_add_issue_comment": [GitHubScope.REPO],
    "github_list_pull_requests": [GitHubScope.REPO],
    "github_get_pull_request": [GitHubScope.REPO],
    "github_list_milestones": [GitHubScope.REPO],
    "github_get_file_content": [GitHubScope.REPO],
    "github_list_branches": [GitHubScope.REPO],
    "github_explore_releases": [GitHubScope.REPO],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="github",
    display_name="GitHub",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
