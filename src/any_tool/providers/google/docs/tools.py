"""Google Docs tool functions for interacting with the Docs and Drive REST APIs."""

from __future__ import annotations

from typing import Any

import httpx

from any_tool.providers.google.docs.types import (
    CopyDocumentParams,
    CopyDocumentResult,
    CreateDocumentParams,
    CreateDocumentResult,
    DocumentFile,
    ListDocumentsParams,
    ListDocumentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    ReplaceTextParams,
    ReplaceTextResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
)
from any_tool.tool import tool

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
