"""Linear tool functions for interacting with the Linear GraphQL API."""

from __future__ import annotations

from typing import Any

import httpx

from apron_tools.fileio import resolve_file_input
from apron_tools.providers.linear.types import (
    CreateIssueParams,
    CreateIssueResult,
    CreateProjectParams,
    CreateProjectResult,
    CycleDetail,
    IssueDetail,
    IssueSummary,
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
    MutationIssue,
    MutationProject,
    ProjectDetail,
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
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.linear.app/graphql"
_TIMEOUT = 30.0
_API_DOCS = "https://developers.linear.app/docs/graphql/working-with-the-graphql-api"


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers for a Linear API request."""
    return {
        "Authorization": token,
        "Content-Type": "application/json",
    }


async def _execute_graphql(
    query: str,
    variables: dict[str, Any] | None,
    token: str,
    base_url: str,
) -> dict[str, Any]:
    """Execute a GraphQL query against the Linear API and return the raw response."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            base_url,
            headers=_headers(token),
            json=payload,
        )

    return response.json()


def _extract_error(data: dict[str, Any]) -> str | None:
    """Extract the first error message from a GraphQL response, if present."""
    errors = data.get("errors")
    if errors:
        return errors[0].get("message", "Unknown error") if errors else "Unknown error"
    return None


# ---------------------------------------------------------------------------
# whoami
# ---------------------------------------------------------------------------

_WHOAMI_QUERY = """
query {
    viewer {
        id
        name
        email
        displayName
    }
}
"""


