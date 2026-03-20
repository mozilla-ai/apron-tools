"""Google Slides tool functions for interacting with the Slides and Drive REST APIs."""

from __future__ import annotations

import contextlib
import uuid

import httpx

from apron_tools.providers.google._images import delete_drive_file, upload_image_to_drive
from apron_tools.providers.google.slides.types import (
    AddSlideParams,
    AddSlideResult,
    CopyPresentationParams,
    CopyPresentationResult,
    CreatePresentationParams,
    CreatePresentationResult,
    DuplicateSlideParams,
    DuplicateSlideResult,
    FormatTextParams,
    FormatTextResult,
    InsertElementParams,
    InsertElementResult,
    InsertImageParams,
    InsertImageResult,
    ListPresentationsParams,
    ListPresentationsResult,
    PresentationFile,
    ReadPresentationParams,
    ReadPresentationResult,
    SlideInfo,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UpdateTableCellParams,
    UpdateTableCellResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_SLIDES_BASE_URL = "https://slides.googleapis.com/v1/presentations"
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


def _extract_slide_text(slide: dict) -> list[str]:
    """Extract all text content from a slide's page elements."""
    texts: list[str] = []
    for element in slide.get("pageElements", []):
        shape = element.get("shape", {})
        for text_elem in shape.get("text", {}).get("textElements", []):
            content = text_elem.get("textRun", {}).get("content", "").strip()
            if content:
                texts.append(content)
    return texts


@tool(
    scopes=SCOPES["google_slides_list_presentations"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/list",
    provider="google",
    service="google_slides",
)
async def google_slides_list_presentations(
    params: ListPresentationsParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> ListPresentationsResult:
    """List all Google Slides presentations accessible by the user."""
    query_params = {
        "q": "mimeType='application/vnd.google-apps.presentation'",
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
        return ListPresentationsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListPresentationsResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    files = [PresentationFile.model_validate(f) for f in data.get("files", [])]
    return ListPresentationsResult(success=True, files=files)


@tool(
    scopes=SCOPES["google_slides_create_presentation"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/create",
    provider="google",
    service="google_slides",
)
async def google_slides_create_presentation(
    params: CreatePresentationParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> CreatePresentationResult:
    """Create a new Google Slides presentation."""
    body: dict = {"title": params.title}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                base_url,
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreatePresentationResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreatePresentationResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    return CreatePresentationResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_slides_copy_presentation"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/copy",
    provider="google",
    service="google_slides",
)
async def google_slides_copy_presentation(
    params: CopyPresentationParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> CopyPresentationResult:
    """Create a copy of an existing Google Slides presentation."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the original presentation title from Drive.
            meta_resp = await client.get(
                f"{_DRIVE_BASE_URL}/{params.presentation_id}",
                headers=_headers(token),
                params={"fields": "name", "supportsAllDrives": "true"},
            )
            if not meta_resp.is_success:
                return CopyPresentationResult(
                    success=False,
                    error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
                )
            original_name = meta_resp.json().get("name", "Unknown")

            # Copy via Drive API.
            copy_resp = await client.post(
                f"{_DRIVE_BASE_URL}/{params.presentation_id}/copy",
                headers=_headers(token, content_type=True),
                json={"name": params.new_title},
                params={"supportsAllDrives": "true"},
            )
    except httpx.HTTPError as exc:
        return CopyPresentationResult(success=False, error=str(exc))

    if not copy_resp.is_success:
        return CopyPresentationResult(
            success=False,
            error=f"Drive API error {copy_resp.status_code}: {copy_resp.text}",
        )

    copy_data = copy_resp.json()
    return CopyPresentationResult(
        success=True,
        id=copy_data.get("id", ""),
        name=copy_data.get("name", params.new_title),
        original_name=original_name,
    )


@tool(
    scopes=SCOPES["google_slides_read_presentation"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/get",
    provider="google",
    service="google_slides",
)
async def google_slides_read_presentation(
    params: ReadPresentationParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> ReadPresentationResult:
    """Read the content of a Google Slides presentation."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/{params.presentation_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ReadPresentationResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadPresentationResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    title = data.get("title", "Untitled")
    raw_slides = data.get("slides", [])
    slides: list[SlideInfo] = []
    for i, slide in enumerate(raw_slides):
        text_content = _extract_slide_text(slide)
        if params.include_speaker_notes:
            notes_page = slide.get("slideProperties", {}).get("notesPage", {})
            text_content.extend(_extract_slide_text(notes_page))
        slides.append(
            SlideInfo(
                object_id=slide.get("objectId", ""),
                index=i,
                text_content=text_content,
            )
        )

    return ReadPresentationResult(
        success=True,
        title=title,
        slide_count=len(raw_slides),
        slides=slides,
    )


@tool(
    scopes=SCOPES["google_slides_add_slide"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_add_slide(
    params: AddSlideParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> AddSlideResult:
    """Add a new slide to a Google Slides presentation."""
    slide_id = f"slide_{uuid.uuid4().hex[:8]}"
    create_slide: dict = {
        "objectId": slide_id,
        "slideLayoutReference": {"predefinedLayout": params.layout},
    }
    if params.insertion_index is not None:
        create_slide["insertionIndex"] = params.insertion_index

    body = {"requests": [{"createSlide": create_slide}]}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return AddSlideResult(success=False, error=str(exc))

    if not resp.is_success:
        return AddSlideResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    result = AddSlideResult.model_validate(resp.json())
    result.presentation_id = params.presentation_id
    return result


@tool(
    scopes=SCOPES["google_slides_update_slide_text"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_update_slide_text(
    params: UpdateSlideTextParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> UpdateSlideTextResult:
    """Update text content in a slide shape or text box."""
    requests: list[dict] = []
    target_shape_id = params.shape_id

    if target_shape_id:
        # Replace text in an existing shape.
        requests.append({"deleteText": {"objectId": target_shape_id, "textRange": {"type": "ALL"}}})
        requests.append(
            {
                "insertText": {
                    "objectId": target_shape_id,
                    "insertionIndex": 0,
                    "text": params.text,
                }
            }
        )
    else:
        # Create a new text box on the slide.
        target_shape_id = f"textbox_{uuid.uuid4().hex[:8]}"
        requests.append(
            {
                "createShape": {
                    "objectId": target_shape_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": params.slide_id,
                        "size": {
                            "width": {"magnitude": 400, "unit": "PT"},
                            "height": {"magnitude": 50, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 100,
                            "translateY": 100,
                            "unit": "PT",
                        },
                    },
                }
            }
        )
        requests.append(
            {
                "insertText": {
                    "objectId": target_shape_id,
                    "insertionIndex": 0,
                    "text": params.text,
                }
            }
        )

    body = {"requests": requests}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return UpdateSlideTextResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateSlideTextResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    return UpdateSlideTextResult(
        success=True,
        presentation_id=params.presentation_id,
        shape_id=target_shape_id,
    )


@tool(
    scopes=SCOPES["google_slides_duplicate_slide"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_duplicate_slide(
    params: DuplicateSlideParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> DuplicateSlideResult:
    """Duplicate a slide in a Google Slides presentation."""
    body = {"requests": [{"duplicateObject": {"objectId": params.slide_id}}]}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return DuplicateSlideResult(success=False, error=str(exc))

    if not resp.is_success:
        return DuplicateSlideResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    result = DuplicateSlideResult.model_validate(resp.json())
    result.presentation_id = params.presentation_id
    return result


@tool(
    scopes=SCOPES["google_slides_insert_element"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_insert_element(
    params: InsertElementParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> InsertElementResult:
    """Insert a shape element with optional text into a slide."""
    element_id = f"shape_{uuid.uuid4().hex[:8]}"
    requests: list[dict] = [
        {
            "createShape": {
                "objectId": element_id,
                "shapeType": params.shape_type,
                "elementProperties": {
                    "pageObjectId": params.slide_id,
                    "size": {
                        "width": {"magnitude": params.width, "unit": "PT"},
                        "height": {"magnitude": params.height, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": params.x,
                        "translateY": params.y,
                        "unit": "PT",
                    },
                },
            }
        }
    ]

    if params.text:
        requests.append(
            {
                "insertText": {
                    "objectId": element_id,
                    "insertionIndex": 0,
                    "text": params.text,
                }
            }
        )

    body = {"requests": requests}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return InsertElementResult(success=False, error=str(exc))

    if not resp.is_success:
        return InsertElementResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    return InsertElementResult(
        success=True,
        presentation_id=params.presentation_id,
        element_id=element_id,
    )


@tool(
    scopes=SCOPES["google_slides_update_table_cell"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_update_table_cell(
    params: UpdateTableCellParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> UpdateTableCellResult:
    """Update text in a table cell within a presentation."""
    cell_location = {
        "rowIndex": params.row,
        "columnIndex": params.column,
    }

    requests: list[dict] = [
        {
            "deleteText": {
                "objectId": params.table_id,
                "cellLocation": cell_location,
                "textRange": {"type": "ALL"},
            }
        },
        {
            "insertText": {
                "objectId": params.table_id,
                "cellLocation": cell_location,
                "insertionIndex": 0,
                "text": params.text,
            }
        },
    ]

    body = {"requests": requests}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return UpdateTableCellResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateTableCellResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    return UpdateTableCellResult(
        success=True,
        presentation_id=params.presentation_id,
        table_id=params.table_id,
        row=params.row,
        column=params.column,
    )


@tool(
    scopes=SCOPES["google_slides_format_text"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_format_text(
    params: FormatTextParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> FormatTextResult:
    """Format text style in a shape or text box."""
    # Build the text range.
    text_range: dict
    if params.start_index is not None and params.end_index is not None:
        text_range = {
            "type": "FIXED_RANGE",
            "startIndex": params.start_index,
            "endIndex": params.end_index,
        }
    elif params.start_index is not None:
        text_range = {
            "type": "FROM_START_INDEX",
            "startIndex": params.start_index,
        }
    else:
        text_range = {"type": "ALL"}

    # Collect style properties and field mask entries.
    style: dict = {}
    fields: list[str] = []

    if params.bold is not None:
        style["bold"] = params.bold
        fields.append("bold")
    if params.italic is not None:
        style["italic"] = params.italic
        fields.append("italic")
    if params.font_size is not None:
        style["fontSize"] = {"magnitude": params.font_size, "unit": "PT"}
        fields.append("fontSize")
    if params.foreground_color is not None:
        hex_color = params.foreground_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        style["foregroundColor"] = {"opaqueColor": {"rgbColor": {"red": r, "green": g, "blue": b}}}
        fields.append("foregroundColor")

    if not fields:
        return FormatTextResult(
            success=False,
            error="No formatting options provided.",
        )

    body = {
        "requests": [
            {
                "updateTextStyle": {
                    "objectId": params.object_id,
                    "textRange": text_range,
                    "style": style,
                    "fields": ",".join(fields),
                }
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return FormatTextResult(success=False, error=str(exc))

    if not resp.is_success:
        return FormatTextResult(
            success=False,
            error=f"Slides API error {resp.status_code}: {resp.text}",
        )

    return FormatTextResult(
        success=True,
        presentation_id=params.presentation_id,
        object_id=params.object_id,
    )


@tool(
    scopes=SCOPES["google_slides_insert_image"],
    api_docs="https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate",
    provider="google",
    service="google_slides",
)
async def google_slides_insert_image(
    params: InsertImageParams,
    *,
    token: str,
    base_url: str = _SLIDES_BASE_URL,
) -> InsertImageResult:
    """Insert an image onto a slide in a Google Slides presentation."""
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

        image_id = f"image_{uuid.uuid4().hex[:8]}"
        batch_body = {
            "requests": [
                {
                    "createImage": {
                        "objectId": image_id,
                        "url": public_url,
                        "elementProperties": {
                            "pageObjectId": params.slide_id,
                            "size": {
                                "width": {"magnitude": params.width, "unit": "PT"},
                                "height": {"magnitude": params.height, "unit": "PT"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": params.x,
                                "translateY": params.y,
                                "unit": "PT",
                            },
                        },
                    }
                }
            ]
        }

        try:
            resp = await client.post(
                f"{base_url}/{params.presentation_id}:batchUpdate",
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
                error=f"Slides API error {resp.status_code}: {resp.text}",
                drive_file_id=drive_file_id,
            )

        return InsertImageResult(
            success=True,
            presentation_id=params.presentation_id,
            image_id=image_id,
            filename=filename,
            drive_file_id=drive_file_id,
        )


async def _cleanup_drive_file(file_id: str, token: str, *, client: httpx.AsyncClient) -> None:
    """Best-effort cleanup of an uploaded Drive file after insert failure."""
    with contextlib.suppress(httpx.HTTPError):
        await delete_drive_file(file_id, token, client=client)
