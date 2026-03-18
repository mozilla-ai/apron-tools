"""Google Sheets tool functions for interacting with the Sheets and Drive REST APIs."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from any_tool.providers.google.sheets.types import (
    AddSheetParams,
    AddSheetResult,
    AppendRowParams,
    AppendRowResult,
    CopySpreadsheetParams,
    CopySpreadsheetResult,
    CreateSpreadsheetParams,
    CreateSpreadsheetResult,
    FindRowParams,
    FindRowResult,
    ListSpreadsheetsParams,
    ListSpreadsheetsResult,
    ReadSpreadsheetParams,
    ReadSpreadsheetResult,
    SpreadsheetFile,
    UpdateSpreadsheetParams,
    UpdateSpreadsheetResult,
)
from any_tool.tool import tool

from .scopes import SCOPES

_SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
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
    scopes=SCOPES["list_spreadsheets"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/list",
    provider="google_sheets",
)
async def list_spreadsheets(
    params: ListSpreadsheetsParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> ListSpreadsheetsResult:
    """List all Google Sheets spreadsheets accessible by the user."""
    query_params = {
        "q": "mimeType='application/vnd.google-apps.spreadsheet'",
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
        return ListSpreadsheetsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListSpreadsheetsResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    files = [SpreadsheetFile.model_validate(f) for f in data.get("files", [])]
    return ListSpreadsheetsResult(success=True, files=files)


@tool(
    scopes=SCOPES["create_spreadsheet"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/create",
    provider="google_sheets",
)
async def create_spreadsheet(
    params: CreateSpreadsheetParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> CreateSpreadsheetResult:
    """Create a new Google Sheets spreadsheet."""
    body: dict = {"properties": {"title": params.title}}
    if params.sheet_names:
        body["sheets"] = [{"properties": {"title": name}} for name in params.sheet_names]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                base_url,
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateSpreadsheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateSpreadsheetResult(
            success=False,
            error=f"Sheets API error {resp.status_code}: {resp.text}",
        )

    return CreateSpreadsheetResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["copy_spreadsheet"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/copy",
    provider="google_sheets",
)
async def copy_spreadsheet(
    params: CopySpreadsheetParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> CopySpreadsheetResult:
    """Create a copy of an existing Google Sheets spreadsheet."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the original spreadsheet title from Drive.
            meta_resp = await client.get(
                f"{_DRIVE_BASE_URL}/{params.spreadsheet_id}",
                headers=_headers(token),
                params={"fields": "name", "supportsAllDrives": "true"},
            )
            if not meta_resp.is_success:
                return CopySpreadsheetResult(
                    success=False,
                    error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
                )
            original_name = meta_resp.json().get("name", "Unknown")

            # Copy via Drive API.
            copy_resp = await client.post(
                f"{_DRIVE_BASE_URL}/{params.spreadsheet_id}/copy",
                headers=_headers(token, content_type=True),
                json={"name": params.new_title},
                params={"supportsAllDrives": "true"},
            )
    except httpx.HTTPError as exc:
        return CopySpreadsheetResult(success=False, error=str(exc))

    if not copy_resp.is_success:
        return CopySpreadsheetResult(
            success=False,
            error=f"Drive API error {copy_resp.status_code}: {copy_resp.text}",
        )

    copy_data = copy_resp.json()
    return CopySpreadsheetResult(
        success=True,
        id=copy_data.get("id", ""),
        name=copy_data.get("name", params.new_title),
        original_name=original_name,
    )


