"""Notion tool functions for interacting with the Notion API."""

from __future__ import annotations

import re

import httpx

from any_tool.providers.notion.types import (
    CreateDatabaseParams,
    CreateDatabaseResult,
    CreateOrUpdateDatabaseEntryParams,
    CreateOrUpdateDatabaseEntryResult,
    CreatePageParams,
    CreatePageResult,
    DatabaseObject,
    ExploreTeamspaceParams,
    ExploreTeamspaceResult,
    GetDatabaseEntryParams,
    GetDatabaseEntryResult,
    GetDatabaseSchemaParams,
    GetDatabaseSchemaResult,
    PageObject,
    QueryDatabaseParams,
    QueryDatabaseResult,
    ReadPageParams,
    ReadPageResult,
    UpdateDatabaseSchemaParams,
    UpdateDatabaseSchemaResult,
    UpdatePageParams,
    UpdatePageResult,
)
from any_tool.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.notion.com"
_TIMEOUT = 60.0
_NOTION_VERSION = "2026-03-11"


def _headers(token: str) -> dict[str, str]:
    """Build authorization and versioning headers for a Notion API request."""
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Markdown-to-blocks helpers (ported from Octonous)
# ---------------------------------------------------------------------------


def _parse_rich_text(text: str) -> list[dict[str, object]]:
    """Parse inline markdown formatting into Notion rich text objects."""
    if not text:
        return []

    segments: list[dict[str, object]] = []
    # Match ***bold+italic***, **bold**, *italic* in precedence order.
    pattern = r"\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*"

    last_end = 0
    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            plain = text[last_end : match.start()]
            if plain:
                segments.append({"type": "text", "text": {"content": plain}})

        if match.group(1) is not None:
            segments.append(
                {
                    "type": "text",
                    "text": {"content": match.group(1)},
                    "annotations": {"bold": True, "italic": True},
                }
            )
        elif match.group(2) is not None:
            segments.append(
                {
                    "type": "text",
                    "text": {"content": match.group(2)},
                    "annotations": {"bold": True},
                }
            )
        elif match.group(3) is not None:
            segments.append(
                {
                    "type": "text",
                    "text": {"content": match.group(3)},
                    "annotations": {"italic": True},
                }
            )

        last_end = match.end()

    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            segments.append({"type": "text", "text": {"content": remaining}})

    if not segments:
        segments.append({"type": "text", "text": {"content": text}})

    return segments


