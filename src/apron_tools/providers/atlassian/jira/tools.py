"""Atlassian Jira tool functions for interacting with the Jira REST API v3."""

from __future__ import annotations

import httpx

from apron_tools._utils import parse_csv_ids
from apron_tools.fileio import resolve_file_input
from apron_tools.providers.atlassian.jira.types import (
    AddCommentParams,
    AddCommentResult,
    AssignIssueItem,
    AssignIssuesParams,
    AssignIssuesResult,
    BoardSummary,
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
    SprintSummary,
    UploadAttachmentParams,
    UploadAttachmentResult,
    VersionSummary,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.atlassian.com"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Jira API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


async def _resolve_cloud_id(token: str, base_url: str) -> str | None:
    """Resolve the Jira cloud ID for the authenticated user.

    Atlassian cloud APIs require a cloud ID to construct API URLs. This
    calls the accessible-resources endpoint to retrieve it.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/oauth/token/accessible-resources",
                headers=_headers(token),
            )
            if resp.is_success:
                resources = resp.json()
                if resources:
                    return resources[0].get("id")
    except httpx.HTTPError:
        pass
    return None


def _api_url(cloud_id: str, path: str, *, base_url: str) -> str:
    """Build a Jira REST API v3 URL."""
    return f"{base_url}/ex/jira/{cloud_id}/rest/api/3{path}"


def _agile_url(cloud_id: str, path: str, *, base_url: str) -> str:
    """Build a Jira Agile REST API URL."""
    return f"{base_url}/ex/jira/{cloud_id}/rest/agile/1.0{path}"


@tool(
    scopes=SCOPES["atlassian_jira_explore_projects"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-project-search/#api-rest-api-3-project-search-get",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_explore_projects(
    params: ExploreProjectsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreProjectsResult:
    """List all Jira projects accessible to the authenticated user."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ExploreProjectsResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_url(cloud_id, "/project/search", base_url=base_url),
                headers=_headers(token),
                params={"maxResults": params.max_results},
            )
    except httpx.HTTPError as exc:
        return ExploreProjectsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ExploreProjectsResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    projects = [ProjectSummary.model_validate(v) for v in data.get("values", [])]
    return ExploreProjectsResult(success=True, projects=projects)


@tool(
    scopes=SCOPES["atlassian_jira_explore_issues"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/#api-rest-api-3-search-jql-post",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_explore_issues(
    params: ExploreIssuesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreIssuesResult:
    """List issues in a Jira project, ordered by most recently updated."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ExploreIssuesResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    jql = f"project = {params.project_key}"
    if params.updated_after:
        jql += f' AND updated >= "{params.updated_after.strip()}"'
    jql += " ORDER BY updated DESC"

    body = {
        "jql": jql,
        "fields": [
            "summary",
            "description",
            "status",
            "priority",
            "assignee",
            "reporter",
            "created",
            "updated",
            "issuetype",
        ],
        "maxResults": params.max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _api_url(cloud_id, "/search/jql", base_url=base_url),
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return ExploreIssuesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ExploreIssuesResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    issues = [IssueSummary.model_validate(i) for i in data.get("issues", [])]
    return ExploreIssuesResult(
        success=True,
        project_key=params.project_key,
        total=data.get("total", len(issues)),
        issues=issues,
    )


@tool(
    scopes=SCOPES["atlassian_jira_create_issue"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-post",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_create_issue(
    params: CreateIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateIssueResult:
    """Create a new Jira issue."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return CreateIssueResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    fields: dict = {
        "project": {"key": params.project_key.upper()},
        "summary": params.summary,
        "issuetype": {"name": params.issue_type},
        "priority": {"name": params.priority},
    }

    if params.description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": params.description}],
                }
            ],
        }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _api_url(cloud_id, "/issue", base_url=base_url),
                headers=_headers(token, content_type=True),
                json={"fields": fields},
            )
    except httpx.HTTPError as exc:
        return CreateIssueResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateIssueResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    return CreateIssueResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["atlassian_jira_edit_issue"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-put",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_edit_issue(
    params: EditIssueParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> EditIssueResult:
    """Edit an existing Jira issue."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return EditIssueResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    fields: dict = {}
    if params.summary is not None:
        fields["summary"] = params.summary
    if params.description is not None:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": params.description}],
                }
            ],
        }
    if params.priority is not None:
        fields["priority"] = {"name": params.priority}

    if not fields:
        return EditIssueResult(success=False, error="No changes provided.")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.put(
                _api_url(cloud_id, f"/issue/{params.issue_key}", base_url=base_url),
                headers=_headers(token, content_type=True),
                json={"fields": fields},
            )
    except httpx.HTTPError as exc:
        return EditIssueResult(success=False, error=str(exc))

    if not resp.is_success:
        return EditIssueResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    return EditIssueResult(success=True, issue_key=params.issue_key)


async def _assign_one_issue(
    cloud_id: str,
    issue_key: str,
    account_id: str | None,
    token: str,
    base_url: str,
    client: httpx.AsyncClient,
) -> AssignIssueItem:
    """Run a single assignee PUT and shape the per-issue outcome."""
    try:
        resp = await client.put(
            _api_url(cloud_id, f"/issue/{issue_key}/assignee", base_url=base_url),
            headers=_headers(token, content_type=True),
            json={"accountId": account_id},
        )
    except httpx.HTTPError as exc:
        return AssignIssueItem(issue_key=issue_key, success=False, error=str(exc))

    if not resp.is_success:
        return AssignIssueItem(
            issue_key=issue_key,
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    return AssignIssueItem(issue_key=issue_key, success=True)


@tool(
    scopes=SCOPES["atlassian_jira_assign_issues"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-assignee-put",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_assign_issues(
    params: AssignIssuesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> AssignIssuesResult:
    """Assign or unassign one or more Jira issues with a shared assignee.

    ``assign_to_me`` applies to every issue in the call: pass True to assign
    each issue to the authenticated user, False to unassign each issue.
    Per-issue outcomes are returned in ``items`` so partial failures surface
    without aborting the whole bulk call.
    """
    issue_keys = parse_csv_ids(params.issue_keys)
    if not issue_keys:
        return AssignIssuesResult(success=False, error="No issue keys provided.")

    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return AssignIssuesResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    account_id: str | None = None
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        if params.assign_to_me:
            try:
                myself_resp = await client.get(
                    _api_url(cloud_id, "/myself", base_url=base_url),
                    headers=_headers(token),
                )
                if myself_resp.is_success:
                    account_id = myself_resp.json().get("accountId")
            except httpx.HTTPError:
                pass

            if not account_id:
                return AssignIssuesResult(
                    success=False,
                    error="Could not retrieve current user account ID.",
                )

        items = [await _assign_one_issue(cloud_id, key, account_id, token, base_url, client) for key in issue_keys]
    return AssignIssuesResult(success=True, assigned=params.assign_to_me, items=items)


@tool(
    scopes=SCOPES["atlassian_jira_add_comment"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/#api-rest-api-3-issue-issueidorkey-comment-post",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_add_comment(
    params: AddCommentParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> AddCommentResult:
    """Add a comment to a Jira issue."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return AddCommentResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": params.comment}],
                }
            ],
        }
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _api_url(cloud_id, f"/issue/{params.issue_key}/comment", base_url=base_url),
                headers=_headers(token, content_type=True),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return AddCommentResult(success=False, error=str(exc))

    if not resp.is_success:
        return AddCommentResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return AddCommentResult(
        success=True,
        issue_key=params.issue_key,
        comment_id=data.get("id", ""),
    )