@tool(scopes=SCOPES["linear_whoami"], api_docs=_API_DOCS, provider="linear")
async def linear_whoami(
    params: WhoamiParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> WhoamiResult:
    """Get information about the currently authenticated Linear user."""
    try:
        data = await _execute_graphql(_WHOAMI_QUERY, None, token, base_url)
    except httpx.HTTPError as exc:
        return WhoamiResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return WhoamiResult(success=False, error=error)

    viewer = data.get("data", {}).get("viewer")
    if not viewer:
        return WhoamiResult(success=False, error="No viewer data returned")

    return WhoamiResult.model_validate(viewer)


# ---------------------------------------------------------------------------
# list_teams
# ---------------------------------------------------------------------------

_LIST_TEAMS_QUERY = """
query {
    teams {
        nodes {
            id
            name
            key
            description
        }
    }
}
"""


@tool(scopes=SCOPES["linear_list_teams"], api_docs=_API_DOCS, provider="linear")
async def linear_list_teams(
    params: ListTeamsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListTeamsResult:
    """List all teams in the Linear workspace."""
    try:
        data = await _execute_graphql(_LIST_TEAMS_QUERY, None, token, base_url)
    except httpx.HTTPError as exc:
        return ListTeamsResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ListTeamsResult(success=False, error=error)

    nodes = data.get("data", {}).get("teams", {}).get("nodes", [])
    return ListTeamsResult(success=True, teams=nodes)


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

_LIST_USERS_QUERY = """
query {
    users {
        nodes {
            id
            name
            email
            displayName
            active
        }
    }
}
"""


@tool(scopes=SCOPES["linear_list_users"], api_docs=_API_DOCS, provider="linear")
async def linear_list_users(
    params: ListUsersParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListUsersResult:
    """List all users in the Linear workspace."""
    try:
        data = await _execute_graphql(_LIST_USERS_QUERY, None, token, base_url)
    except httpx.HTTPError as exc:
        return ListUsersResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ListUsersResult(success=False, error=error)

    nodes = data.get("data", {}).get("users", {}).get("nodes", [])
    return ListUsersResult(success=True, users=nodes)


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------


def _build_list_issues_query(params: ListIssuesParams) -> str:
    """Build the GraphQL query string for listing issues with inline filters."""
    filter_parts: list[str] = []
    if params.team_id:
        filter_parts.append(f'team: {{ id: {{ eq: "{params.team_id}" }} }}')
    if params.assignee_id:
        filter_parts.append(f'assignee: {{ id: {{ eq: "{params.assignee_id}" }} }}')
    if params.state:
        filter_parts.append(f'state: {{ name: {{ eq: "{params.state}" }} }}')
    if params.project_id:
        filter_parts.append(f'project: {{ id: {{ eq: "{params.project_id}" }} }}')
    if params.created_after:
        filter_parts.append(f'createdAt: {{ gte: "{params.created_after}" }}')
    if params.updated_after:
        filter_parts.append(f'updatedAt: {{ gte: "{params.updated_after}" }}')

    filter_str = ", ".join(filter_parts)
    filter_arg = f", filter: {{ {filter_str} }}" if filter_str else ""

    return f"""
    query {{
        issues(first: {params.limit}{filter_arg}) {{
            nodes {{
                id
                identifier
                title
                description
                priority
                state {{
                    id
                    name
                    type
                }}
                assignee {{
                    id
                    name
                }}
                team {{
                    id
                    name
                }}
                createdAt
                updatedAt
            }}
        }}
    }}
    """


@tool(scopes=SCOPES["linear_list_issues"], api_docs=_API_DOCS, provider="linear")
async def linear_list_issues(
    params: ListIssuesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListIssuesResult:
    """List issues from Linear with optional filters."""
    query = _build_list_issues_query(params)

    try:
        data = await _execute_graphql(query, None, token, base_url)
    except httpx.HTTPError as exc:
        return ListIssuesResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ListIssuesResult(success=False, error=error)

    nodes = data.get("data", {}).get("issues", {}).get("nodes", [])
    issues = [IssueSummary.model_validate(n) for n in nodes]
    return ListIssuesResult(success=True, issues=issues)


# ---------------------------------------------------------------------------
# read_issue
# ---------------------------------------------------------------------------

_READ_ISSUE_QUERY = """
query($id: String!) {
    issue(id: $id) {
        id
        identifier
        title
        description
        priority
        priorityLabel
        estimate
        state {
            id
            name
            type
        }
        assignee {
            id
            name
        }
        team {
            id
            name
        }
        labels {
            nodes {
                id
                name
            }
        }
        project {
            id
            name
        }
        cycle {
            id
            name
        }
        comments {
            nodes {
                body
                user {
                    id
                    name
                }
                createdAt
            }
        }
        createdAt
        updatedAt
        url
    }
}
"""


@tool(scopes=SCOPES["linear_read_issue"], api_docs=_API_DOCS, provider="linear")
async def linear_read_issue(
    params: ReadIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ReadIssueResult:
    """Read the details of a specific Linear issue."""
    try:
        data = await _execute_graphql(_READ_ISSUE_QUERY, {"id": params.issue_id}, token, base_url)
    except httpx.HTTPError as exc:
        return ReadIssueResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ReadIssueResult(success=False, error=error)

    issue_data = data.get("data", {}).get("issue")
    if not issue_data:
        return ReadIssueResult(success=False, error="Issue not found")

    # Flatten nested connection fields for model validation.
    if "labels" in issue_data and isinstance(issue_data["labels"], dict):
        issue_data["labels"] = issue_data["labels"].get("nodes", [])
    if "comments" in issue_data and isinstance(issue_data["comments"], dict):
        issue_data["comments"] = issue_data["comments"].get("nodes", [])

    issue = IssueDetail.model_validate(issue_data)
    return ReadIssueResult(success=True, issue=issue)


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------

_CREATE_ISSUE_MUTATION = """
mutation($input: IssueCreateInput!) {
    issueCreate(input: $input) {
        success
        issue {
            id
            identifier
            title
            url
        }
    }
}
"""


@tool(scopes=SCOPES["linear_create_issue"], api_docs=_API_DOCS, provider="linear")
async def linear_create_issue(
    params: CreateIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateIssueResult:
    """Create a new issue in Linear."""
    input_data: dict[str, Any] = {
        "title": params.title,
        "teamId": params.team_id,
    }
    if params.description is not None:
        input_data["description"] = params.description
    if params.project_id is not None:
        input_data["projectId"] = params.project_id
    if params.assignee_id is not None:
        input_data["assigneeId"] = params.assignee_id
    if params.priority is not None:
        input_data["priority"] = params.priority
    if params.state_id is not None:
        input_data["stateId"] = params.state_id

    try:
        data = await _execute_graphql(_CREATE_ISSUE_MUTATION, {"input": input_data}, token, base_url)
    except httpx.HTTPError as exc:
        return CreateIssueResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return CreateIssueResult(success=False, error=error)

    result = data.get("data", {}).get("issueCreate", {})
    if not result.get("success"):
        return CreateIssueResult(success=False, error="Mutation returned success=false")

    issue_data = result.get("issue")
    issue = MutationIssue.model_validate(issue_data) if issue_data else None
    return CreateIssueResult(success=True, issue=issue)


# ---------------------------------------------------------------------------
# update_issue
# ---------------------------------------------------------------------------

_UPDATE_ISSUE_MUTATION = """
mutation($id: String!, $input: IssueUpdateInput!) {
    issueUpdate(id: $id, input: $input) {
        success
        issue {
            id
            identifier
            title
        }
    }
}
"""


@tool(scopes=SCOPES["linear_update_issue"], api_docs=_API_DOCS, provider="linear")
async def linear_update_issue(
    params: UpdateIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateIssueResult:
    """Update an existing Linear issue."""
    input_data: dict[str, Any] = {}
    if params.title is not None:
        input_data["title"] = params.title
    if params.description is not None:
        input_data["description"] = params.description
    if params.state_id is not None:
        input_data["stateId"] = params.state_id
    if params.assignee_id is not None:
        input_data["assigneeId"] = params.assignee_id
    if params.priority is not None:
        input_data["priority"] = params.priority
    if params.project_id is not None:
        input_data["projectId"] = params.project_id

    if not input_data:
        return UpdateIssueResult(success=False, error="No fields provided to update")

    try:
        data = await _execute_graphql(
            _UPDATE_ISSUE_MUTATION,
            {"id": params.issue_id, "input": input_data},
            token,
            base_url,
        )
    except httpx.HTTPError as exc:
        return UpdateIssueResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return UpdateIssueResult(success=False, error=error)

    result = data.get("data", {}).get("issueUpdate", {})
    if not result.get("success"):
        return UpdateIssueResult(success=False, error="Mutation returned success=false")

    issue_data = result.get("issue")
    issue = MutationIssue.model_validate(issue_data) if issue_data else None
    return UpdateIssueResult(success=True, issue=issue)


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


def _build_list_projects_query(params: ListProjectsParams) -> str:
    """Build the GraphQL query string for listing projects."""
    filter_arg = ""
    if params.team_id:
        filter_arg = f', filter: {{ accessibleTeams: {{ id: {{ eq: "{params.team_id}" }} }} }}'

    return f"""
    query {{
        projects(first: 50{filter_arg}) {{
            nodes {{
                id
                name
                description
                state
                progress
                startDate
                targetDate
                teams {{
                    nodes {{
                        id
                        name
                    }}
                }}
                createdAt
                updatedAt
            }}
        }}
    }}
    """


@tool(scopes=SCOPES["linear_list_projects"], api_docs=_API_DOCS, provider="linear")
async def linear_list_projects(
    params: ListProjectsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListProjectsResult:
    """List projects from Linear."""
    query = _build_list_projects_query(params)

    try:
        data = await _execute_graphql(query, None, token, base_url)
    except httpx.HTTPError as exc:
        return ListProjectsResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ListProjectsResult(success=False, error=error)

    nodes = data.get("data", {}).get("projects", {}).get("nodes", [])
    projects: list[ProjectDetail] = []
    for node in nodes:
        # Flatten teams connection.
        if "teams" in node and isinstance(node["teams"], dict):
            node["teams"] = node["teams"].get("nodes", [])
        projects.append(ProjectDetail.model_validate(node))
    return ListProjectsResult(success=True, projects=projects)


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

_CREATE_PROJECT_MUTATION = """
mutation($input: ProjectCreateInput!) {
    projectCreate(input: $input) {
        success
        project {
            id
            name
            url
        }
    }
}
"""


@tool(scopes=SCOPES["linear_create_project"], api_docs=_API_DOCS, provider="linear")
async def linear_create_project(
    params: CreateProjectParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateProjectResult:
    """Create a new project in Linear."""
    input_data: dict[str, Any] = {
        "name": params.name,
        "teamIds": params.team_ids,
    }
    if params.description is not None:
        input_data["description"] = params.description
    if params.lead_id is not None:
        input_data["leadId"] = params.lead_id
    if params.state is not None:
        input_data["state"] = params.state

    try:
        data = await _execute_graphql(_CREATE_PROJECT_MUTATION, {"input": input_data}, token, base_url)
    except httpx.HTTPError as exc:
        return CreateProjectResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return CreateProjectResult(success=False, error=error)

    result = data.get("data", {}).get("projectCreate", {})
    if not result.get("success"):
        return CreateProjectResult(success=False, error="Mutation returned success=false")

    project_data = result.get("project")
    project = MutationProject.model_validate(project_data) if project_data else None
    return CreateProjectResult(success=True, project=project)


# ---------------------------------------------------------------------------
# update_project
# ---------------------------------------------------------------------------

_UPDATE_PROJECT_MUTATION = """
mutation($id: String!, $input: ProjectUpdateInput!) {
    projectUpdate(id: $id, input: $input) {
        success
        project {
            id
            name
        }
    }
}
"""


@tool(scopes=SCOPES["linear_update_project"], api_docs=_API_DOCS, provider="linear")
async def linear_update_project(
    params: UpdateProjectParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateProjectResult:
    """Update an existing Linear project."""
    input_data: dict[str, Any] = {}
    if params.name is not None:
        input_data["name"] = params.name
    if params.description is not None:
        input_data["description"] = params.description
    if params.lead_id is not None:
        input_data["leadId"] = params.lead_id
    if params.state is not None:
        input_data["state"] = params.state

    if not input_data:
        return UpdateProjectResult(success=False, error="No fields provided to update")

    try:
        data = await _execute_graphql(
            _UPDATE_PROJECT_MUTATION,
            {"id": params.project_id, "input": input_data},
            token,
            base_url,
        )
    except httpx.HTTPError as exc:
        return UpdateProjectResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return UpdateProjectResult(success=False, error=error)

    result = data.get("data", {}).get("projectUpdate", {})
    if not result.get("success"):
        return UpdateProjectResult(success=False, error="Mutation returned success=false")

    project_data = result.get("project")
    project = MutationProject.model_validate(project_data) if project_data else None
    return UpdateProjectResult(success=True, project=project)


# ---------------------------------------------------------------------------
# list_cycles
# ---------------------------------------------------------------------------


def _build_list_cycles_query(params: ListCyclesParams) -> str:
    """Build the GraphQL query string for listing cycles."""
    filter_arg = ""
    if params.team_id:
        filter_arg = f', filter: {{ team: {{ id: {{ eq: "{params.team_id}" }} }} }}'

    return f"""
    query {{
        cycles(first: 50{filter_arg}) {{
            nodes {{
                id
                name
                number
                startsAt
                endsAt
                progress
                completedAt
            }}
        }}
    }}
    """


@tool(scopes=SCOPES["linear_list_cycles"], api_docs=_API_DOCS, provider="linear")
async def linear_list_cycles(
    params: ListCyclesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListCyclesResult:
    """List cycles (sprints) from Linear."""
    query = _build_list_cycles_query(params)

    try:
        data = await _execute_graphql(query, None, token, base_url)
    except httpx.HTTPError as exc:
        return ListCyclesResult(success=False, error=str(exc))

    error = _extract_error(data)
    if error:
        return ListCyclesResult(success=False, error=error)

    nodes = data.get("data", {}).get("cycles", {}).get("nodes", [])
    cycles = [CycleDetail.model_validate(n) for n in nodes]
    return ListCyclesResult(success=True, cycles=cycles)


# ---------------------------------------------------------------------------
# upload_file_to_issue
# ---------------------------------------------------------------------------

_FILE_UPLOAD_MUTATION = """
mutation($size: Int!, $contentType: String!, $filename: String!) {
    fileUpload(size: $size, contentType: $contentType, filename: $filename) {
        success
        uploadFile {
            uploadUrl
            assetUrl
            headers {
                key
                value
            }
        }
    }
}
"""

_ATTACHMENT_CREATE_MUTATION = """
mutation($issueId: String!, $title: String!, $url: String!) {
    attachmentCreate(input: {
        issueId: $issueId,
        title: $title,
        url: $url
    }) {
        success
        attachment {
            id
            url
        }
    }
}
"""


@tool(
    scopes=SCOPES["linear_upload_file_to_issue"],
    api_docs=_API_DOCS,
    provider="linear",
)
async def linear_upload_file_to_issue(
    params: UploadFileToIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UploadFileToIssueResult:
    """Upload a file and attach it to a Linear issue."""
    try:
        file_data, filename, mime_type = await resolve_file_input(params.file)
    except Exception as exc:
        return UploadFileToIssueResult(success=False, error=f"Failed to resolve file: {exc}")

    # Step 1: Request a presigned upload URL.
    try:
        upload_resp = await _execute_graphql(
            _FILE_UPLOAD_MUTATION,
            {
                "size": len(file_data),
                "contentType": mime_type,
                "filename": filename,
            },
            token,
            base_url,
        )
    except httpx.HTTPError as exc:
        return UploadFileToIssueResult(success=False, error=str(exc))

    error = _extract_error(upload_resp)
    if error:
        return UploadFileToIssueResult(success=False, error=error)

    file_upload = upload_resp.get("data", {}).get("fileUpload", {})
    if not file_upload.get("success"):
        return UploadFileToIssueResult(success=False, error="fileUpload mutation returned success=false")

    upload_file = file_upload.get("uploadFile", {})
    upload_url = upload_file.get("uploadUrl")
    asset_url = upload_file.get("assetUrl")

    if not upload_url or not asset_url:
        return UploadFileToIssueResult(success=False, error="No upload URL returned from fileUpload")

    # Step 2: PUT the file bytes to the presigned URL.
    upload_headers = {h["key"]: h["value"] for h in upload_file.get("headers", [])}
    upload_headers["Content-Type"] = mime_type

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            put_resp = await client.put(upload_url, headers=upload_headers, content=file_data)
    except httpx.HTTPError as exc:
        return UploadFileToIssueResult(success=False, error=str(exc))

    if not put_resp.is_success:
        return UploadFileToIssueResult(
            success=False,
            error=f"Upload failed with status {put_resp.status_code}",
        )

    # Step 3: Create an attachment linking the uploaded file to the issue.
    attachment_title = params.title or filename

    try:
        attach_resp = await _execute_graphql(
            _ATTACHMENT_CREATE_MUTATION,
            {
                "issueId": params.issue_id,
                "title": attachment_title,
                "url": asset_url,
            },
            token,
            base_url,
        )
    except httpx.HTTPError as exc:
        return UploadFileToIssueResult(success=False, error=str(exc))

    error = _extract_error(attach_resp)
    if error:
        return UploadFileToIssueResult(success=False, error=error)

    attachment = attach_resp.get("data", {}).get("attachmentCreate", {}).get("attachment", {})

    return UploadFileToIssueResult(
        success=True,
        attachment_id=attachment.get("id"),
        asset_url=asset_url,
        filename=filename,
    )