def _parse_markdown_to_blocks(content: str) -> list[dict[str, object]]:
    """Convert markdown content to a list of Notion block objects."""
    if not content:
        return []

    lines = content.split("\n")
    blocks: list[dict[str, object]] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Divider.
        if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", stripped):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Headings (check ### before ## before #).
        if stripped.startswith("### "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": _parse_rich_text(stripped[4:])},
                }
            )
            i += 1
            continue

        if stripped.startswith("## "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": _parse_rich_text(stripped[3:])},
                }
            )
            i += 1
            continue

        if stripped.startswith("# "):
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": _parse_rich_text(stripped[2:])},
                }
            )
            i += 1
            continue

        # Bulleted list item.
        if stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": _parse_rich_text(stripped[2:])},
                }
            )
            i += 1
            continue

        # Numbered list item.
        numbered_match = re.match(r"^\d+\.\s+(.*)", stripped)
        if numbered_match:
            blocks.append(
                {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": _parse_rich_text(numbered_match.group(1))},
                }
            )
            i += 1
            continue

        # Callout (blockquote syntax).
        if stripped.startswith("> "):
            callout_lines = [stripped[2:]]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("> "):
                callout_lines.append(lines[i].strip()[2:])
                i += 1
            full_text = "\n".join(callout_lines)
            blocks.append(
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": _parse_rich_text(full_text),
                        "icon": {"type": "emoji", "emoji": "\U0001f4a1"},
                    },
                }
            )
            continue

        # Default: paragraph.
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _parse_rich_text(stripped)},
            }
        )
        i += 1

    return blocks


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["explore_teamspace"],
    api_docs="https://developers.notion.com/reference/post-search",
    provider="notion",
)
async def explore_teamspace(
    params: ExploreTeamspaceParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreTeamspaceResult:
    """Search for pages and databases in the Notion teamspace."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            pages_resp = await client.post(
                f"{base_url}/v1/search",
                headers=_headers(token),
                json={
                    "filter": {"property": "object", "value": "page"},
                    "page_size": params.page_size,
                },
            )
            if not pages_resp.is_success:
                return ExploreTeamspaceResult(
                    success=False,
                    error=f"Notion API error {pages_resp.status_code}: {pages_resp.text}",
                )
            pages_data = pages_resp.json()

            dbs_resp = await client.post(
                f"{base_url}/v1/search",
                headers=_headers(token),
                json={
                    "filter": {"property": "object", "value": "database"},
                    "page_size": params.page_size,
                },
            )
            if not dbs_resp.is_success:
                return ExploreTeamspaceResult(
                    success=False,
                    error=f"Notion API error {dbs_resp.status_code}: {dbs_resp.text}",
                )
            dbs_data = dbs_resp.json()

    except httpx.HTTPError as exc:
        return ExploreTeamspaceResult(success=False, error=str(exc))

    pages = [PageObject.model_validate(p) for p in pages_data.get("results", [])]
    databases = [DatabaseObject.model_validate(d) for d in dbs_data.get("results", [])]

    return ExploreTeamspaceResult(success=True, pages=pages, databases=databases)


@tool(
    scopes=SCOPES["create_page"],
    api_docs="https://developers.notion.com/reference/post-page",
    provider="notion",
)
async def create_page(
    params: CreatePageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreatePageResult:
    """Create a new page in Notion under a parent page."""
    payload: dict[str, object] = {
        "parent": {"page_id": params.parent_page_id},
        "properties": {"title": {"title": [{"text": {"content": params.title}}]}},
    }

    blocks = _parse_markdown_to_blocks(params.content) if params.content else []
    if blocks:
        payload["children"] = blocks[:100]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/v1/pages",
                headers=_headers(token),
                json=payload,
            )
            if not response.is_success:
                return CreatePageResult(
                    success=False,
                    error=f"Notion API error {response.status_code}: {response.text}",
                )
            data = response.json()
            page_id = data.get("id", "")

            # Append remaining blocks in batches of 100.
            remaining = blocks[100:]
            for batch_start in range(0, len(remaining), 100):
                batch = remaining[batch_start : batch_start + 100]
                append_resp = await client.patch(
                    f"{base_url}/v1/blocks/{page_id}/children",
                    headers=_headers(token),
                    json={"children": batch},
                )
                if not append_resp.is_success:
                    return CreatePageResult(
                        success=False,
                        error=f"Page created (id={page_id}) but failed to append blocks: {append_resp.text}",
                    )

    except httpx.HTTPError as exc:
        return CreatePageResult(success=False, error=str(exc))

    return CreatePageResult.model_validate(data)


@tool(
    scopes=SCOPES["update_page"],
    api_docs="https://developers.notion.com/reference/patch-block-children",
    provider="notion",
)
async def update_page(
    params: UpdatePageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdatePageResult:
    """Append content blocks to an existing Notion page."""
    blocks = _parse_markdown_to_blocks(params.content)
    if not blocks:
        return UpdatePageResult(success=True, page_id=params.page_id, blocks_appended=0)

    total_appended = 0
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for batch_start in range(0, len(blocks), 100):
                batch = blocks[batch_start : batch_start + 100]
                response = await client.patch(
                    f"{base_url}/v1/blocks/{params.page_id}/children",
                    headers=_headers(token),
                    json={"children": batch},
                )
                if not response.is_success:
                    return UpdatePageResult(
                        success=False,
                        error=f"Notion API error {response.status_code}: {response.text}",
                    )
                total_appended += len(batch)
    except httpx.HTTPError as exc:
        return UpdatePageResult(success=False, error=str(exc))

    return UpdatePageResult(success=True, page_id=params.page_id, blocks_appended=total_appended)


@tool(
    scopes=SCOPES["read_page"],
    api_docs="https://developers.notion.com/reference/retrieve-a-page",
    provider="notion",
)
async def read_page(
    params: ReadPageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ReadPageResult:
    """Read the content of a Notion page including its blocks."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            page_resp = await client.get(
                f"{base_url}/v1/pages/{params.page_id}",
                headers=_headers(token),
            )
            if not page_resp.is_success:
                return ReadPageResult(
                    success=False,
                    error=f"Notion API error {page_resp.status_code}: {page_resp.text}",
                )
            page_data = page_resp.json()

            blocks_resp = await client.get(
                f"{base_url}/v1/blocks/{params.page_id}/children",
                headers=_headers(token),
                params={"page_size": 100},
            )
            if not blocks_resp.is_success:
                return ReadPageResult(
                    success=False,
                    error=f"Notion API error {blocks_resp.status_code}: {blocks_resp.text}",
                )
            blocks_data = blocks_resp.json()

    except httpx.HTTPError as exc:
        return ReadPageResult(success=False, error=str(exc))

    from any_tool.providers.notion.types import BlockObject

    page = PageObject.model_validate(page_data)
    block_list = [BlockObject.model_validate(b) for b in blocks_data.get("results", [])]

    return ReadPageResult(success=True, page=page, blocks=block_list)


