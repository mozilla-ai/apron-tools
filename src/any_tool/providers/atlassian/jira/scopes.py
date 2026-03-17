"""OAuth scope definitions for Atlassian Jira tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class JiraScope(StrEnum):
    """OAuth scopes for Atlassian Jira API access."""

    READ_JIRA_WORK = "read:jira-work"
    WRITE_JIRA_WORK = "write:jira-work"
    READ_JIRA_USER = "read:jira-user"


SCOPES: dict[str, list[JiraScope]] = {
    "explore_projects": [JiraScope.READ_JIRA_WORK],
    "explore_issues": [JiraScope.READ_JIRA_WORK],
    "create_issue": [JiraScope.WRITE_JIRA_WORK],
    "edit_issue": [JiraScope.WRITE_JIRA_WORK],
    "assign_issue": [JiraScope.WRITE_JIRA_WORK, JiraScope.READ_JIRA_USER],
    "add_comment": [JiraScope.WRITE_JIRA_WORK],
    "list_versions": [JiraScope.READ_JIRA_WORK],
    "list_boards": [JiraScope.READ_JIRA_WORK],
    "list_sprints": [JiraScope.READ_JIRA_WORK],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="atlassian_jira",
    display_name="Atlassian Jira",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
