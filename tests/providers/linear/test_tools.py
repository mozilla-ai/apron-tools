"""Tests for Linear tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.linear.tools import (
    linear_create_issue,
    linear_create_project,
    linear_list_cycles,
    linear_list_issues,
    linear_list_projects,
    linear_list_teams,
    linear_list_users,
    linear_read_issue,
    linear_update_issue,
    linear_update_project,
    linear_upload_file_to_issue,
    linear_whoami,
)
from apron_tools.providers.linear.types import (
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
    UploadFileToIssueParams,
    UploadFileToIssueResult,
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

        result = await linear_whoami(WhoamiParams(), token=_TOKEN)

        assert isinstance(result, WhoamiResult)
        assert result.success is True
        assert result.name == "Alice Smith"
        assert result.email == "alice@example.com"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("whoami.json"))

        await linear_whoami(WhoamiParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == _TOKEN

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_whoami(WhoamiParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "Entity not found" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = linear_whoami._tool_definition
        assert defn.name == "linear_whoami"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]
        assert defn.api_docs_url == _API_DOCS


# ---------------------------------------------------------------------------
# list_teams
# ---------------------------------------------------------------------------


class TestListTeams:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_teams.json"))

        result = await linear_list_teams(ListTeamsParams(), token=_TOKEN)

        assert isinstance(result, ListTeamsResult)
        assert result.success is True
        assert len(result.teams) == 2
        assert result.teams[0].name == "Engineering"
        assert result.teams[0].key == "ENG"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_teams.json"))

        await linear_list_teams(ListTeamsParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == _TOKEN

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_list_teams(ListTeamsParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = linear_list_teams._tool_definition
        assert defn.name == "linear_list_teams"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]
        assert defn.api_docs_url == _API_DOCS


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_users.json"))

        result = await linear_list_users(ListUsersParams(), token=_TOKEN)

        assert isinstance(result, ListUsersResult)
        assert result.success is True
        assert len(result.users) == 2
        assert result.users[0].name == "Alice Smith"
        assert result.users[0].active is True

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_list_users(ListUsersParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_list_users._tool_definition
        assert defn.name == "linear_list_users"
        assert defn.provider == "linear"
        assert "read" in defn.scopes
        assert "admin" in defn.scopes


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------


class TestListIssues:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_issues.json"))

        result = await linear_list_issues(ListIssuesParams(), token=_TOKEN)

        assert isinstance(result, ListIssuesResult)
        assert result.success is True
        assert len(result.issues) == 1
        assert result.issues[0].identifier == "ENG-123"
        assert result.issues[0].state is not None
        assert result.issues[0].state.name == "In Progress"

    async def test_with_filters(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_issues.json"))

        params = ListIssuesParams(team_id="team-001", state="In Progress")
        result = await linear_list_issues(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "team" in body["query"]
        assert "state" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_list_issues(ListIssuesParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_list_issues._tool_definition
        assert defn.name == "linear_list_issues"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# read_issue
# ---------------------------------------------------------------------------


class TestReadIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("read_issue.json"))

        result = await linear_read_issue(ReadIssueParams(issue_id="issue-001"), token=_TOKEN)

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

        await linear_read_issue(ReadIssueParams(issue_id="issue-001"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["variables"]["id"] == "issue-001"

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_read_issue(ReadIssueParams(issue_id="missing"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "Entity not found" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = linear_read_issue._tool_definition
        assert defn.name == "linear_read_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------


class TestCreateIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_issue.json"))

        params = CreateIssueParams(title="New issue", team_id="team-001")
        result = await linear_create_issue(params, token=_TOKEN)

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
        await linear_create_issue(params, token=_TOKEN)

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
        result = await linear_create_issue(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_create_issue._tool_definition
        assert defn.name == "linear_create_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# update_issue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("update_issue.json"))

        params = UpdateIssueParams(issue_id="issue-001", title="Updated title")
        result = await linear_update_issue(params, token=_TOKEN)

        assert isinstance(result, UpdateIssueResult)
        assert result.success is True
        assert result.issue is not None
        assert result.issue.identifier == "ENG-123"

    async def test_no_fields_returns_error(self) -> None:
        params = UpdateIssueParams(issue_id="issue-001")
        result = await linear_update_issue(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "No fields" in result.error

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = UpdateIssueParams(issue_id="issue-001", title="Fail")
        result = await linear_update_issue(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_update_issue._tool_definition
        assert defn.name == "linear_update_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


class TestListProjects:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_projects.json"))

        result = await linear_list_projects(ListProjectsParams(), token=_TOKEN)

        assert isinstance(result, ListProjectsResult)
        assert result.success is True
        assert len(result.projects) == 1
        assert result.projects[0].name == "Q1 Sprint"
        assert result.projects[0].progress == 0.45
        assert len(result.projects[0].teams) == 1

    async def test_with_team_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_projects.json"))

        params = ListProjectsParams(team_id="team-001")
        result = await linear_list_projects(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "accessibleTeams" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_list_projects(ListProjectsParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_list_projects._tool_definition
        assert defn.name == "linear_list_projects"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------


class TestCreateProject:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_project.json"))

        params = CreateProjectParams(name="New Project", team_ids=["team-001"])
        result = await linear_create_project(params, token=_TOKEN)

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
        await linear_create_project(params, token=_TOKEN)

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
        result = await linear_create_project(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_create_project._tool_definition
        assert defn.name == "linear_create_project"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# update_project
# ---------------------------------------------------------------------------


class TestUpdateProject:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("update_project.json"))

        params = UpdateProjectParams(project_id="project-001", name="Updated name")
        result = await linear_update_project(params, token=_TOKEN)

        assert isinstance(result, UpdateProjectResult)
        assert result.success is True
        assert result.project is not None

    async def test_no_fields_returns_error(self) -> None:
        params = UpdateProjectParams(project_id="project-001")
        result = await linear_update_project(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "No fields" in result.error

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        params = UpdateProjectParams(project_id="project-001", name="Fail")
        result = await linear_update_project(params, token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_update_project._tool_definition
        assert defn.name == "linear_update_project"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]


# ---------------------------------------------------------------------------
# list_cycles
# ---------------------------------------------------------------------------


class TestListCycles:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_cycles.json"))

        result = await linear_list_cycles(ListCyclesParams(), token=_TOKEN)

        assert isinstance(result, ListCyclesResult)
        assert result.success is True
        assert len(result.cycles) == 1
        assert result.cycles[0].name == "Sprint 5"
        assert result.cycles[0].progress == 0.3

    async def test_with_team_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_cycles.json"))

        params = ListCyclesParams(team_id="team-001")
        result = await linear_list_cycles(params, token=_TOKEN)

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "team" in body["query"]

    async def test_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("error.json"))

        result = await linear_list_cycles(ListCyclesParams(), token=_TOKEN)

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = linear_list_cycles._tool_definition
        assert defn.name == "linear_list_cycles"
        assert defn.provider == "linear"
        assert defn.scopes == ["read"]


# ---------------------------------------------------------------------------
# upload_file_to_issue
# ---------------------------------------------------------------------------


class TestUploadFileToIssue:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        file_content = b"hello world"
        b64 = base64.b64encode(file_content).decode()

        # Step 1: fileUpload mutation response.
        httpx_mock.add_response(json=_load_json("file_upload.json"))
        # Step 2: PUT to presigned URL.
        httpx_mock.add_response(status_code=200)
        # Step 3: attachmentCreate mutation response.
        httpx_mock.add_response(json=_load_json("attachment_create.json"))

        params = UploadFileToIssueParams(
            issue_id="issue-001",
            file=FileFromBytes(data=b64, filename="notes.txt", mime_type="text/plain"),
        )
        result = await linear_upload_file_to_issue(params, token=_TOKEN)

        assert isinstance(result, UploadFileToIssueResult)
        assert result.success is True
        assert result.attachment_id == "attachment-001"
        assert result.asset_url == "https://uploads.linear.app/asset-001.txt"
        assert result.filename == "notes.txt"
        assert "notes.txt" in str(result)

        # Verify the PUT request used the presigned URL and headers.
        requests = httpx_mock.get_requests()
        put_req = requests[1]
        assert put_req.method == "PUT"
        assert str(put_req.url) == "https://uploads.linear.app/presigned-url"
        assert put_req.headers["x-amz-acl"] == "public-read"
        assert put_req.headers["Content-Type"] == "text/plain"
        assert put_req.content == file_content

    async def test_file_upload_graphql_error(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        httpx_mock.add_response(json=_load_json("error.json"))

        params = UploadFileToIssueParams(
            issue_id="issue-001",
            file=FileFromBytes(
                data=base64.b64encode(b"data").decode(),
                filename="f.txt",
                mime_type="text/plain",
            ),
        )
        result = await linear_upload_file_to_issue(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None

    async def test_presigned_put_failure(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        # Step 1 succeeds.
        httpx_mock.add_response(json=_load_json("file_upload.json"))
        # Step 2: PUT fails.
        httpx_mock.add_response(status_code=403)

        params = UploadFileToIssueParams(
            issue_id="issue-001",
            file=FileFromBytes(
                data=base64.b64encode(b"data").decode(),
                filename="f.txt",
                mime_type="text/plain",
            ),
        )
        result = await linear_upload_file_to_issue(params, token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_attachment_create_error(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        # Steps 1 and 2 succeed.
        httpx_mock.add_response(json=_load_json("file_upload.json"))
        httpx_mock.add_response(status_code=200)
        # Step 3: attachmentCreate fails.
        httpx_mock.add_response(json=_load_json("error.json"))

        params = UploadFileToIssueParams(
            issue_id="issue-001",
            file=FileFromBytes(
                data=base64.b64encode(b"data").decode(),
                filename="f.txt",
                mime_type="text/plain",
            ),
        )
        result = await linear_upload_file_to_issue(params, token=_TOKEN)

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = linear_upload_file_to_issue._tool_definition
        assert defn.name == "linear_upload_file_to_issue"
        assert defn.provider == "linear"
        assert defn.scopes == ["write"]
