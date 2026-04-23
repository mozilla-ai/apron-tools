"""Tests for web_access tool functions."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tabstack.types.research_event import (
    V1ResearchEventComplete,
    V1ResearchEventCompleteData,
    V1ResearchEventError,
    V1ResearchEventErrorData,
    V1ResearchEventStart,
    V1ResearchEventStartData,
)

from apron_tools.providers.web_access.tools import (
    web_access_extract_json,
    web_access_research,
)
from apron_tools.providers.web_access.types import (
    ExtractJsonParams,
    ExtractJsonResult,
    ResearchParams,
    ResearchResult,
)

_TOKEN = "tbst_test_token_abc123"


def _start_event(message: str, *, timestamp: float = 0.0) -> V1ResearchEventStart:
    """Build an in-progress research event carrying *message*."""
    data = V1ResearchEventStartData.model_construct(message=message, timestamp=timestamp)
    return V1ResearchEventStart.model_construct(event="start", data=data)


def _complete_event(
    *,
    message: str = "Research complete",
    report: Any,
    timestamp: float = 0.0,
) -> V1ResearchEventComplete:
    """Build a terminal ``complete`` research event with *report* payload."""
    data = V1ResearchEventCompleteData.model_construct(
        message=message,
        report=report,
        timestamp=timestamp,
        metadata=None,
    )
    return V1ResearchEventComplete.model_construct(event="complete", data=data)


def _error_event(message: str, *, timestamp: float = 0.0) -> V1ResearchEventError:
    """Build a terminal ``error`` research event."""
    data = V1ResearchEventErrorData.model_construct(
        error=None,
        message=message,
        timestamp=timestamp,
        activity=None,
        iteration=None,
    )
    return V1ResearchEventError.model_construct(event="error", data=data)


class _AsyncStream:
    """Minimal async iterator standing in for the Tabstack SSE stream."""

    def __init__(self, events: list[Any]):
        self._events = iter(events)

    def __aiter__(self) -> _AsyncStream:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _mock_client(
    *,
    research_stream: _AsyncStream | None = None,
    research_side_effect: BaseException | None = None,
    extract_result: Any = None,
    extract_side_effect: BaseException | None = None,
) -> MagicMock:
    """Build a mock AsyncTabstack client with research/extract/close wired."""
    client = MagicMock()
    if research_side_effect is not None:
        client.agent.research = AsyncMock(side_effect=research_side_effect)
    else:
        client.agent.research = AsyncMock(return_value=research_stream)

    if extract_side_effect is not None:
        client.extract.json = AsyncMock(side_effect=extract_side_effect)
    else:
        client.extract.json = AsyncMock(return_value=extract_result)

    client.close = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# web_access_research
# ---------------------------------------------------------------------------


class TestResearch:
    async def test_success_returns_final_report(self) -> None:
        stream = _AsyncStream(
            [
                _start_event("Searching", timestamp=1.0),
                _complete_event(
                    report="Deep research result with citations.",
                    timestamp=2.0,
                ),
            ]
        )
        client = _mock_client(research_stream=stream)

        result = await web_access_research(
            ResearchParams(query="What is AI?"),
            token=_TOKEN,
            client=client,
        )

        assert isinstance(result, ResearchResult)
        assert result.success is True
        assert result.report == "Deep research result with citations."
        assert str(result) == "Deep research result with citations."
        client.agent.research.assert_awaited_once_with(query="What is AI?", mode="fast")
        # When a client is injected the tool must NOT close it.
        client.close.assert_not_called()

    async def test_mode_forwarded_to_sdk(self) -> None:
        stream = _AsyncStream([_complete_event(report="x")])
        client = _mock_client(research_stream=stream)

        await web_access_research(
            ResearchParams(query="q", mode="balanced"),
            token=_TOKEN,
            client=client,
        )

        client.agent.research.assert_awaited_once_with(query="q", mode="balanced")

    async def test_error_event_returns_failure(self) -> None:
        stream = _AsyncStream([_error_event("Research error: upstream 503")])
        client = _mock_client(research_stream=stream)

        result = await web_access_research(ResearchParams(query="q"), token=_TOKEN, client=client)

        assert result.success is False
        assert result.error is not None
        assert "error" in result.error.lower()

    async def test_empty_stream_returns_no_results(self) -> None:
        client = _mock_client(research_stream=_AsyncStream([]))

        result = await web_access_research(ResearchParams(query="q"), token=_TOKEN, client=client)

        assert result.success is False
        assert "No research results" in (result.error or "")

    async def test_sdk_request_exception(self) -> None:
        client = _mock_client(research_side_effect=RuntimeError("boom"))

        result = await web_access_research(ResearchParams(query="q"), token=_TOKEN, client=client)

        assert result.success is False
        assert "boom" in (result.error or "")

    async def test_report_extracted_from_nested_dict(self) -> None:
        stream = _AsyncStream([_complete_event(report={"content": "nested dict content"})])
        client = _mock_client(research_stream=stream)

        result = await web_access_research(ResearchParams(query="q"), token=_TOKEN, client=client)

        assert result.success is True
        assert result.report == "nested dict content"

    async def test_owned_client_is_closed(self) -> None:
        """When no client is injected, the tool must close the client it built."""
        fake_client = _mock_client(research_stream=_AsyncStream([_complete_event(report="ok")]))

        with patch(
            "apron_tools.providers.web_access.tools._make_client",
            return_value=fake_client,
        ) as make_client:
            result = await web_access_research(ResearchParams(query="q"), token=_TOKEN)

        assert result.success is True
        make_client.assert_called_once_with(_TOKEN)
        fake_client.close.assert_awaited_once()

    async def test_has_tool_definition(self) -> None:
        defn = web_access_research._tool_definition
        assert defn.name == "web_access_research"
        assert defn.provider == "web_access"
        assert defn.service == "web_access"
        assert defn.scopes == ["research"]
        assert defn.api_docs_url.startswith("https://")


# ---------------------------------------------------------------------------
# web_access_extract_json
# ---------------------------------------------------------------------------


class TestExtractJson:
    async def test_success_returns_serialised_json(self) -> None:
        client = _mock_client(extract_result={"title": "Example", "price": "$9.99"})

        with patch(
            "apron_tools.providers.web_access.tools.validate_url",
            return_value=None,
        ):
            result = await web_access_extract_json(
                ExtractJsonParams(
                    url="https://example.com/",
                    json_schema='{"type":"object","properties":{"title":{"type":"string"}}}',
                ),
                token=_TOKEN,
                client=client,
            )

        assert isinstance(result, ExtractJsonResult)
        assert result.success is True
        parsed = json.loads(result.data)
        assert parsed["title"] == "Example"
        assert parsed["price"] == "$9.99"

    async def test_schema_parsed_before_request(self) -> None:
        client = _mock_client(extract_result={"ok": True})

        with patch(
            "apron_tools.providers.web_access.tools.validate_url",
            return_value=None,
        ):
            await web_access_extract_json(
                ExtractJsonParams(
                    url="https://example.com/",
                    json_schema='{"type":"object"}',
                    effort="max",
                ),
                token=_TOKEN,
                client=client,
            )

        client.extract.json.assert_awaited_once()
        kwargs = client.extract.json.await_args.kwargs
        assert kwargs["url"] == "https://example.com/"
        assert kwargs["json_schema"] == {"type": "object"}
        assert kwargs["effort"] == "max"

    async def test_rejects_ssrf_url_before_client_call(self) -> None:
        """SSRF blocklist must short-circuit before the SDK is touched."""
        client = _mock_client(extract_result={"should": "not run"})

        result = await web_access_extract_json(
            ExtractJsonParams(url="http://localhost/secret", json_schema='{"type":"object"}'),
            token=_TOKEN,
            client=client,
        )

        assert result.success is False
        assert result.error is not None
        client.extract.json.assert_not_called()

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://10.0.0.5/",
            "http://169.254.1.1/",
        ],
    )
    async def test_rejects_various_unsafe_urls(self, url: str) -> None:
        client = _mock_client(extract_result={})

        result = await web_access_extract_json(
            ExtractJsonParams(url=url, json_schema='{"type":"object"}'),
            token=_TOKEN,
            client=client,
        )

        assert result.success is False
        client.extract.json.assert_not_called()

    async def test_invalid_schema_is_reported(self) -> None:
        client = _mock_client(extract_result={})
        bad_schema = "not json { with sentinel-XYZZY garbage"

        with patch(
            "apron_tools.providers.web_access.tools.validate_url",
            return_value=None,
        ):
            result = await web_access_extract_json(
                ExtractJsonParams(url="https://example.com/", json_schema=bad_schema),
                token=_TOKEN,
                client=client,
            )

        assert result.success is False
        error = result.error or ""
        assert "Invalid JSON schema" in error
        assert "line" in error and "column" in error
        # Caller-supplied schema must NOT be echoed back into the error payload.
        assert "sentinel-XYZZY" not in error
        client.extract.json.assert_not_called()

    async def test_sdk_exception_is_wrapped(self) -> None:
        client = _mock_client(extract_side_effect=RuntimeError("429 throttled"))

        with patch(
            "apron_tools.providers.web_access.tools.validate_url",
            return_value=None,
        ):
            result = await web_access_extract_json(
                ExtractJsonParams(url="https://example.com/", json_schema='{"type":"object"}'),
                token=_TOKEN,
                client=client,
            )

        assert result.success is False
        assert "429" in (result.error or "")

    async def test_owned_client_is_closed(self) -> None:
        fake_client = _mock_client(extract_result={"ok": True})

        with (
            patch(
                "apron_tools.providers.web_access.tools.validate_url",
                return_value=None,
            ),
            patch(
                "apron_tools.providers.web_access.tools._make_client",
                return_value=fake_client,
            ) as make_client,
        ):
            result = await web_access_extract_json(
                ExtractJsonParams(url="https://example.com/", json_schema='{"type":"object"}'),
                token=_TOKEN,
            )

        assert result.success is True
        make_client.assert_called_once_with(_TOKEN)
        fake_client.close.assert_awaited_once()

    async def test_has_tool_definition(self) -> None:
        defn = web_access_extract_json._tool_definition
        assert defn.name == "web_access_extract_json"
        assert defn.provider == "web_access"
        assert defn.service == "web_access"
        assert defn.scopes == ["extract"]
        assert defn.api_docs_url.startswith("https://")