@tool(
    scopes=SCOPES["read_spreadsheet"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get",
    provider="google_sheets",
)
async def read_spreadsheet(
    params: ReadSpreadsheetParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> ReadSpreadsheetResult:
    """Read data from a Google Sheets spreadsheet."""
    range_str = params.range
    title = ""
    sheet_names: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch metadata when requested or when no range is specified.
            if params.include_metadata or not range_str:
                meta_resp = await client.get(
                    f"{base_url}/{params.spreadsheet_id}",
                    headers=_headers(token),
                    params={"fields": "properties.title,sheets.properties"},
                )
                if not meta_resp.is_success:
                    return ReadSpreadsheetResult(
                        success=False,
                        error=f"Sheets API error {meta_resp.status_code}: {meta_resp.text}",
                    )
                meta_data = meta_resp.json()
                title = meta_data.get("properties", {}).get("title", "")
                sheets = meta_data.get("sheets", [])
                sheet_names = [s.get("properties", {}).get("title", "Untitled") for s in sheets]
                # Default to the first sheet when no range is provided.
                if not range_str and sheets:
                    range_str = sheets[0].get("properties", {}).get("title", "Sheet1")

            encoded_range = quote(range_str, safe="")
            values_resp = await client.get(
                f"{base_url}/{params.spreadsheet_id}/values/{encoded_range}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ReadSpreadsheetResult(success=False, error=str(exc))

    if not values_resp.is_success:
        return ReadSpreadsheetResult(
            success=False,
            error=f"Sheets API error {values_resp.status_code}: {values_resp.text}",
        )

    values_data = values_resp.json()
    return ReadSpreadsheetResult(
        success=True,
        range=values_data.get("range", range_str),
        values=values_data.get("values", []),
        title=title if params.include_metadata else "",
        sheet_names=sheet_names if params.include_metadata else [],
    )


@tool(
    scopes=SCOPES["update_spreadsheet"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update",
    provider="google_sheets",
)
async def update_spreadsheet(
    params: UpdateSpreadsheetParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> UpdateSpreadsheetResult:
    """Update values in a Google Sheets spreadsheet."""
    encoded_range = quote(params.range, safe="")
    url = f"{base_url}/{params.spreadsheet_id}/values/{encoded_range}"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.put(
                url,
                headers=_headers(token, content_type=True),
                params={"valueInputOption": "USER_ENTERED"},
                json={"range": params.range, "values": params.values},
            )
    except httpx.HTTPError as exc:
        return UpdateSpreadsheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateSpreadsheetResult(
            success=False,
            error=f"Sheets API error {resp.status_code}: {resp.text}",
        )

    return UpdateSpreadsheetResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["append_row"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/append",
    provider="google_sheets",
)
async def append_row(
    params: AppendRowParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> AppendRowResult:
    """Append rows to a Google Sheets spreadsheet."""
    encoded_range = quote(params.range, safe="")
    url = f"{base_url}/{params.spreadsheet_id}/values/{encoded_range}:append"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers=_headers(token, content_type=True),
                params={
                    "valueInputOption": "USER_ENTERED",
                    "insertDataOption": "INSERT_ROWS",
                },
                json={"range": params.range, "values": params.values},
            )
    except httpx.HTTPError as exc:
        return AppendRowResult(success=False, error=str(exc))

    if not resp.is_success:
        return AppendRowResult(
            success=False,
            error=f"Sheets API error {resp.status_code}: {resp.text}",
        )

    return AppendRowResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["add_sheet"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate",
    provider="google_sheets",
)
async def add_sheet(
    params: AddSheetParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> AddSheetResult:
    """Add a new sheet tab to an existing spreadsheet."""
    body = {"requests": [{"addSheet": {"properties": {"title": params.title}}}]}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.spreadsheet_id}:batchUpdate",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return AddSheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return AddSheetResult(
            success=False,
            error=f"Sheets API error {resp.status_code}: {resp.text}",
        )

    result = AddSheetResult.model_validate(resp.json())
    result.spreadsheet_id = params.spreadsheet_id
    return result


@tool(
    scopes=SCOPES["find_row"],
    api_docs="https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get",
    provider="google_sheets",
)
async def find_row(
    params: FindRowParams,
    *,
    token: str,
    base_url: str = _SHEETS_BASE_URL,
) -> FindRowResult:
    """Find the first row where a column matches a given value."""
    column = params.column.strip().upper()
    range_str = f"{params.sheet}!{column}:{column}"
    search_value = params.value.strip()

    encoded_range = quote(range_str, safe="")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/{params.spreadsheet_id}/values/{encoded_range}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return FindRowResult(success=False, error=str(exc))

    if not resp.is_success:
        return FindRowResult(
            success=False,
            error=f"Sheets API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    rows = data.get("values", [])

    for i, row in enumerate(rows, start=1):
        if row and str(row[0]).strip() == search_value:
            return FindRowResult(
                success=True,
                row_number=i,
                sheet=params.sheet,
                column=column,
                value=search_value,
            )

    return FindRowResult(
        success=True,
        row_number=0,
        sheet=params.sheet,
        column=column,
        value=search_value,
    )
