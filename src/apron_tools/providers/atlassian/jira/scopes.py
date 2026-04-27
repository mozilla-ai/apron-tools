"""OAuth scope definitions for Atlassian Jira tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class JiraScope(Scope):
    """OAuth scopes for Atlassian Jira API access."""

    READ_JIRA_WORK = (
        "read:jira-work",
        "Read Issues",
        "View Jira issues, projects, and boards",
        "read",
        False,
    )
    WRITE_JIRA_WORK = (
        "write:jira-work",
        "Write Issues",
        "Create and modify Jira issues and comments",
        "write",
        False,
    )
    READ_JIRA_USER = (
        "read:jira-user",
        "Read Users",
        "View Jira user profiles",
        "read",
        False,
    )


SCOPES: dict[str, list[JiraScope]] = {
    "atlassian_jira_explore_projects": [JiraScope.READ_JIRA_WORK],
    "atlassian_jira_explore_issues": [JiraScope.READ_JIRA_WORK],
    "atlassian_jira_create_issue": [JiraScope.WRITE_JIRA_WORK],
    "atlassian_jira_edit_issue": [JiraScope.WRITE_JIRA_WORK],
    "atlassian_jira_assign_issue": [JiraScope.WRITE_JIRA_WORK, JiraScope.READ_JIRA_USER],
    "atlassian_jira_add_comment": [JiraScope.WRITE_JIRA_WORK],
    "atlassian_jira_list_versions": [JiraScope.READ_JIRA_WORK],
    "atlassian_jira_list_boards": [JiraScope.READ_JIRA_WORK],
    "atlassian_jira_list_sprints": [JiraScope.READ_JIRA_WORK],
    "atlassian_jira_upload_attachment": [JiraScope.WRITE_JIRA_WORK],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="atlassian_jira",
    display_name="Atlassian Jira",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
