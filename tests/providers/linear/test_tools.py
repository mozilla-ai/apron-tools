"""Tests for Linear tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.linear.tools import (
    create_issue,
    create_project,
    list_cycles,
    list_issues,
    list_projects,
    list_teams,
    list_users,
    read_issue,
    update_issue,
    update_project,
    whoami,
)
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
_TOKEN = "lin_api_test_token_abc123"
_BASE_URL = "https://api.linear.app/graphql"
_API_DOCS = "https://developers.linear.app/docs/graphql/working-with-the-graphql-api"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# whoami
# ---------------------------------------------------------------------------


class TestWhoami:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("whoami.json"), url=_BASE_URL)

        result = await whoami(WhoamiParams(), token=_TOKEN)

        assert isinstance(result, WhoamiResult)
        assert result.success is True
        assert result.name == "Alice Smith"
        assert result.email == "alice@example.com"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("whoami.json"))

        await whoami(WhoamiParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == _TOKEN

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await whoami(WhoamiParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "Entity not found" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = whoami._tool_definition
        assert defn.name == "whoami"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]
        assert defn.api_docs_url == _API_DOCS


# ---------------------------------------------------------------------------
# list_teams
# ---------------------------------------------------------------------------


class TestListTeams:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_teams.json"))

        result = await list_teams(ListTeamsParams(), token=_TOKEN)

        assert isinstance(result, ListTeamsResult)
        assert result.success is True
        assert len(result.teams) == 2
        assert result.teams[0].name == "Engineering"
        assert result.teams[0].key == "ENG"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_teams.json"))

        await list_teams(ListTeamsParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == _TOKEN

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await list_teams(ListTeamsParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = list_teams._tool_definition
        assert defn.name == "list_teams"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]
        assert defn.api_docs_url == _API_DOCS


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_users.json"))

        result = await list_users(ListUsersParams(), token=_TOKEN)

        assert isinstance(result, ListUsersResult)
        assert result.success is True
        assert len(result.users) == 2
        assert result.users[0].name == "Alice Smith"
        assert result.users[0].active is True

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await list_users(ListUsersParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = list_users._tool_definition
        assert defn.name == "list_users"
        assert defn.provider == "linear"
        assert "read" in defn.scopes
        assert "admin" in defn.scopes


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_issues.json"))

        result = await list_issues(ListIssuesParams(), token=_TOKEN)

        assert isinstance(result, ListIssuesResult)
        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].identifier == "ENG-123"
        assert result.issues[0].state is not None
        assert result.issues[0].state.name == "In Progress"

    async def test_with_filters(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_issues.json"))

        params = ListIssuesParams(team_id="team-001", state="In Progress")
        result = await list_issues(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "team" in body["query"]
        assert "state" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await list_issues(ListIssuesParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = list_issues._tool_definition
        assert defn.name == "list_issues"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# read_issue
# ---------------------------------------------------------------------------


class TestReadIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("read_issue.json"))

        result = await read_issue(ReadIssueParams(issue_id="issue-001"), token=_TOKEN)

        assert isinstance(result, ReadIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-123"
        assert result.issue.priority_label == "Urgent"
        assert len(result.issue.labels) == 1
        assert result.issue.labels[0].name == "bug"
        assert result.issue.project is not None
        assert result.issue.project.name == "Q1 Sprint"
        assert len(result.issue.comments) == 1

    async def test_sends_issue_id_variable(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("read_issue.json"))

        await read_issue(ReadIssueParams(issue_id="issue-001"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["variables"]["id"] == "issue-001"

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await read_issue(ReadIssueParams(issue_id="missing"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "Entity not found" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = read_issue._tool_definition
        assert defn.name == "read_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_issue.json"))

        params = CreateIssueParams(title="New issue", team_id="team-001")
        result = await create_issue(params, token=_TOKEN)

        assert isinstance(result, CreateIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-124"

    async def test_sends_input_variables(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_issue.json"))

        params = CreateIssueParams(
            title="New issue",
            team_id="team-001",
            description="Details",
            priority=2,
        )
        await create_issue(params, token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        input_data = body["variables"]["input"]
        assert input_data["title"] == "New issue"
        assert input_data["teamId"] == "team-001"
        assert input_data["description"] == "Details"
        assert input_data["priority"] == 2

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = CreateIssueParams(title="Fail", team_id="team-001")
        result = await create_issue(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = create_issue._tool_definition
        assert defn.name == "create_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("update_issue.json"))

        params = UpdateIssueParams(issue_id="issue-001", title="Updated title")
        result = await update_issue(params, token=_TOKEN)

        assert isinstance(result, UpdateIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-123"

    async def test_no_fields_returns_error(self) -> None:
        params = UpdateIssueParams(issue_id="issue-001")
        result = await update_issue(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "No fields" in result.error

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = UpdateIssueParams(issue_id="issue-001", title="Fail")
        result = await update_issue(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = update_issue._tool_definition
        assert defn.name == "update_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


class TestListProjects:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_projects.json"))

        result = await list_projects(ListProjectsParams(), token=_TOKEN)

        assert isinstance(result, ListProjectsResult)
        assert result.success is True
        assert len(result.projects) == 1
        assert result.projects[0].name == "Q1 Sprint"
        assert result.projects[0].progress == 0.45
        assert len(result.projects[0].teams) == 1

    async def test_with_team_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_projects.json"))

        params = ListProjectsParams(team_id="team-001")
        result = await list_projects(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "accessibleTeams" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await list_projects(ListProjectsParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = list_projects._tool_definition
        assert defn.name == "list_projects"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------


class TestCreateProject:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_project.json"))

        params = CreateProjectParams(name="New Project", team_ids=["team-001"])
        result = await create_project(params, token=_TOKEN)

        assert isinstance(result, CreateProjectResult)
        assert result.success is True
        assert result.project is not None
        assert result.project.name == "New Project"

    async def test_sends_input_variables(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_project.json"))

        params = CreateProjectParams(
            name="New Project",
            team_ids=["team-001"],
            description="A project",
            state="planned",
        )
        await create_project(params, token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        input_data = body["variables"]["input"]
        assert input_data["name"] == "New Project"
        assert input_data["teamIds"] == ["team-001"]
        assert input_data["description"] == "A project"
        assert input_data["state"] == "planned"

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = CreateProjectParams(name="Fail", team_ids=["team-001"])
        result = await create_project(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = create_project._tool_definition
        assert defn.name == "create_project"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# update_project
# ---------------------------------------------------------------------------


class TestUpdateProject:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("update_project.json"))

        params = UpdateProjectParams(project_id="project-001", name="Updated name")
        result = await update_project(params, token=_TOKEN)

        assert isinstance(result, UpdateProjectResult)
        assert result.success is True
        assert result.project is not None

    async def test_no_fields_returns_error(self) -> None:
        params = UpdateProjectParams(project_id="project-001")
        result = await update_project(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "No fields" in result.error

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = UpdateProjectParams(project_id="project-001", name="Fail")
        result = await update_project(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = update_project._tool_definition
        assert defn.name == "update_project"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# list_cycles
# ---------------------------------------------------------------------------


class TestListCycles:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_cycles.json"))

        result = await list_cycles(ListCyclesParams(), token=_TOKEN)

        assert isinstance(result, ListCyclesResult)
        assert result.success is True
        assert len(result.cycles) == 1
        assert result.cycles[0].name == "Sprint 5"
        assert result.cycles[0].progress == 0.3

    async def test_with_team_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_cycles.json"))

        params = ListCyclesParams(team_id="team-001")
        result = await list_cycles(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "team" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await list_cycles(ListCyclesParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = list_cycles._tool_definition
        assert defn.name == "list_cycles"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]
