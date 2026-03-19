"""Microsoft PowerPoint tool functions.

Each tool composes shared OneDrive operations (network) with
presentation format manipulation (pure, synchronous). The tools
module is the thin orchestration layer between the two.
"""

from __future__ import annotations

import httpx

from apron_tools.providers.microsoft import onedrive
from apron_tools.providers.microsoft.powerpoint import presentation
from apron_tools.providers.microsoft.powerpoint.types import (
    AddSlideParams,
    AddSlideResult,
    CreatePresentationParams,
    CreatePresentationResult,
    ExplorePresentationsParams,
    ExplorePresentationsResult,
    PresentationInfo,
    ReadPresentationParams,
    ReadPresentationResult,
    SlideInfo,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UploadToOnedriveParams,
    UploadToOnedriveResult,
)
from apron_tools.tool import tool
from apron_tools.types import FileFromUrl

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_PPTX_EXTENSIONS = {".pptx", ".ppt", ".pptm"}


@tool(
    scopes=SCOPES["microsoft_powerpoint_explore_presentations"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-search",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_explore_presentations(
    params: ExplorePresentationsParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ExplorePresentationsResult:
    """List PowerPoint presentations accessible by the user in OneDrive."""
    try:
        files = await onedrive.search_files(
            token,
            _PPTX_EXTENSIONS,
            max_results=params.max_results,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return ExplorePresentationsResult(success=False, error=str(exc))

    presentations = [PresentationInfo.model_validate(f) for f in files]
    return ExplorePresentationsResult(
        success=True,
        presentations=presentations,
    )


@tool(
    scopes=SCOPES["microsoft_powerpoint_read_presentation"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-get-content",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_read_presentation(
    params: ReadPresentationParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadPresentationResult:
    """Read the content of a PowerPoint presentation from OneDrive."""
    try:
        meta = await onedrive.get_file_metadata(token, params.presentation_id, base_url=base_url)
        pptx_bytes = await onedrive.download_file(token, params.presentation_id, base_url=base_url)
    except httpx.HTTPError as exc:
        return ReadPresentationResult(success=False, error=str(exc))

    slides_data = presentation.extract_slides(pptx_bytes, params.include_notes)
    slides = [SlideInfo(**s) for s in slides_data]

    return ReadPresentationResult(
        success=True,
        name=meta.get("name", ""),
        slides=slides,
    )


@tool(
    scopes=SCOPES["microsoft_powerpoint_create_presentation"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_create_presentation(
    params: CreatePresentationParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreatePresentationResult:
    """Create a new PowerPoint presentation in OneDrive."""
    filename = params.name if params.name.endswith(".pptx") else f"{params.name}.pptx"

    try:
        pptx_bytes = presentation.build_pptx(params.title)
        result = await onedrive.upload_file(
            token,
            pptx_bytes,
            filename,
            _PPTX_MIME,
            params.folder_path,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return CreatePresentationResult(success=False, error=str(exc))

    return CreatePresentationResult(
        success=True,
        presentation_id=result.get("id", ""),
        name=result.get("name", filename),
        web_url=result.get("webUrl", ""),
    )


@tool(
    scopes=SCOPES["microsoft_powerpoint_add_slide"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_add_slide(
    params: AddSlideParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> AddSlideResult:
    """Add a new slide to an existing PowerPoint presentation."""
    try:
        meta = await onedrive.get_file_metadata(token, params.presentation_id, base_url=base_url)
        pptx_bytes = await onedrive.download_file(token, params.presentation_id, base_url=base_url)
    except httpx.HTTPError as exc:
        return AddSlideResult(success=False, error=str(exc))

    updated_bytes, slide_count = presentation.add_slide(pptx_bytes, params.layout, params.title, params.content)

    try:
        await onedrive.update_file_content(
            token,
            params.presentation_id,
            updated_bytes,
            _PPTX_MIME,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return AddSlideResult(success=False, error=str(exc))

    return AddSlideResult(
        success=True,
        name=meta.get("name", ""),
        layout=params.layout,
        slide_count=slide_count,
    )


@tool(
    scopes=SCOPES["microsoft_powerpoint_update_slide_text"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_update_slide_text(
    params: UpdateSlideTextParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> UpdateSlideTextResult:
    """Update text in a shape on a specific slide of a PowerPoint presentation."""
    try:
        meta = await onedrive.get_file_metadata(token, params.presentation_id, base_url=base_url)
        pptx_bytes = await onedrive.download_file(token, params.presentation_id, base_url=base_url)
    except httpx.HTTPError as exc:
        return UpdateSlideTextResult(success=False, error=str(exc))

    updated_bytes, shape_name, error = presentation.update_text(
        pptx_bytes, params.slide_number, params.text, params.shape_index
    )

    if error:
        return UpdateSlideTextResult(success=False, error=error)

    try:
        await onedrive.update_file_content(
            token,
            params.presentation_id,
            updated_bytes,
            _PPTX_MIME,
            base_url=base_url,
        )
    except httpx.HTTPError as exc:
        return UpdateSlideTextResult(success=False, error=str(exc))

    return UpdateSlideTextResult(
        success=True,
        name=meta.get("name", ""),
        slide_number=params.slide_number,
        shape_name=shape_name,
    )


@tool(
    scopes=SCOPES["microsoft_powerpoint_upload_to_onedrive"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-put-content",
    provider="microsoft",
    service="microsoft_powerpoint",
)
async def microsoft_powerpoint_upload_to_onedrive(
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
