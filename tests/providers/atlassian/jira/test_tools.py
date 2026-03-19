"""Tests for Atlassian Jira tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.atlassian.jira.tools import (
    atlassian_jira_add_comment,
    atlassian_jira_assign_issue,
    atlassian_jira_create_issue,
    atlassian_jira_edit_issue,
    atlassian_jira_explore_issues,
    atlassian_jira_explore_projects,
    atlassian_jira_list_boards,
    atlassian_jira_list_sprints,
    atlassian_jira_list_versions,
)
from any_tool.providers.atlassian.jira.types import (
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
    ListBoardsParams,
    ListBoardsResult,
    ListSprintsParams,
    ListSprintsResult,
    ListVersionsParams,
    ListVersionsResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_BASE = "https://api.atlassian.com"
_CLOUD_ID = "1324a887-45db-1bf4-1e99-ef0ff456d421"
_API_PREFIX = f"{_BASE}/ex/jira/{_CLOUD_ID}/rest/api/3"
_AGILE_PREFIX = f"{_BASE}/ex/jira/{_CLOUD_ID}/rest/agile/1.0"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


def _mock_cloud_id(httpx_mock: HTTPXMock) -> None:
    """Register the accessible-resources response that resolves the cloud ID."""
    httpx_mock.add_response(
        url=f"{_BASE}/oauth/token/accessible-resources",
        json=_load_json("accessible_resources.json"),
    )


# ---------------------------------------------------------------------------
# explore_projects
# ---------------------------------------------------------------------------


class TestExploreProjects:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/project/search?maxResults=50",
            json=_load_json("project_search.json"),
        )

        result = await atlassian_jira_explore_projects(ExploreProjectsParams(), token=_TOKEN)

        assert isinstance(result, ExploreProjectsResult)
        assert result.success is True
        assert len(result.projects) == 2
        assert result.projects[0].key == "EX"
        assert result.projects[0].name == "Example"

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            json=[],
        )

        result = await atlassian_jira_explore_projects(ExploreProjectsParams(), token=_TOKEN)

        assert result.success is False
        assert "cloud ID" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await atlassian_jira_explore_projects(ExploreProjectsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_explore_projects._tool_definition
        assert defn.name == "atlassian_jira_explore_projects"
        assert defn.provider == "atlassian_jira"
        assert "read:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# explore_issues
# ---------------------------------------------------------------------------


class TestExploreIssues:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/search/jql",
            json=_load_json("search_issues.json"),
        )

        result = await atlassian_jira_explore_issues(
            ExploreIssuesParams(project_key="EX"),
            token=_TOKEN,
        )

        assert isinstance(result, ExploreIssuesResult)
        assert result.success is True
        assert result.total == 2
        assert result.project_key == "EX"
        assert result.issues[0].key == "EX-1"

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            status_code=401,
            text="Unauthorized",
        )

        result = await atlassian_jira_explore_issues(
            ExploreIssuesParams(project_key="EX"),
            token=_TOKEN,
        )

        assert result.success is False

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await atlassian_jira_explore_issues(
            ExploreIssuesParams(project_key="EX"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_explore_issues._tool_definition
        assert defn.name == "atlassian_jira_explore_issues"
        assert defn.provider == "atlassian_jira"
        assert "read:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/issue",
            json=_load_json("create_issue.json"),
            status_code=201,
        )

        result = await atlassian_jira_create_issue(
            CreateIssueParams(project_key="EX", summary="New task"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateIssueResult)
        assert result.success is True
        assert result.key == "EX-3"
        assert result.id == "10000"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            status_code=400,
            text='{"errorMessages":["Project not found"]}',
        )

        result = await atlassian_jira_create_issue(
            CreateIssueParams(project_key="NOPE", summary="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_create_issue._tool_definition
        assert defn.name == "atlassian_jira_create_issue"
        assert defn.provider == "atlassian_jira"
        assert "write:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# edit_issue
# ---------------------------------------------------------------------------


class TestEditIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/issue/EX-1",
            status_code=204,
        )

        result = await atlassian_jira_edit_issue(
            EditIssueParams(issue_key="EX-1", summary="Updated title"),
            token=_TOKEN,
        )

        assert isinstance(result, EditIssueResult)
        assert result.success is True
        assert result.issue_key == "EX-1"

    async def test_no_changes(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)

        result = await atlassian_jira_edit_issue(
            EditIssueParams(issue_key="EX-1"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "No changes" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await atlassian_jira_edit_issue(
            EditIssueParams(issue_key="EX-999", summary="Nope"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_edit_issue._tool_definition
        assert defn.name == "atlassian_jira_edit_issue"
        assert defn.provider == "atlassian_jira"
        assert "write:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# assign_issue
# ---------------------------------------------------------------------------


class TestAssignIssue:
    async def test_assign_to_me(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/myself",
            json=_load_json("myself.json"),
        )
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/issue/EX-1/assignee",
            status_code=204,
        )

        result = await atlassian_jira_assign_issue(
            AssignIssueParams(issue_key="EX-1"),
            token=_TOKEN,
        )

        assert isinstance(result, AssignIssueResult)
        assert result.success is True
        assert result.assigned is True

    async def test_unassign(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/issue/EX-1/assignee",
            status_code=204,
        )

        result = await atlassian_jira_assign_issue(
            AssignIssueParams(issue_key="EX-1", assign_to_me=False),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.assigned is False

    async def test_myself_failure(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/myself",
            status_code=401,
            text="Unauthorized",
        )

        result = await atlassian_jira_assign_issue(
            AssignIssueParams(issue_key="EX-1"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "account ID" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_assign_issue._tool_definition
        assert defn.name == "atlassian_jira_assign_issue"
        assert defn.provider == "atlassian_jira"
        assert "write:jira-work" in defn.scopes
        assert "read:jira-user" in defn.scopes


# ---------------------------------------------------------------------------
# add_comment
# ---------------------------------------------------------------------------


class TestAddComment:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/issue/EX-1/comment",
            json=_load_json("add_comment.json"),
            status_code=201,
        )

        result = await atlassian_jira_add_comment(
            AddCommentParams(issue_key="EX-1", comment="Looks good"),
            token=_TOKEN,
        )

        assert isinstance(result, AddCommentResult)
        assert result.success is True
        assert result.comment_id == "10000"
        assert result.issue_key == "EX-1"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await atlassian_jira_add_comment(
            AddCommentParams(issue_key="EX-999", comment="Hi"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_add_comment._tool_definition
        assert defn.name == "atlassian_jira_add_comment"
        assert defn.provider == "atlassian_jira"
        assert "write:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------


class TestListVersions:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_PREFIX}/project/EX/version",
            json=_load_json("list_versions.json"),
        )

        result = await atlassian_jira_list_versions(
            ListVersionsParams(project_key="EX"),
            token=_TOKEN,
        )

        assert isinstance(result, ListVersionsResult)
        assert result.success is True
        assert len(result.versions) == 2
        assert result.versions[0].name == "Version 1.0"
        assert result.versions[0].released is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Project not found")

        result = await atlassian_jira_list_versions(
            ListVersionsParams(project_key="NOPE"),
            token=_TOKEN,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_list_versions._tool_definition
        assert defn.name == "atlassian_jira_list_versions"
        assert defn.provider == "atlassian_jira"
        assert "read:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# list_boards
# ---------------------------------------------------------------------------


class TestListBoards:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_AGILE_PREFIX}/board",
            json=_load_json("list_boards.json"),
        )

        result = await atlassian_jira_list_boards(
            ListBoardsParams(),
            token=_TOKEN,
        )

        assert isinstance(result, ListBoardsResult)
        assert result.success is True
        assert len(result.boards) == 2
        assert result.boards[0].name == "EX board"
        assert result.boards[0].type == "scrum"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await atlassian_jira_list_boards(ListBoardsParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_list_boards._tool_definition
        assert defn.name == "atlassian_jira_list_boards"
        assert defn.provider == "atlassian_jira"
        assert "read:jira-work" in defn.scopes


# ---------------------------------------------------------------------------
# list_sprints
# ---------------------------------------------------------------------------


class TestListSprints:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_AGILE_PREFIX}/board/84/sprint",
            json=_load_json("list_sprints.json"),
        )

        result = await atlassian_jira_list_sprints(
            ListSprintsParams(board_id=84),
            token=_TOKEN,
        )

        assert isinstance(result, ListSprintsResult)
        assert result.success is True
        assert len(result.sprints) == 2
        assert result.sprints[0].name == "Sprint 1"
        assert result.sprints[0].state == "closed"
        assert result.sprints[1].state == "active"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Board not found")

        result = await atlassian_jira_list_sprints(
            ListSprintsParams(board_id=999),
            token=_TOKEN,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_jira_list_sprints._tool_definition
        assert defn.name == "atlassian_jira_list_sprints"
        assert defn.provider == "atlassian_jira"
        assert "read:jira-work" in defn.scopes
