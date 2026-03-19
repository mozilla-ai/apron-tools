"""Tests for Linear provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.linear.types import (
    CreateIssueParams,
    CreateIssueResult,
    CreateProjectParams,
    CreateProjectResult,
    ListCyclesParams,
    ListCyclesResult,
    ListIssuesParams,
    ListIssuesResult,
    ListProjectsParams,
    ListProjectsResult,
    ListTeamsParams,
    ListTeamsResult,
    ListUsersParams,
    ListUsersResult,
    ReadIssueParams,
    ReadIssueResult,
    UpdateIssueParams,
    UpdateIssueResult,
    UpdateProjectParams,
    UpdateProjectResult,
    WhoamiParams,
    WhoamiResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestWhoamiParams:
    def test_empty(self):
        params = WhoamiParams()
        assert params is not None


class TestListTeamsParams:
    def test_empty(self):
        params = ListTeamsParams()
        assert params is not None


class TestListUsersParams:
    def test_empty(self):
        params = ListUsersParams()
        assert params is not None


class TestListIssuesParams:
    def test_defaults(self):
        params = ListIssuesParams()
        assert params.limit == 50
        assert params.team_id is None
        assert params.assignee_id is None
        assert params.state is None
        assert params.project_id is None
        assert params.created_after is None
        assert params.updated_after is None

    def test_custom_values(self):
        params = ListIssuesParams(
            team_id="team-001",
            assignee_id="user-001",
            state="In Progress",
            limit=10,
        )
        assert params.team_id == "team-001"
        assert params.assignee_id == "user-001"
        assert params.state == "In Progress"
        assert params.limit == 10


class TestReadIssueParams:
    def test_required_issue_id(self):
        params = ReadIssueParams(issue_id="issue-001")
        assert params.issue_id == "issue-001"


class TestCreateIssueParams:
    def test_required_fields(self):
        params = CreateIssueParams(title="Bug fix", team_id="team-001")
        assert params.title == "Bug fix"
        assert params.team_id == "team-001"
        assert params.description is None
        assert params.priority is None

    def test_all_fields(self):
        params = CreateIssueParams(
            title="Bug fix",
            team_id="team-001",
            description="Fix the bug",
            project_id="project-001",
            assignee_id="user-001",
            priority=1,
            state_id="state-001",
        )
        assert params.priority == 1
        assert params.state_id == "state-001"


class TestUpdateIssueParams:
    def test_required_fields(self):
        params = UpdateIssueParams(issue_id="issue-001")
        assert params.issue_id == "issue-001"
        assert params.title is None

    def test_partial_update(self):
        params = UpdateIssueParams(issue_id="issue-001", title="New title")
        assert params.title == "New title"
        assert params.description is None


class TestListProjectsParams:
    def test_defaults(self):
        params = ListProjectsParams()
        assert params.team_id is None

    def test_with_team(self):
        params = ListProjectsParams(team_id="team-001")
        assert params.team_id == "team-001"


class TestCreateProjectParams:
    def test_required_fields(self):
        params = CreateProjectParams(name="Q2 Sprint", team_ids=["team-001"])
        assert params.name == "Q2 Sprint"
        assert params.team_ids == ["team-001"]
        assert params.description is None


class TestUpdateProjectParams:
    def test_required_fields(self):
        params = UpdateProjectParams(project_id="project-001")
        assert params.project_id == "project-001"
        assert params.name is None


class TestListCyclesParams:
    def test_defaults(self):
        params = ListCyclesParams()
        assert params.team_id is None

    def test_with_team(self):
        params = ListCyclesParams(team_id="team-001")
        assert params.team_id == "team-001"


# ---------------------------------------------------------------------------
# WhoamiResult
# ---------------------------------------------------------------------------


class TestWhoamiResult:
    def test_parse_api_response(self):
        data = _load_json("whoami.json")
        result = WhoamiResult.model_validate(data["data"]["viewer"])

        assert result.success is True
        assert result.id == "user-001"
        assert result.name == "Alice Smith"
        assert result.email == "alice@example.com"
        assert result.display_name == "Alice"

    def test_str_output(self):
        data = _load_json("whoami.json")
        result = WhoamiResult.model_validate(data["data"]["viewer"])
        text = str(result)

        assert "Alice Smith" in text
        assert "alice@example.com" in text
        assert "user-001" in text

    def test_str_on_error(self):
        result = WhoamiResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


# ---------------------------------------------------------------------------
# ListTeamsResult
# ---------------------------------------------------------------------------


class TestListTeamsResult:
    def test_parse_api_response(self):
        data = _load_json("list_teams.json")
        nodes = data["data"]["teams"]["nodes"]
        result = ListTeamsResult(teams=nodes)

        assert result.success is True
        assert len(result.teams) == 2
        assert result.teams[0].id == "team-001"
        assert result.teams[0].name == "Engineering"
        assert result.teams[0].key == "ENG"

    def test_str_output(self):
        data = _load_json("list_teams.json")
        nodes = data["data"]["teams"]["nodes"]
        result = ListTeamsResult(teams=nodes)
        text = str(result)

        assert "2 team(s)" in text
        assert "Engineering" in text
        assert "Design" in text

    def test_str_on_error(self):
        result = ListTeamsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# ListUsersResult
# ---------------------------------------------------------------------------


class TestListUsersResult:
    def test_parse_api_response(self):
        data = _load_json("list_users.json")
        nodes = data["data"]["users"]["nodes"]
        result = ListUsersResult(users=nodes)

        assert result.success is True
        assert len(result.users) == 2
        assert result.users[0].name == "Alice Smith"
        assert result.users[0].active is True

    def test_str_output(self):
        data = _load_json("list_users.json")
        nodes = data["data"]["users"]["nodes"]
        result = ListUsersResult(users=nodes)
        text = str(result)

        assert "2 user(s)" in text
        assert "Alice Smith" in text
        assert "active" in text

    def test_str_on_error(self):
        result = ListUsersResult(success=False, error="Rate limited")
        assert str(result) == "Error: Rate limited"


# ---------------------------------------------------------------------------
# ListIssuesResult
# ---------------------------------------------------------------------------


class TestListIssuesResult:
    def test_parse_api_response(self):
        data = _load_json("list_issues.json")
        from any_tool.providers.linear.types import IssueSummary

        nodes = data["data"]["issues"]["nodes"]
        issues = [IssueSummary.model_validate(n) for n in nodes]
        result = ListIssuesResult(issues=issues)

        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].identifier == "ENG-123"
        assert result.issues[0].title == "Fix login bug"
        assert result.issues[0].state is not None
        assert result.issues[0].state.name == "In Progress"

    def test_str_output(self):
        from any_tool.providers.linear.types import IssueSummary

        data = _load_json("list_issues.json")
        nodes = data["data"]["issues"]["nodes"]
        issues = [IssueSummary.model_validate(n) for n in nodes]
        result = ListIssuesResult(issues=issues)
        text = str(result)

        assert "1 issue(s)" in text
        assert "ENG-123" in text
        assert "Fix login bug" in text
        assert "In Progress" in text

    def test_str_on_error(self):
        result = ListIssuesResult(success=False, error="Bad request")
        assert str(result) == "Error: Bad request"


# ---------------------------------------------------------------------------
# ReadIssueResult
# ---------------------------------------------------------------------------


class TestReadIssueResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import IssueDetail

        data = _load_json("read_issue.json")
        issue_data = data["data"]["issue"]
        # Flatten connections like the tool does.
        issue_data["labels"] = issue_data["labels"]["nodes"]
        issue_data["comments"] = issue_data["comments"]["nodes"]
        issue = IssueDetail.model_validate(issue_data)
        result = ReadIssueResult(issue=issue)

        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-123"
        assert result.issue.priority_label == "Urgent"
        assert len(result.issue.labels) == 1
        assert result.issue.labels[0].name == "bug"
        assert result.issue.project is not None
        assert result.issue.project.name == "Q1 Sprint"
        assert len(result.issue.comments) == 1

    def test_str_output(self):
        from any_tool.providers.linear.types import IssueDetail

        data = _load_json("read_issue.json")
        issue_data = data["data"]["issue"]
        issue_data["labels"] = issue_data["labels"]["nodes"]
        issue_data["comments"] = issue_data["comments"]["nodes"]
        issue = IssueDetail.model_validate(issue_data)
        result = ReadIssueResult(issue=issue)
        text = str(result)

        assert "ENG-123" in text
        assert "Fix login bug" in text
        assert "Urgent" in text
        assert "bug" in text
        assert "Q1 Sprint" in text

    def test_str_on_error(self):
        result = ReadIssueResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_no_issue(self):
        result = ReadIssueResult(success=True, issue=None)
        assert str(result) == "Issue not found."


# ---------------------------------------------------------------------------
# CreateIssueResult
# ---------------------------------------------------------------------------


class TestCreateIssueResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import MutationIssue

        data = _load_json("create_issue.json")
        issue_data = data["data"]["issueCreate"]["issue"]
        issue = MutationIssue.model_validate(issue_data)
        result = CreateIssueResult(issue=issue)

        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-124"

    def test_str_output(self):
        from any_tool.providers.linear.types import MutationIssue

        data = _load_json("create_issue.json")
        issue_data = data["data"]["issueCreate"]["issue"]
        issue = MutationIssue.model_validate(issue_data)
        result = CreateIssueResult(issue=issue)
        text = str(result)

        assert "ENG-124" in text
        assert "New issue" in text

    def test_str_on_error(self):
        result = CreateIssueResult(success=False, error="Missing team")
        assert str(result) == "Error: Missing team"


# ---------------------------------------------------------------------------
# UpdateIssueResult
# ---------------------------------------------------------------------------


class TestUpdateIssueResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import MutationIssue

        data = _load_json("update_issue.json")
        issue_data = data["data"]["issueUpdate"]["issue"]
        issue = MutationIssue.model_validate(issue_data)
        result = UpdateIssueResult(issue=issue)

        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-123"

    def test_str_output(self):
        from any_tool.providers.linear.types import MutationIssue

        data = _load_json("update_issue.json")
        issue_data = data["data"]["issueUpdate"]["issue"]
        issue = MutationIssue.model_validate(issue_data)
        result = UpdateIssueResult(issue=issue)
        text = str(result)

        assert "ENG-123" in text
        assert "Updated" in text

    def test_str_on_error(self):
        result = UpdateIssueResult(success=False, error="Conflict")
        assert str(result) == "Error: Conflict"


# ---------------------------------------------------------------------------
# ListProjectsResult
# ---------------------------------------------------------------------------


class TestListProjectsResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import ProjectDetail

        data = _load_json("list_projects.json")
        nodes = data["data"]["projects"]["nodes"]
        projects = []
        for node in nodes:
            if "teams" in node and isinstance(node["teams"], dict):
                node["teams"] = node["teams"].get("nodes", [])
            projects.append(ProjectDetail.model_validate(node))
        result = ListProjectsResult(projects=projects)

        assert result.success is True
        assert len(result.projects) == 1
        assert result.projects[0].name == "Q1 Sprint"
        assert result.projects[0].progress == 0.45
        assert len(result.projects[0].teams) == 1

    def test_str_output(self):
        from any_tool.providers.linear.types import ProjectDetail

        data = _load_json("list_projects.json")
        nodes = data["data"]["projects"]["nodes"]
        projects = []
        for node in nodes:
            if "teams" in node and isinstance(node["teams"], dict):
                node["teams"] = node["teams"].get("nodes", [])
            projects.append(ProjectDetail.model_validate(node))
        result = ListProjectsResult(projects=projects)
        text = str(result)

        assert "1 project(s)" in text
        assert "Q1 Sprint" in text
        assert "Engineering" in text

    def test_str_on_error(self):
        result = ListProjectsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# CreateProjectResult
# ---------------------------------------------------------------------------


class TestCreateProjectResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import MutationProject

        data = _load_json("create_project.json")
        project_data = data["data"]["projectCreate"]["project"]
        project = MutationProject.model_validate(project_data)
        result = CreateProjectResult(project=project)

        assert result.success is True
        assert result.project is not None
        assert result.project.name == "New Project"

    def test_str_output(self):
        from any_tool.providers.linear.types import MutationProject

        data = _load_json("create_project.json")
        project_data = data["data"]["projectCreate"]["project"]
        project = MutationProject.model_validate(project_data)
        result = CreateProjectResult(project=project)
        text = str(result)

        assert "New Project" in text
        assert "project-002" in text

    def test_str_on_error(self):
        result = CreateProjectResult(success=False, error="Missing name")
        assert str(result) == "Error: Missing name"


# ---------------------------------------------------------------------------
# UpdateProjectResult
# ---------------------------------------------------------------------------


class TestUpdateProjectResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import MutationProject

        data = _load_json("update_project.json")
        project_data = data["data"]["projectUpdate"]["project"]
        project = MutationProject.model_validate(project_data)
        result = UpdateProjectResult(project=project)

        assert result.success is True
        assert result.project is not None
        assert result.project.name == "Q1 Sprint (updated)"

    def test_str_output(self):
        from any_tool.providers.linear.types import MutationProject

        data = _load_json("update_project.json")
        project_data = data["data"]["projectUpdate"]["project"]
        project = MutationProject.model_validate(project_data)
        result = UpdateProjectResult(project=project)
        text = str(result)

        assert "Q1 Sprint (updated)" in text

    def test_str_on_error(self):
        result = UpdateProjectResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListCyclesResult
# ---------------------------------------------------------------------------


class TestListCyclesResult:
    def test_parse_api_response(self):
        from any_tool.providers.linear.types import CycleDetail

        data = _load_json("list_cycles.json")
        nodes = data["data"]["cycles"]["nodes"]
        cycles = [CycleDetail.model_validate(n) for n in nodes]
        result = ListCyclesResult(cycles=cycles)

        assert result.success is True
        assert len(result.cycles) == 1
        assert result.cycles[0].name == "Sprint 5"
        assert result.cycles[0].progress == 0.3

    def test_str_output(self):
        from any_tool.providers.linear.types import CycleDetail

        data = _load_json("list_cycles.json")
        nodes = data["data"]["cycles"]["nodes"]
        cycles = [CycleDetail.model_validate(n) for n in nodes]
        result = ListCyclesResult(cycles=cycles)
        text = str(result)

        assert "1 cycle(s)" in text
        assert "Sprint 5" in text
        assert "30%" in text

    def test_str_on_error(self):
        result = ListCyclesResult(success=False, error="Timeout")
        assert str(result) == "Error: Timeout"