@tool(
    scopes=SCOPES["atlassian_jira_list_versions"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-project-versions/#api-rest-api-3-project-projectidorkey-version-get",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_list_versions(
    params: ListVersionsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListVersionsResult:
    """List versions (milestones) for a Jira project."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ListVersionsResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    query: dict[str, str] = {}
    if params.status:
        query["status"] = params.status

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_url(cloud_id, f"/project/{params.project_key}/version", base_url=base_url),
                headers=_headers(token),
                params=query,
            )
    except httpx.HTTPError as exc:
        return ListVersionsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListVersionsResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    versions = [VersionSummary.model_validate(v) for v in data.get("values", [])]
    return ListVersionsResult(success=True, versions=versions)


@tool(
    scopes=SCOPES["atlassian_jira_list_boards"],
    api_docs="https://developer.atlassian.com/cloud/jira/software/rest/api-group-board/#api-rest-agile-1-0-board-get",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_list_boards(
    params: ListBoardsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListBoardsResult:
    """List Jira boards, optionally filtered by project."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ListBoardsResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    query: dict[str, str] = {}
    if params.project_key:
        query["projectKeyOrId"] = params.project_key

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _agile_url(cloud_id, "/board", base_url=base_url),
                headers=_headers(token),
                params=query,
            )
    except httpx.HTTPError as exc:
        return ListBoardsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListBoardsResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    boards = [BoardSummary.model_validate(b) for b in data.get("values", [])]
    return ListBoardsResult(success=True, boards=boards)


@tool(
    scopes=SCOPES["atlassian_jira_list_sprints"],
    api_docs="https://developer.atlassian.com/cloud/jira/software/rest/api-group-sprint/#api-rest-agile-1-0-board-boardid-sprint-get",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_list_sprints(
    params: ListSprintsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListSprintsResult:
    """List sprints for a Jira board."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ListSprintsResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    query: dict[str, str] = {}
    if params.state:
        query["state"] = params.state

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _agile_url(cloud_id, f"/board/{params.board_id}/sprint", base_url=base_url),
                headers=_headers(token),
                params=query,
            )
    except httpx.HTTPError as exc:
        return ListSprintsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListSprintsResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    sprints = [SprintSummary.model_validate(s) for s in data.get("values", [])]
    return ListSprintsResult(success=True, sprints=sprints)


@tool(
    scopes=SCOPES["atlassian_jira_upload_attachment"],
    api_docs="https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/",
    provider="atlassian",
    service="atlassian_jira",
)
async def atlassian_jira_upload_attachment(
    params: UploadAttachmentParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UploadAttachmentResult:
    """Upload a file as an attachment to a Jira issue."""
    try:
        data, filename, mime_type = await resolve_file_input(params.file)
    except Exception as exc:
        return UploadAttachmentResult(success=False, error=f"Failed to resolve file: {exc}")

    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return UploadAttachmentResult(
            success=False,
            error="Failed to resolve Jira cloud ID. Ensure you have access to a Jira site.",
        )

    url = _api_url(cloud_id, f"/issue/{params.issue_key}/attachments", base_url=base_url)
    headers = _headers(token)
    headers["X-Atlassian-Token"] = "no-check"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers=headers,
                files={"file": (filename, data, mime_type)},
            )
    except httpx.HTTPError as exc:
        return UploadAttachmentResult(success=False, error=str(exc))

    if not resp.is_success:
        return UploadAttachmentResult(
            success=False,
            error=f"Jira API error {resp.status_code}: {resp.text}",
        )

    attachments = resp.json()
    if isinstance(attachments, list) and attachments:
        att = attachments[0]
        return UploadAttachmentResult(
            success=True,
            attachment_id=att.get("id", ""),
            filename=att.get("filename", filename),
            issue_key=params.issue_key,
        )

    return UploadAttachmentResult(
        success=True,
        filename=filename,
        issue_key=params.issue_key,
    )
