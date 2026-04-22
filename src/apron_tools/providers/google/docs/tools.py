"""Google Docs tool functions for interacting with the Docs and Drive REST APIs."""

from __future__ import annotations

import contextlib
from typing import Any

import httpx

from apron_tools.providers.google._images import delete_drive_file, upload_image_to_drive
from apron_tools.providers.google.docs.types import (
    Comment,
    CopyDocumentParams,
    CopyDocumentResult,
    CreateCommentParams,
    CreateCommentResult,
    CreateDocumentParams,
    CreateDocumentResult,
    DocumentFile,
    InsertImageParams,
    InsertImageResult,
    ListDocumentsParams,
    ListDocumentsResult,
    ReadCommentsParams,
    ReadCommentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    ReplaceTextParams,
    ReplaceTextResult,
    ReplyToCommentParams,
    ReplyToCommentResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
    UpdateTableCellParams,
    UpdateTableCellResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_DOCS_BASE_URL = "https://docs.googleapis.com/v1/documents"
_DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3/files"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Google API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


@tool(
    scopes=SCOPES["google_docs_list_documents"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/list",
    provider="google",
    service="google_docs",
)
async def google_docs_list_documents(
    params: ListDocumentsParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> ListDocumentsResult:
    """List all Google Docs documents accessible by the user."""
    query_params: dict[str, Any] = {
        "q": "mimeType='application/vnd.google-apps.document'",
        "pageSize": params.max_results,
        "fields": "files(id,name,createdTime,modifiedTime)",
        "orderBy": "modifiedTime desc",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "corpora": "allDrives",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _DRIVE_BASE_URL,
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListDocumentsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListDocumentsResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    files = [DocumentFile.model_validate(f) for f in data.get("files", [])]
    return ListDocumentsResult(success=True, files=files)


@tool(
    scopes=SCOPES["google_docs_create_document"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/create",
    provider="google",
    service="google_docs",
)
async def google_docs_create_document(
    params: CreateDocumentParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> CreateDocumentResult:
    """Create a new Google Docs document."""
    body: dict[str, Any] = {"title": params.title}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                base_url,
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateDocumentResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateDocumentResult(
            success=False,
            error=f"Docs API error {resp.status_code}: {resp.text}",
        )

    return CreateDocumentResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_docs_read_document"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get",
    provider="google",
    service="google_docs",
)
async def google_docs_read_document(
    params: ReadDocumentParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> ReadDocumentResult:
    """Read the content of a Google Docs document."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/{params.document_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ReadDocumentResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadDocumentResult(
            success=False,
            error=f"Docs API error {resp.status_code}: {resp.text}",
        )

    return ReadDocumentResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_docs_update_document"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate",
    provider="google",
    service="google_docs",
)
async def google_docs_update_document(
    params: UpdateDocumentParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> UpdateDocumentResult:
    """Update a Google Docs document via batchUpdate."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.document_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json={"requests": params.requests},
            )
    except httpx.HTTPError as exc:
        return UpdateDocumentResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateDocumentResult(
            success=False,
            error=f"Docs API error {resp.status_code}: {resp.text}",
        )

    return UpdateDocumentResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_docs_copy_document"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/copy",
    provider="google",
    service="google_docs",
)
async def google_docs_copy_document(
    params: CopyDocumentParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> CopyDocumentResult:
    """Create a copy of an existing Google Docs document."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the original document title from Drive.
            meta_resp = await client.get(
                f"{_DRIVE_BASE_URL}/{params.document_id}",
                headers=_headers(token),
                params={"fields": "name", "supportsAllDrives": "true"},
            )
            if not meta_resp.is_success:
                return CopyDocumentResult(
                    success=False,
                    error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
                )
            original_name = meta_resp.json().get("name", "Unknown")

            # Copy via Drive API.
            copy_resp = await client.post(
                f"{_DRIVE_BASE_URL}/{params.document_id}/copy",
                headers=_headers(token, content_type=True),
                json={"name": params.new_title},
                params={"supportsAllDrives": "true"},
            )
    except httpx.HTTPError as exc:
        return CopyDocumentResult(success=False, error=str(exc))

    if not copy_resp.is_success:
        return CopyDocumentResult(
            success=False,
            error=f"Drive API error {copy_resp.status_code}: {copy_resp.text}",
        )

    copy_data = copy_resp.json()
    return CopyDocumentResult(
        success=True,
        id=copy_data.get("id", ""),
        name=copy_data.get("name", params.new_title),
        original_name=original_name,
    )


@tool(
    scopes=SCOPES["google_docs_replace_text"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate",
    provider="google",
    service="google_docs",
)
async def google_docs_replace_text(
    params: ReplaceTextParams, *, token: str, base_url: str = _DOCS_BASE_URL
) -> ReplaceTextResult:
    """Find and replace all occurrences of a text string in a Google Doc."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Get document title first.
            doc_resp = await client.get(
                f"{base_url}/{params.document_id}",
                headers=_headers(token),
                params={"fields": "title"},
            )
            if not doc_resp.is_success:
                return ReplaceTextResult(
                    success=False,
                    error=f"Docs API error {doc_resp.status_code}: {doc_resp.text}",
                )
            title = doc_resp.json().get("title", "Untitled")

            # Perform the replacement.
            batch_resp = await client.post(
                f"{base_url}/{params.document_id}:batchUpdate",
                headers=_headers(token),
                json={
                    "requests": [
                        {
                            "replaceAllText": {
                                "containsText": {
                                    "text": params.find_text,
                                    "matchCase": params.match_case,
                                },
                                "replaceText": params.replace_text,
                            }
                        }
                    ]
                },
            )
    except httpx.HTTPError as exc:
        return ReplaceTextResult(success=False, error=str(exc))

    if not batch_resp.is_success:
        return ReplaceTextResult(
            success=False,
            error=f"Docs API error {batch_resp.status_code}: {batch_resp.text}",
        )

    replies = batch_resp.json().get("replies", [])
    occurrences = 0
    if replies:
        occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0)

    return ReplaceTextResult(
        success=True,
        document_id=params.document_id,
        title=title,
        occurrences_changed=occurrences,
    )


@tool(
    scopes=SCOPES["google_docs_insert_image"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate",
    provider="google",
    service="google_docs",
)
async def google_docs_insert_image(
    params: InsertImageParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> InsertImageResult:
    """Insert an image into a Google Doc at a given position."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            drive_file_id, public_url, filename = await upload_image_to_drive(params.file, token, client=client)
        except ValueError as exc:
            return InsertImageResult(success=False, error=str(exc))
        except httpx.HTTPStatusError as exc:
            return InsertImageResult(
                success=False,
                error=f"Drive API error {exc.response.status_code}: {exc.response.text}",
            )
        except httpx.HTTPError as exc:
            return InsertImageResult(success=False, error=str(exc))

        batch_body = {
            "requests": [
                {
                    "insertInlineImage": {
                        "uri": public_url,
                        "location": {"index": params.location_index},
                        "objectSize": {
                            "width": {"magnitude": params.width_pt, "unit": "PT"},
                            "height": {"magnitude": params.height_pt, "unit": "PT"},
                        },
                    }
                }
            ]
        }

        try:
            resp = await client.post(
                f"{base_url}/{params.document_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=batch_body,
            )
        except httpx.HTTPError as exc:
            await _cleanup_drive_file(drive_file_id, token, client=client)
            return InsertImageResult(success=False, error=str(exc), drive_file_id=drive_file_id)

        if not resp.is_success:
            await _cleanup_drive_file(drive_file_id, token, client=client)
            return InsertImageResult(
                success=False,
                error=f"Docs API error {resp.status_code}: {resp.text}",
                drive_file_id=drive_file_id,
            )

        return InsertImageResult(
            success=True,
            document_id=params.document_id,
            filename=filename,
            drive_file_id=drive_file_id,
        )


async def _cleanup_drive_file(file_id: str, token: str, *, client: httpx.AsyncClient) -> None:
    """Best-effort cleanup of an uploaded Drive file after insert failure."""
    with contextlib.suppress(httpx.HTTPError):
        await delete_drive_file(file_id, token, client=client)


def _find_nth_table(content: list[dict[str, Any]], table_index: int) -> dict[str, Any] | None:
    """Return the Nth top-level table element in the body, or None if missing.

    Tables nested inside another table's cell are intentionally ignored so
    that indices match the reading order a human sees in the document.
    """
    if table_index < 0:
        return None
    count = 0
    for element in content:
        if "table" not in element:
            continue
        if count == table_index:
            return element["table"]
        count += 1
    return None


@tool(
    scopes=SCOPES["google_docs_update_table_cell"],
    api_docs="https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate",
    provider="google",
    service="google_docs",
)
async def google_docs_update_table_cell(
    params: UpdateTableCellParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> UpdateTableCellResult:
    """Replace the contents of a single cell in a native Google Docs table."""
    fields = "title,body(content(table(tableRows(tableCells(startIndex,endIndex)))))"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            doc_resp = await client.get(
                f"{base_url}/{params.document_id}",
                headers=_headers(token),
                params={"fields": fields},
            )
            if not doc_resp.is_success:
                return UpdateTableCellResult(
                    success=False,
                    error=f"Docs API error {doc_resp.status_code}: {doc_resp.text}",
                )

            doc_data = doc_resp.json()
            title = doc_data.get("title", "Untitled")
            content_elements = doc_data.get("body", {}).get("content", [])

            table = _find_nth_table(content_elements, params.table_index)
            if table is None:
                return UpdateTableCellResult(
                    success=False,
                    error=(f"Table at index {params.table_index} not found in document '{title}'."),
                    document_id=params.document_id,
                    title=title,
                    table_index=params.table_index,
                    row=params.row,
                    column=params.column,
                )

            table_rows = table.get("tableRows", [])
            if params.row >= len(table_rows):
                return UpdateTableCellResult(
                    success=False,
                    error=(
                        f"Row {params.row} is out of range (table {params.table_index} has {len(table_rows)} row(s))."
                    ),
                    document_id=params.document_id,
                    title=title,
                    table_index=params.table_index,
                    row=params.row,
                    column=params.column,
                )

            table_cells = table_rows[params.row].get("tableCells", [])
            if params.column >= len(table_cells):
                return UpdateTableCellResult(
                    success=False,
                    error=(
                        f"Column {params.column} is out of range (row {params.row} has {len(table_cells)} column(s))."
                    ),
                    document_id=params.document_id,
                    title=title,
                    table_index=params.table_index,
                    row=params.row,
                    column=params.column,
                )

            cell = table_cells[params.column]
            cell_start = cell.get("startIndex")
            cell_end = cell.get("endIndex")
            if not isinstance(cell_start, int) or not isinstance(cell_end, int):
                return UpdateTableCellResult(
                    success=False,
                    error=(f"Cell (row {params.row}, column {params.column}) is missing position information."),
                    document_id=params.document_id,
                    title=title,
                    table_index=params.table_index,
                    row=params.row,
                    column=params.column,
                )

            # A cell's editable interior is [cell_start + 1, cell_end - 1).
            # The trailing paragraph break at cell_end - 1 must be preserved:
            # Google Docs rejects batchUpdates that would delete the newline
            # that terminates every cell.
            content_start = cell_start + 1
            content_end = cell_end - 1

            requests: list[dict[str, Any]] = []
            if content_end > content_start:
                requests.append(
                    {
                        "deleteContentRange": {
                            "range": {
                                "startIndex": content_start,
                                "endIndex": content_end,
                            }
                        }
                    }
                )
            if params.text:
                requests.append(
                    {
                        "insertText": {
                            "location": {"index": content_start},
                            "text": params.text,
                        }
                    }
                )

            if not requests:
                return UpdateTableCellResult(
                    success=True,
                    document_id=params.document_id,
                    title=title,
                    table_index=params.table_index,
                    row=params.row,
                    column=params.column,
                )

            batch_resp = await client.post(
                f"{base_url}/{params.document_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json={"requests": requests},
            )
    except httpx.HTTPError as exc:
        return UpdateTableCellResult(success=False, error=str(exc))

    if not batch_resp.is_success:
        return UpdateTableCellResult(
            success=False,
            error=f"Docs API error {batch_resp.status_code}: {batch_resp.text}",
            document_id=params.document_id,
            title=title,
            table_index=params.table_index,
            row=params.row,
            column=params.column,
        )

    return UpdateTableCellResult(
        success=True,
        document_id=params.document_id,
        title=title,
        table_index=params.table_index,
        row=params.row,
        column=params.column,
    )


@tool(
    scopes=SCOPES["google_docs_read_comments"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/comments/list",
    provider="google",
    service="google_docs",
)
async def google_docs_read_comments(
    params: ReadCommentsParams,
    *,
    token: str,
    base_url: str = _DOCS_BASE_URL,
) -> ReadCommentsResult:
    """List comments on a Google Docs document via the Drive Comments API."""
    page_size = min(max(1, params.max_results), 100)
    comment_fields = (
        "nextPageToken,comments(id,content,resolved,"
        "author(displayName),createdTime,quotedFileContent,"
        "replies(id,content,author(displayName),createdTime))"
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            doc_resp = await client.get(
                f"{base_url}/{params.document_id}",
                headers=_headers(token),
                params={"fields": "title"},
            )
            if not doc_resp.is_success:
                return ReadCommentsResult(
                    success=False,
                    error=f"Docs API error {doc_resp.status_code}: {doc_resp.text}",
                )
            title = doc_resp.json().get("title", "Untitled")

            comments_resp = await client.get(
                f"{_DRIVE_BASE_URL}/{params.document_id}/comments",
                headers=_headers(token),
                params={
                    "fields": comment_fields,
                    "pageSize": page_size,
                    "supportsAllDrives": "true",
                },
            )
    except httpx.HTTPError as exc:
        return ReadCommentsResult(success=False, error=str(exc))

    if not comments_resp.is_success:
        return ReadCommentsResult(
            success=False,
            error=f"Drive API error {comments_resp.status_code}: {comments_resp.text}",
            document_id=params.document_id,
            title=title,
        )

    data = comments_resp.json()
    raw_comments = data.get("comments", [])
    has_more = data.get("nextPageToken") is not None

    if not params.include_resolved:
        raw_comments = [c for c in raw_comments if not c.get("resolved", False)]

    comments = [Comment.model_validate(c) for c in raw_comments]
    return ReadCommentsResult(
        success=True,
        document_id=params.document_id,
        title=title,
        comments=comments,
        include_resolved=params.include_resolved,
        has_more=has_more,
    )


@tool(
    scopes=SCOPES["google_docs_create_comment"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/comments/create",
    provider="google",
    service="google_docs",
)
async def google_docs_create_comment(
    params: CreateCommentParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> CreateCommentResult:
    """Create a comment on a Google Docs document via the Drive Comments API."""
    body: dict[str, Any] = {"content": params.comment}
    if params.quoted_text:
        body["quotedFileContent"] = {
            "value": params.quoted_text,
            "mimeType": "text/html",
        }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.document_id}/comments",
                headers=_headers(token, content_type=True),
                json=body,
                params={
                    "fields": "id,content,author(displayName),createdTime,quotedFileContent",
                    "supportsAllDrives": "true",
                },
            )
    except httpx.HTTPError as exc:
        return CreateCommentResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateCommentResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return CreateCommentResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_docs_reply_to_comment"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/replies/create",
    provider="google",
    service="google_docs",
)
async def google_docs_reply_to_comment(
    params: ReplyToCommentParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> ReplyToCommentResult:
    """Reply to an existing comment thread on a Google Docs document."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.document_id}/comments/{params.comment_id}/replies",
                headers=_headers(token, content_type=True),
                json={"content": params.reply},
                params={
                    "fields": "id,content,author(displayName),createdTime",
                    "supportsAllDrives": "true",
                },
            )
    except httpx.HTTPError as exc:
        return ReplyToCommentResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReplyToCommentResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return ReplyToCommentResult.model_validate(resp.json())
