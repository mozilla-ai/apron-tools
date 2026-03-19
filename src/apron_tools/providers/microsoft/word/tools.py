"""Microsoft Word tool functions.

Each tool composes shared OneDrive operations (network) with
document format manipulation (pure, synchronous). The tools
module is the thin orchestration layer between the two.
"""

from __future__ import annotations

import httpx

from apron_tools.providers.microsoft import onedrive
from apron_tools.providers.microsoft.word import document
from apron_tools.providers.microsoft.word.types import (
    CreateDocumentParams,
    CreateDocumentResult,
    DocumentInfo,
    ExploreDocumentsParams,
    ExploreDocumentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
    UploadToOnedriveParams,
    UploadToOnedriveResult,
)
from apron_tools.tool import tool
from apron_tools.types import FileFromUrl

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_DOCX_EXTENSIONS = {".docx", ".doc"}


@tool(
    scopes=SCOPES["microsoft_word_explore_documents"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-search",
    provider="microsoft",
    service="microsoft_word",
)
async def microsoft_word_explore_documents(
    params: ExploreDocumentsParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ExploreDocumentsResult:
    """List Word documents accessible by the user in OneDrive."""
    try:
        files = await onedrive.search_files(
            token,
            _DOCX_EXTENSIONS,
            max_results=params.max_results,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return ExploreDocumentsResult(success=False, error=str(exc))

    documents = [DocumentInfo.model_validate(f) for f in files]
    return ExploreDocumentsResult(
        success=True,
        documents=documents,
    )


@tool(
    scopes=SCOPES["microsoft_word_read_document"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-get-content",
    provider="microsoft",
    service="microsoft_word",
)
async def microsoft_word_read_document(
    params: ReadDocumentParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadDocumentResult:
    """Read the content of a Word document from OneDrive."""
    try:
        meta = await onedrive.get_file_metadata(token, params.document_id, base_url=base_url)
        docx_bytes = await onedrive.download_file(token, params.document_id, base_url=base_url)
    except httpx.HTTPError as exc:
        return ReadDocumentResult(success=False, error=str(exc))

    text_data = document.extract_text(docx_bytes)

    return ReadDocumentResult(
        success=True,
        name=meta.get("name", ""),
        paragraphs=text_data["paragraphs"],
        tables=text_data["tables"],
    )


@tool(
    scopes=SCOPES["microsoft_word_create_document"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_word",
)
async def microsoft_word_create_document(
    params: CreateDocumentParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreateDocumentResult:
    """Create a new Word document in OneDrive."""
    filename = params.name if params.name.endswith(".docx") else f"{params.name}.docx"

    try:
        docx_bytes = document.build_docx(params.content)
        result = await onedrive.upload_file(
            token,
            docx_bytes,
            filename,
            _DOCX_MIME,
            params.folder_path,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return CreateDocumentResult(success=False, error=str(exc))

    return CreateDocumentResult(
        success=True,
        document_id=result.get("id", ""),
        name=result.get("name", filename),
        web_url=result.get("webUrl", ""),
    )


@tool(
    scopes=SCOPES["microsoft_word_update_document"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_word",
)
async def microsoft_word_update_document(
    params: UpdateDocumentParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> UpdateDocumentResult:
    """Append content to an existing Word document in OneDrive."""
    try:
        meta = await onedrive.get_file_metadata(token, params.document_id, base_url=base_url)
        docx_bytes = await onedrive.download_file(token, params.document_id, base_url=base_url)
    except httpx.HTTPError as exc:
        return UpdateDocumentResult(success=False, error=str(exc))

    updated_bytes = document.append_content(docx_bytes, params.content)

    try:
        await onedrive.update_file_content(
            token,
            params.document_id,
            updated_bytes,
            _DOCX_MIME,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return UpdateDocumentResult(success=False, error=str(exc))

    return UpdateDocumentResult(
        success=True,
        name=meta.get("name", ""),
    )


@tool(
    scopes=SCOPES["microsoft_word_upload_to_onedrive"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_word",
)
async def microsoft_word_upload_to_onedrive(
    params: UploadToOnedriveParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> UploadToOnedriveResult:
    """Upload a file to OneDrive."""
    file_input = params.file

    if isinstance(file_input, FileFromUrl):
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(str(file_input.url))
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            return UploadToOnedriveResult(success=False, error=f"Download failed: {exc}")

        data = resp.content
        filename = params.name or file_input.filename or str(file_input.url).rsplit("/", 1)[-1]
        mime_type = file_input.mime_type or resp.headers.get("content-type", "application/octet-stream")
    else:
        data = file_input.data
        filename = params.name or file_input.filename
        mime_type = file_input.mime_type

    try:
        result = await onedrive.upload_file(
            token,
            data,
            filename,
            mime_type,
            params.folder_path,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return UploadToOnedriveResult(success=False, error=str(exc))

    return UploadToOnedriveResult(
        success=True,
        file_id=result.get("id", ""),
        name=result.get("name", filename),
        web_url=result.get("webUrl", ""),
    )