@tool(
    scopes=SCOPES["get_database_schema"],
    api_docs="https://developers.notion.com/reference/retrieve-database",
    provider="notion",
)
async def get_database_schema(
    params: GetDatabaseSchemaParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetDatabaseSchemaResult:
    """Retrieve the schema of a Notion database."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/v1/databases/{params.database_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetDatabaseSchemaResult(success=False, error=str(exc))

    if not response.is_success:
        return GetDatabaseSchemaResult(
            success=False,
            error=f"Notion API error {response.status_code}: {response.text}",
        )

    db = DatabaseObject.model_validate(response.json())
    return GetDatabaseSchemaResult(success=True, database=db)


@tool(
    scopes=SCOPES["query_database"],
    api_docs="https://developers.notion.com/reference/query-a-data-source",
    provider="notion",
)
async def query_database(
    params: QueryDatabaseParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> QueryDatabaseResult:
    """Query a Notion database via the data sources endpoint."""
    payload: dict[str, object] = {"page_size": min(params.page_size, 100)}
    if params.filter is not None:
        payload["filter"] = params.filter
    if params.sorts is not None:
        payload["sorts"] = params.sorts
    else:
        payload["sorts"] = [{"timestamp": "last_edited_time", "direction": "descending"}]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/v1/data_sources/{params.data_source_id}/query",
                headers=_headers(token),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return QueryDatabaseResult(success=False, error=str(exc))

    if not response.is_success:
        return QueryDatabaseResult(
            success=False,
            error=f"Notion API error {response.status_code}: {response.text}",
        )

    data = response.json()
    results = [PageObject.model_validate(p) for p in data.get("results", [])]

    return QueryDatabaseResult(
        success=True,
        results=results,
        has_more=data.get("has_more", False),
        next_cursor=data.get("next_cursor"),
    )


@tool(
    scopes=SCOPES["get_database_entry"],
    api_docs="https://developers.notion.com/reference/retrieve-a-page",
    provider="notion",
)
async def get_database_entry(
    params: GetDatabaseEntryParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetDatabaseEntryResult:
    """Retrieve a single database entry with its properties and content blocks."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            page_resp = await client.get(
                f"{base_url}/v1/pages/{params.page_id}",
                headers=_headers(token),
            )
            if not page_resp.is_success:
                return GetDatabaseEntryResult(
                    success=False,
                    error=f"Notion API error {page_resp.status_code}: {page_resp.text}",
                )
            page_data = page_resp.json()

            blocks_resp = await client.get(
                f"{base_url}/v1/blocks/{params.page_id}/children",
                headers=_headers(token),
                params={"page_size": 100},
            )
            if not blocks_resp.is_success:
                return GetDatabaseEntryResult(
                    success=False,
                    error=f"Notion API error {blocks_resp.status_code}: {blocks_resp.text}",
                )
            blocks_data = blocks_resp.json()

    except httpx.HTTPError as exc:
        return GetDatabaseEntryResult(success=False, error=str(exc))

    from any_tool.providers.notion.types import BlockObject

    page = PageObject.model_validate(page_data)
    block_list = [BlockObject.model_validate(b) for b in blocks_data.get("results", [])]

    return GetDatabaseEntryResult(success=True, page=page, blocks=block_list)


