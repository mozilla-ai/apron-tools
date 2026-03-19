"""Microsoft Excel tool functions for interacting with the Graph REST API."""

from __future__ import annotations

import re

import httpx

from any_tool.providers.microsoft.excel.types import (
    AddWorksheetParams,
    AddWorksheetResult,
    AppendRowParams,
    AppendRowResult,
    CreateWorkbookParams,
    CreateWorkbookResult,
    DriveItem,
    GetWorkbookInfoParams,
    GetWorkbookInfoResult,
    ListWorkbooksParams,
    ListWorkbooksResult,
    RangeData,
    ReadWorksheetParams,
    ReadWorksheetResult,
    UpdateWorksheetParams,
    UpdateWorksheetResult,
    WorksheetSummary,
)
from any_tool.tool import tool

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0

_EXCEL_EXTENSIONS = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _is_excel_file(name: str) -> bool:
    """Check whether a filename has a recognised Excel extension."""
    lower = name.lower()
    return any(lower.endswith(ext) for ext in _EXCEL_EXTENSIONS)


def _col_letter(n: int) -> str:
    """Convert a zero-based column index to an Excel column letter."""
    result = ""
    while n >= 0:
        result = chr((n % 26) + 65) + result
        n = (n // 26) - 1
    return result


def _strip_sheet_prefix(address: str) -> str:
    """Strip the worksheet prefix from a range address."""
    if "!" in address:
        return address.split("!")[-1]
    return address


def _last_row_from_address(address: str) -> int:
    """Extract the last row number from a range address string."""
    range_part = _strip_sheet_prefix(address)
    last_cell = range_part.split(":")[-1] if ":" in range_part else range_part
    match = re.search(r"\d+", last_cell)
    return int(match.group()) if match else 0


@tool(
    scopes=SCOPES["microsoft_excel_list_workbooks"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-search",
    provider="microsoft_excel",
)
async def microsoft_excel_list_workbooks(
    params: ListWorkbooksParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListWorkbooksResult:
    """List Excel workbooks accessible by the user in OneDrive."""
    search_url = f"{base_url}/me/drive/root/search(q='xls')"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                search_url,
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ListWorkbooksResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListWorkbooksResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    items = [DriveItem.model_validate(item) for item in data.get("value", []) if _is_excel_file(item.get("name", ""))]
    return ListWorkbooksResult(success=True, workbooks=items[: params.max_results])


@tool(
    scopes=SCOPES["microsoft_excel_get_workbook_info"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/workbook-list-worksheets",
    provider="microsoft_excel",
)
async def microsoft_excel_get_workbook_info(
    params: GetWorkbookInfoParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> GetWorkbookInfoResult:
    """Get information about an Excel workbook including its worksheets."""
    item_url = f"{base_url}/me/drive/items/{params.item_id}"
    worksheets_url = f"{item_url}/workbook/worksheets"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            item_resp = await client.get(
                item_url,
                headers=_headers(token),
                params={"$select": "id,name,size,webUrl,createdDateTime,lastModifiedDateTime"},
            )
            if not item_resp.is_success:
                return GetWorkbookInfoResult(
                    success=False,
                    error=f"Graph API error {item_resp.status_code}: {item_resp.text}",
                )

            item = DriveItem.model_validate(item_resp.json())

            ws_resp = await client.get(
                worksheets_url,
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetWorkbookInfoResult(success=False, error=str(exc))

    worksheets: list[WorksheetSummary] = []
    if ws_resp.is_success:
        ws_data = ws_resp.json()
        worksheets = [WorksheetSummary.model_validate(ws) for ws in ws_data.get("value", [])]

    return GetWorkbookInfoResult(success=True, item=item, worksheets=worksheets)


@tool(
    scopes=SCOPES["microsoft_excel_read_worksheet"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/range-usedrange",
    provider="microsoft_excel",
)
async def microsoft_excel_read_worksheet(
    params: ReadWorksheetParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadWorksheetResult:
    """Read data from an Excel worksheet."""
    wb_base = f"{base_url}/me/drive/items/{params.item_id}/workbook/worksheets/{params.worksheet_name}"

    url = f"{wb_base}/range(address='{params.range_address}')" if params.range_address else f"{wb_base}/usedRange"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
    except httpx.HTTPError as exc:
        return ReadWorksheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadWorksheetResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    range_data = RangeData.model_validate(resp.json())
    return ReadWorksheetResult(success=True, range_data=range_data)


@tool(
    scopes=SCOPES["microsoft_excel_update_worksheet"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/range-update",
    provider="microsoft_excel",
)
async def microsoft_excel_update_worksheet(
    params: UpdateWorksheetParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> UpdateWorksheetResult:
    """Update data in an Excel worksheet."""
    url = (
        f"{base_url}/me/drive/items/{params.item_id}"
        f"/workbook/worksheets/{params.worksheet_name}"
        f"/range(address='{params.range_address}')"
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.patch(
                url,
                headers=_headers(token, content_type=True),
                json={"values": params.values},
            )
    except httpx.HTTPError as exc:
        return UpdateWorksheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateWorksheetResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    range_data = RangeData.model_validate(resp.json())
    return UpdateWorksheetResult(success=True, range_data=range_data)


@tool(
    scopes=SCOPES["microsoft_excel_append_row"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/range-update",
    provider="microsoft_excel",
)
async def microsoft_excel_append_row(
    params: AppendRowParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> AppendRowResult:
    """Append rows to the end of used data in an Excel worksheet."""
    if not params.values or not params.values[0]:
        return AppendRowResult(success=False, error="No data provided to append.")

    wb_base = f"{base_url}/me/drive/items/{params.item_id}/workbook/worksheets/{params.worksheet_name}"

    # Check for a table first; prefer the table rows/add endpoint.
    tables_url = f"{wb_base}/tables"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            tables_resp = await client.get(tables_url, headers=_headers(token))
            if tables_resp.is_success:
                tables = tables_resp.json().get("value", [])
                if tables:
                    table_name = tables[0].get("name", "")
                    if table_name:
                        add_url = f"{wb_base}/tables/{table_name}/rows/add"
                        add_resp = await client.post(
                            add_url,
                            headers=_headers(token, content_type=True),
                            json={"index": None, "values": params.values},
                        )
                        if not add_resp.is_success:
                            return AppendRowResult(
                                success=False,
                                error=f"Graph API error {add_resp.status_code}: {add_resp.text}",
                            )
                        row_data = add_resp.json()
                        range_data = RangeData(
                            address=f"table:{table_name}",
                            row_count=len(params.values),
                            column_count=len(params.values[0]),
                            cell_count=len(params.values) * len(params.values[0]),
                            values=row_data.get("values", params.values),
                        )
                        return AppendRowResult(success=True, range_data=range_data)

            # Fallback: determine the next empty row from the used range.
            used_range_url = f"{wb_base}/usedRange"
            used_resp = await client.get(used_range_url, headers=_headers(token))
    except httpx.HTTPError as exc:
        return AppendRowResult(success=False, error=str(exc))

    start_row = 1
    if used_resp.is_success:
        used_data = used_resp.json()
        address = used_data.get("address", "")
        last_row = _last_row_from_address(address)
        # Check whether the worksheet is effectively empty.
        cell_values = used_data.get("values", [])
        is_empty = all(cell is None or str(cell).strip() == "" for row in cell_values for cell in row)
        if last_row > 0 and not (is_empty and last_row == 1):
            start_row = last_row + 1

    num_rows = len(params.values)
    num_cols = len(params.values[0])
    end_col = _col_letter(num_cols - 1)
    end_row = start_row + num_rows - 1
    target_range = f"A{start_row}:{end_col}{end_row}"

    patch_url = f"{wb_base}/range(address='{target_range}')"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            patch_resp = await client.patch(
                patch_url,
                headers=_headers(token, content_type=True),
                json={"values": params.values},
            )
    except httpx.HTTPError as exc:
        return AppendRowResult(success=False, error=str(exc))

    if not patch_resp.is_success:
        return AppendRowResult(
            success=False,
            error=f"Graph API error {patch_resp.status_code}: {patch_resp.text}",
        )

    range_data = RangeData.model_validate(patch_resp.json())
    return AppendRowResult(success=True, range_data=range_data)


@tool(
    scopes=SCOPES["microsoft_excel_create_workbook"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-list-children",
    provider="microsoft_excel",
)
async def microsoft_excel_create_workbook(
    params: CreateWorkbookParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreateWorkbookResult:
    """Create a new Excel workbook in OneDrive."""
    filename = params.name if params.name.endswith(".xlsx") else f"{params.name}.xlsx"

    if params.folder_path == "root":
        session_url = f"{base_url}/me/drive/root:/{filename}:/workbook/createSession"
    else:
        session_url = f"{base_url}/me/drive/root:/{params.folder_path}/{filename}:/workbook/createSession"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            session_resp = await client.post(
                session_url,
                headers=_headers(token, content_type=True),
                json={"persistChanges": True},
            )

            if not session_resp.is_success:
                return CreateWorkbookResult(
                    success=False,
                    error=f"Graph API error {session_resp.status_code}: {session_resp.text}",
                )

            # Retrieve the created file metadata.
            file_path = filename if params.folder_path == "root" else f"{params.folder_path}/{filename}"

            file_resp = await client.get(
                f"{base_url}/me/drive/root:/{file_path}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return CreateWorkbookResult(success=False, error=str(exc))

    if not file_resp.is_success:
        return CreateWorkbookResult(
            success=False,
            error=f"Graph API error {file_resp.status_code}: {file_resp.text}",
        )

    item = DriveItem.model_validate(file_resp.json())
    return CreateWorkbookResult(success=True, item=item)


@tool(
    scopes=SCOPES["microsoft_excel_add_worksheet"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/worksheetcollection-add",
    provider="microsoft_excel",
)
async def microsoft_excel_add_worksheet(
    params: AddWorksheetParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> AddWorksheetResult:
    """Add a new worksheet to an existing Excel workbook."""
    url = f"{base_url}/me/drive/items/{params.item_id}/workbook/worksheets/add"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers=_headers(token, content_type=True),
                json={"name": params.name},
            )
    except httpx.HTTPError as exc:
        return AddWorksheetResult(success=False, error=str(exc))

    if not resp.is_success:
        return AddWorksheetResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    worksheet = WorksheetSummary.model_validate(resp.json())
    return AddWorksheetResult(success=True, worksheet=worksheet)
