"""Tests for Atlassian Jira provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.atlassian.jira.types import (
    AddCommentParams,
    AddCommentResult,
    AssignIssueParams,
    AssignIssueResult,
    CreateIssueParams,
    CreateIssueResult,
    EditIssueParams,
    EditIssueResult,
    ExploreIssuesParams,
    ExploreIssuesResult,
    ExploreProjectsParams,
    ExploreProjectsResult,
    IssueSummary,
    ListBoardsParams,
    ListBoardsResult,
    ListSprintsParams,
    ListSprintsResult,
    ListVersionsParams,
    ListVersionsResult,
    ProjectSummary,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreProjectsParams:
    def test_defaults(self):
        params = ExploreProjectsParams()
        assert params.max_results == 50

    def test_custom(self):
        params = ExploreProjectsParams(max_results=10)
        assert params.max_results == 10


class TestExploreIssuesParams:
    def test_required(self):
        params = ExploreIssuesParams(project_key="EX")
        assert params.project_key == "EX"
        assert params.updated_after is None
        assert params.max_results == 50

    def test_custom(self):
        params = ExploreIssuesParams(
            project_key="EX",
            updated_after="2024-01-01T00:00:00Z",
            max_results=20,
        )
        assert params.updated_after == "2024-01-01T00:00:00Z"
        assert params.max_results == 20


class TestCreateIssueParams:
    def test_required(self):
        params = CreateIssueParams(project_key="EX", summary="Test issue")
        assert params.project_key == "EX"
        assert params.summary == "Test issue"
        assert params.issue_type == "Task"
        assert params.description == ""
        assert params.priority == "Medium"

    def test_custom(self):
        params = CreateIssueParams(
            project_key="EX",
            summary="Bug found",
            issue_type="Bug",
            description="Steps to reproduce...",
            priority="High",
        )
        assert params.issue_type == "Bug"
        assert params.priority == "High"


class TestEditIssueParams:
    def test_required(self):
        params = EditIssueParams(issue_key="EX-1")
        assert params.issue_key == "EX-1"
        assert params.summary is None
        assert params.description is None
        assert params.priority is None


class TestAssignIssueParams:
    def test_defaults(self):
        params = AssignIssueParams(issue_key="EX-1")
        assert params.assign_to_me is True

    def test_unassign(self):
        params = AssignIssueParams(issue_key="EX-1", assign_to_me=False)
        assert params.assign_to_me is False


class TestAddCommentParams:
    def test_required(self):
        params = AddCommentParams(issue_key="EX-1", comment="Looks good")
        assert params.issue_key == "EX-1"
        assert params.comment == "Looks good"


class TestListVersionsParams:
    def test_required(self):
        params = ListVersionsParams(project_key="EX")
        assert params.project_key == "EX"
        assert params.status == ""


class TestListBoardsParams:
    def test_defaults(self):
        params = ListBoardsParams()
        assert params.project_key == ""


class TestListSprintsParams:
    def test_required(self):
        params = ListSprintsParams(board_id=84)
        assert params.board_id == 84
        assert params.state == ""


# ---------------------------------------------------------------------------
# ExploreProjectsResult
# ---------------------------------------------------------------------------


class TestExploreProjectsResult:
    def test_parse_projects(self):
        data = _load_json("project_search.json")
        projects = [ProjectSummary.model_validate(v) for v in data["values"]]
        result = ExploreProjectsResult(success=True, projects=projects)

        assert result.success is True
        assert len(result.projects) == 2

    def test_project_fields(self):
        data = _load_json("project_search.json")
        project = ProjectSummary.model_validate(data["values"][0])

        assert project.id == "10001"
        assert project.key == "EX"
        assert project.name == "Example"
        assert project.project_type_key == "software"
        assert project.lead is not None
        assert project.lead.display_name == "Mia Krystof"

    def test_str_output(self):
        data = _load_json("project_search.json")
        projects = [ProjectSummary.model_validate(v) for v in data["values"]]
        result = ExploreProjectsResult(success=True, projects=projects)
        text = str(result)

        assert "2 project(s)" in text
        assert "Example" in text
        assert "EX" in text
        assert "Mia Krystof" in text

    def test_str_on_error(self):
        result = ExploreProjectsResult(success=False, error="Cloud ID not found")
        assert str(result) == "Error: Cloud ID not found"


# ---------------------------------------------------------------------------
# ExploreIssuesResult
# ---------------------------------------------------------------------------


class TestExploreIssuesResult:
    def test_parse_issues(self):
        data = _load_json("search_issues.json")
        issues = [IssueSummary.model_validate(i) for i in data["issues"]]
        result = ExploreIssuesResult(
            success=True,
            project_key="EX",
            total=data["total"],
            issues=issues,
        )

        assert result.success is True
        assert result.total == 2
        assert len(result.issues) == 2

    def test_issue_fields(self):
        data = _load_json("search_issues.json")
        issue = IssueSummary.model_validate(data["issues"][0])

        assert issue.key == "EX-1"
        assert issue.fields.summary == "Example issue for testing"
        assert issue.fields.status.name == "To Do"
        assert issue.fields.priority.name == "Medium"
        assert issue.fields.issuetype.name == "Task"
        assert issue.fields.assignee is not None
        assert issue.fields.assignee.display_name == "Mia Krystof"
        assert issue.fields.reporter is not None
        assert issue.fields.reporter.display_name == "Phoebe Jiang"

    def test_null_assignee(self):
        data = _load_json("search_issues.json")
        issue = IssueSummary.model_validate(data["issues"][1])

        assert issue.key == "EX-2"
        assert issue.fields.assignee is None

    def test_str_output(self):
        data = _load_json("search_issues.json")
        issues = [IssueSummary.model_validate(i) for i in data["issues"]]
        result = ExploreIssuesResult(
            success=True,
            project_key="EX",
            total=2,
            issues=issues,
        )
        text = str(result)

        assert "Project EX" in text
        assert "2 issue(s)" in text
        assert "EX-1" in text
        assert "Example issue for testing" in text
        assert "Mia Krystof" in text
        assert "Unassigned" in text

    def test_str_on_error(self):
        result = ExploreIssuesResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# CreateIssueResult
# ---------------------------------------------------------------------------


class TestCreateIssueResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_issue.json")
        result = CreateIssueResult.model_validate(data)

        assert result.success is True
        assert result.id == "10000"
        assert result.key == "EX-3"
        assert result.self_url == "https://your-domain.atlassian.net/rest/api/3/issue/10000"

    def test_str_output(self):
        data = _load_json("create_issue.json")
        result = CreateIssueResult.model_validate(data)
        text = str(result)

        assert "Issue created" in text
        assert "EX-3" in text
        assert "10000" in text

    def test_str_on_error(self):
        result = CreateIssueResult(success=False, error="Invalid project")
        assert str(result) == "Error: Invalid project"


# ---------------------------------------------------------------------------
# EditIssueResult
# ---------------------------------------------------------------------------


class TestEditIssueResult:
    def test_success(self):
        result = EditIssueResult(success=True, issue_key="EX-1")
        assert result.success is True
        assert result.issue_key == "EX-1"

    def test_str_output(self):
        result = EditIssueResult(success=True, issue_key="EX-1")
        assert "EX-1 updated successfully" in str(result)

    def test_str_on_error(self):
        result = EditIssueResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# AssignIssueResult
# ---------------------------------------------------------------------------


class TestAssignIssueResult:
    def test_assigned(self):
        result = AssignIssueResult(success=True, issue_key="EX-1", assigned=True)
        assert "assigned to you" in str(result)

    def test_unassigned(self):
        result = AssignIssueResult(success=True, issue_key="EX-1", assigned=False)
        assert "unassigned" in str(result)

    def test_str_on_error(self):
        result = AssignIssueResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# AddCommentResult
# ---------------------------------------------------------------------------


class TestAddCommentResult:
    def test_success(self):
        result = AddCommentResult(success=True, issue_key="EX-1", comment_id="10000")
        assert result.comment_id == "10000"
        assert "10000" in str(result)
        assert "EX-1" in str(result)

    def test_str_on_error(self):
        result = AddCommentResult(success=False, error="Issue not found")
        assert str(result) == "Error: Issue not found"


# ---------------------------------------------------------------------------
# ListVersionsResult
# ---------------------------------------------------------------------------


class TestListVersionsResult:
    def test_parse_versions(self):
        data = _load_json("list_versions.json")
        from apron_tools.providers.atlassian.jira.types import VersionSummary

        versions = [VersionSummary.model_validate(v) for v in data["values"]]
        result = ListVersionsResult(success=True, versions=versions)

        assert result.success is True
        assert len(result.versions) == 2

    def test_version_fields(self):
        data = _load_json("list_versions.json")
        from apron_tools.providers.atlassian.jira.types import VersionSummary

        version = VersionSummary.model_validate(data["values"][0])

        assert version.id == "10000"
        assert version.name == "Version 1.0"
        assert version.released is True
        assert version.overdue is False
        assert version.start_date == "2024-01-01"
        assert version.release_date == "2024-03-01"

    def test_overdue_version(self):
        data = _load_json("list_versions.json")
        from apron_tools.providers.atlassian.jira.types import VersionSummary

        version = VersionSummary.model_validate(data["values"][1])

        assert version.released is False
        assert version.overdue is True

    def test_str_output(self):
        data = _load_json("list_versions.json")
        from apron_tools.providers.atlassian.jira.types import VersionSummary

        versions = [VersionSummary.model_validate(v) for v in data["values"]]
        result = ListVersionsResult(success=True, versions=versions)
        text = str(result)

        assert "2 version(s)" in text
        assert "Version 1.0" in text
        assert "released" in text
        assert "overdue" in text

    def test_str_on_error(self):
        result = ListVersionsResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_empty(self):
        result = ListVersionsResult(success=True, versions=[])
        assert str(result) == "No versions found."


# ---------------------------------------------------------------------------
# ListBoardsResult
# ---------------------------------------------------------------------------


class TestListBoardsResult:
    def test_parse_boards(self):
        data = _load_json("list_boards.json")
        from apron_tools.providers.atlassian.jira.types import BoardSummary

        boards = [BoardSummary.model_validate(b) for b in data["values"]]
        result = ListBoardsResult(success=True, boards=boards)

        assert result.success is True
        assert len(result.boards) == 2

    def test_board_fields(self):
        data = _load_json("list_boards.json")
        from apron_tools.providers.atlassian.jira.types import BoardSummary

        board = BoardSummary.model_validate(data["values"][0])

        assert board.id == 84
        assert board.name == "EX board"
        assert board.type == "scrum"

    def test_str_output(self):
        data = _load_json("list_boards.json")
        from apron_tools.providers.atlassian.jira.types import BoardSummary

        boards = [BoardSummary.model_validate(b) for b in data["values"]]
        result = ListBoardsResult(success=True, boards=boards)
        text = str(result)

        assert "2 board(s)" in text
        assert "EX board" in text
        assert "scrum" in text
        assert "kanban" in text

    def test_str_on_error(self):
        result = ListBoardsResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"

    def test_str_empty(self):
        result = ListBoardsResult(success=True, boards=[])
        assert str(result) == "No boards found."


# ---------------------------------------------------------------------------
# ListSprintsResult
# ---------------------------------------------------------------------------


class TestListSprintsResult:
    def test_parse_sprints(self):
        data = _load_json("list_sprints.json")
        from apron_tools.providers.atlassian.jira.types import SprintSummary

        sprints = [SprintSummary.model_validate(s) for s in data["values"]]
        result = ListSprintsResult(success=True, sprints=sprints)

        assert result.success is True
        assert len(result.sprints) == 2

    def test_sprint_fields(self):
        data = _load_json("list_sprints.json")
        from apron_tools.providers.atlassian.jira.types import SprintSummary

        sprint = SprintSummary.model_validate(data["values"][0])

        assert sprint.id == 37
        assert sprint.name == "Sprint 1"
        assert sprint.state == "closed"
        assert sprint.start_date == "2024-01-01T08:00:00.000Z"
        assert sprint.end_date == "2024-01-15T08:00:00.000Z"
        assert sprint.complete_date == "2024-01-14T12:00:00.000Z"
        assert sprint.goal == "Complete onboarding features"

    def test_active_sprint(self):
        data = _load_json("list_sprints.json")
        from apron_tools.providers.atlassian.jira.types import SprintSummary

        sprint = SprintSummary.model_validate(data["values"][1])

        assert sprint.state == "active"
        assert sprint.complete_date is None
        assert sprint.goal == "Fix critical bugs"

    def test_str_output(self):
        data = _load_json("list_sprints.json")
        from apron_tools.providers.atlassian.jira.types import SprintSummary

        sprints = [SprintSummary.model_validate(s) for s in data["values"]]
        result = ListSprintsResult(success=True, sprints=sprints)
        text = str(result)

        assert "2 sprint(s)" in text
        assert "Sprint 1" in text
        assert "closed" in text
        assert "active" in text
        assert "Complete onboarding features" in text

    def test_str_on_error(self):
        result = ListSprintsResult(success=False, error="Board not found")
        assert str(result) == "Error: Board not found"

    def test_str_empty(self):
        result = ListSprintsResult(success=True, sprints=[])
        assert str(result) == "No sprints found."