@tool(
    scopes=SCOPES["create_or_update_database_entry"],
    api_docs="https://developers.notion.com/reference/post-page",
    provider="notion",
)
async def create_or_update_database_entry(
    params: CreateOrUpdateDatabaseEntryParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateOrUpdateDatabaseEntryResult:
    """Create a new database entry or update an existing one."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            if params.page_id:
                # Update existing entry.
                response = await client.patch(
                    f"{base_url}/v1/pages/{params.page_id}",
                    headers=_headers(token),
                    json={"properties": params.properties},
                )
            else:
                # Create new entry.
                response = await client.post(
                    f"{base_url}/v1/pages",
                    headers=_headers(token),
                    json={
                        "parent": {"database_id": params.database_id},
                        "properties": params.properties,
                    },
                )
    except httpx.HTTPError as exc:
        return CreateOrUpdateDatabaseEntryResult(success=False, error=str(exc))

    if not response.is_success:
        return CreateOrUpdateDatabaseEntryResult(
            success=False,
            error=f"Notion API error {response.status_code}: {response.text}",
        )

    return CreateOrUpdateDatabaseEntryResult.model_validate(response.json())


@tool(
    scopes=SCOPES["create_database"],
    api_docs="https://developers.notion.com/reference/create-a-database",
    provider="notion",
)
async def create_database(
    params: CreateDatabaseParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateDatabaseResult:
    """Create a new Notion database under a parent page."""
    properties = params.properties if params.properties else {"Name": {"title": {}}}

    payload: dict[str, object] = {
        "parent": {"type": "page_id", "page_id": params.parent_page_id},
        "title": [{"text": {"content": params.title}}],
        "properties": properties,
    }
    if params.description:
        payload["description"] = [{"text": {"content": params.description}}]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/v1/databases",
                headers=_headers(token),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return CreateDatabaseResult(success=False, error=str(exc))

    if not response.is_success:
        return CreateDatabaseResult(
            success=False,
            error=f"Notion API error {response.status_code}: {response.text}",
        )

    return CreateDatabaseResult.model_validate(response.json())


@tool(
    scopes=SCOPES["update_database_schema"],
    api_docs="https://developers.notion.com/reference/update-a-database",
    provider="notion",
)
async def update_database_schema(
    params: UpdateDatabaseSchemaParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateDatabaseSchemaResult:
    """Update a Notion database schema (title, properties, or description)."""
    update_data: dict[str, object] = {}

    if params.title is not None:
        update_data["title"] = [{"text": {"content": params.title}}]
    if params.description is not None:
        update_data["description"] = [{"text": {"content": params.description}}]
    if params.properties is not None:
        update_data["properties"] = params.properties

    if not update_data:
        return UpdateDatabaseSchemaResult(
            success=False,
            error="No updates provided. Supply at least one of: title, properties, description.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.patch(
                f"{base_url}/v1/databases/{params.database_id}",
                headers=_headers(token),
                json=update_data,
            )
    except httpx.HTTPError as exc:
        return UpdateDatabaseSchemaResult(success=False, error=str(exc))

    if not response.is_success:
        return UpdateDatabaseSchemaResult(
            success=False,
            error=f"Notion API error {response.status_code}: {response.text}",
        )

    return UpdateDatabaseSchemaResult.model_validate(response.json())
