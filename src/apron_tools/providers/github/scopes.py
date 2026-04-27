"""OAuth scope definitions for GitHub tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GitHubScope(Scope):
    """OAuth scopes for GitHub API access."""

    REPO = (
        "repo",
        "All Repositories",
        "Full access to public and private repositories, including code, issues, and pull requests",
        "write",
        False,
    )
    PUBLIC_REPO = (
        "public_repo",
        "Public Repositories",
        "Access public repositories only (code, issues, pull requests)",
        "write",
        False,
    )


SCOPES: dict[str, list[GitHubScope]] = {
    "github_list_repositories": [GitHubScope.REPO],
    "github_get_repository": [GitHubScope.REPO],
    "github_list_issues": [GitHubScope.REPO],
    "github_get_issue": [GitHubScope.REPO],
    "github_create_issue": [GitHubScope.REPO],
    "github_add_issue_comments": [GitHubScope.REPO],
    "github_list_pull_requests": [GitHubScope.REPO],
    "github_get_pull_request": [GitHubScope.REPO],
    "github_create_pull_request": [GitHubScope.REPO],
    "github_list_milestones": [GitHubScope.REPO],
    "github_get_file_content": [GitHubScope.REPO],
    "github_update_file": [GitHubScope.REPO],
    "github_list_branches": [GitHubScope.REPO],
    "github_create_branch": [GitHubScope.REPO],
    "github_explore_releases": [GitHubScope.REPO],
    "github_generate_release_notes": [GitHubScope.REPO],
    "github_create_release": [GitHubScope.REPO],
    "github_fork_repository": [GitHubScope.REPO],
    "github_get_repo_tree": [GitHubScope.REPO],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="github",
    display_name="GitHub",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
