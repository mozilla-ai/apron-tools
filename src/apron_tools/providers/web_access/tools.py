"""web_access tool functions backed by the Tabstack Python SDK.

The SDK provides streamed research responses over Server-Sent Events and a
JSON extraction endpoint. All URLs supplied by the caller are passed through
:func:`validate_url` before any network activity to prevent SSRF against
loopback, private, link-local, and cloud metadata addresses.
"""

from __future__ import annotations

import json
import logging

from tabstack import AsyncTabstack

from apron_tools.providers.web_access.ssrf import validate_url
from apron_tools.providers.web_access.types import (
    ExtractJsonParams,
    ExtractJsonResult,
    ResearchParams,
    ResearchResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_log = logging.getLogger(__name__)

_API_DOCS = "https://github.com/Mozilla-Ocho/tabstack-python/blob/main/api.md"

# Covers research (fast ~15-30s) and extract (~5-20s) with comfortable headroom.
_CLIENT_TIMEOUT = 90.0


def _make_client(token: str) -> AsyncTabstack:
    """Construct an AsyncTabstack client authenticated with *token*."""
    return AsyncTabstack(api_key=token, timeout=_CLIENT_TIMEOUT)


def _report_from_extra(extra: dict) -> str | None:
    """Pull a report/result string out of a ResearchEvent's model_extra.

    Tabstack's completion event carries the final report in
    ``model_extra["report"]`` — either as a plain string or a nested dict
    with ``content``/``result`` fields. Intermediate events may supply a
    ``result`` key instead. Returns None when no usable payload is present.
    """
    report = extra.get("report")
    if isinstance(report, str) and report:
        return report
    if isinstance(report, dict):
        return report.get("content") or report.get("result") or json.dumps(report)
    result = extra.get("result")
    if isinstance(result, str) and result:
        return result
    if isinstance(result, dict):
        return result.get("content") or json.dumps(result)
    return None


async def _collect_research_report(stream) -> tuple[str, str | None]:
    """Consume a Tabstack research stream and return (report, error).

    Iterates every event, treats any message containing the word "error" as
    a terminal failure, and otherwise returns the first usable report payload
    or — failing that — the payload of the last event.
    """
    last_extra: dict = {}
    async for event in stream:
        extra = event.model_extra or {}
        msg = extra.get("message", "")
        _log.debug("Tabstack research event: %s", msg)

        if "error" in msg.lower():
            return "", msg

        report = _report_from_extra(extra)
        if report:
            return report, None

        last_extra = extra

    final = _report_from_extra(last_extra)
    if final:
        return final, None
    return "", None


@tool(
    scopes=SCOPES["web_access_research"],
    api_docs=_API_DOCS,
    provider="web_access",
)
async def web_access_research(
    params: ResearchParams,
    *,
    token: str,
    client: AsyncTabstack | None = None,
) -> ResearchResult:
    """Execute multi-source web research via the Tabstack agent."""
    owns_client = client is None
    tabstack_client = client or _make_client(token)

    try:
        try:
            stream = await tabstack_client.agent.research(query=params.query, mode=params.mode)
        except Exception as exc:
            _log.exception("Tabstack research request failed")
            return ResearchResult(success=False, error=f"Error performing research: {exc}")

        try:
            report, err = await _collect_research_report(stream)
        except Exception as exc:
            _log.exception("Tabstack research stream failed")
            return ResearchResult(success=False, error=f"Error performing research: {exc}")

        if err is not None:
            return ResearchResult(success=False, error=err)

        if not report:
            return ResearchResult(success=False, error="No research results found.")

        return ResearchResult(success=True, report=report)
    finally:
        if owns_client:
            await tabstack_client.close()


@tool(
    scopes=SCOPES["web_access_extract_json"],
    api_docs=_API_DOCS,
    provider="web_access",
)
async def web_access_extract_json(
    params: ExtractJsonParams,
    *,
    token: str,
    client: AsyncTabstack | None = None,
) -> ExtractJsonResult:
    """Extract structured data from a web page using a JSON Schema."""
    url_error = validate_url(params.url)
    if url_error:
        return ExtractJsonResult(success=False, error=url_error)

    try:
        schema = json.loads(params.json_schema)
    except json.JSONDecodeError as exc:
        return ExtractJsonResult(
            success=False,
            error=f"Invalid JSON schema: {exc.msg} (line {exc.lineno}, column {exc.colno})",
        )

    owns_client = client is None
    tabstack_client = client or _make_client(token)

    try:
        try:
            data = await tabstack_client.extract.json(
                url=params.url,
                json_schema=schema,
                effort=params.effort,
            )
        except Exception as exc:
            _log.exception("Tabstack extract_json request failed")
            return ExtractJsonResult(success=False, error=f"Error extracting data: {exc}")

        serialised = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        return ExtractJsonResult(success=True, data=serialised)
    finally:
        if owns_client:
            await tabstack_client.close()
