"""Tests for Typeform tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.typeform.tools import typeform_get_form, typeform_get_responses, typeform_list_forms
from any_tool.providers.typeform.types import (
    GetFormParams,
    GetFormResult,
    GetResponsesParams,
    GetResponsesResult,
    ListFormsParams,
    ListFormsResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "tfp_test_token_abc123"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_forms
# ---------------------------------------------------------------------------


class TestListForms:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("list_forms.json")
        httpx_mock.add_response(json=data, url="https://api.typeform.com/forms?page=1&page_size=10")

        result = await typeform_list_forms(ListFormsParams(), token=_TOKEN)

        assert isinstance(result, ListFormsResult)
        assert result.success is True
        assert result.total_items == 2
        assert len(result.items) == 2
        assert result.items[0].id == "abc123"
        assert result.items[0].title == "Customer Feedback"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_forms.json"))

        await typeform_list_forms(ListFormsParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await typeform_list_forms(ListFormsParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_list_forms._tool_definition
        assert defn.name == "typeform_list_forms"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:read"]
        assert defn.api_docs_url == "https://www.typeform.com/developers/create/reference/retrieve-forms/"


# ---------------------------------------------------------------------------
# get_form
# ---------------------------------------------------------------------------


class TestGetForm:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("get_form.json")
        httpx_mock.add_response(json=data, url="https://api.typeform.com/forms/abc123")

        result = await typeform_get_form(GetFormParams(form_id="abc123"), token=_TOKEN)

        assert isinstance(result, GetFormResult)
        assert result.success is True
        assert result.id == "id"
        assert result.title == "title"
        assert result.language == "en"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_form.json"))

        await typeform_get_form(GetFormParams(form_id="abc123"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_form_id_in_url(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_form.json"))

        await typeform_get_form(GetFormParams(form_id="my_form_99"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert "/forms/my_form_99" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await typeform_get_form(GetFormParams(form_id="missing"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_get_form._tool_definition
        assert defn.name == "typeform_get_form"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:read"]
        assert defn.api_docs_url == "https://www.typeform.com/developers/create/reference/retrieve-form/"


# ---------------------------------------------------------------------------
# get_responses
# ---------------------------------------------------------------------------


class TestGetResponses:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("get_responses.json")
        httpx_mock.add_response(
            json=data,
            url="https://api.typeform.com/forms/abc123/responses?page_size=25",
        )

        result = await typeform_get_responses(GetResponsesParams(form_id="abc123"), token=_TOKEN)

        assert isinstance(result, GetResponsesResult)
        assert result.success is True
        assert result.total_items == 4
        assert len(result.items) == 4
        assert result.items[0].response_id == "21085286190ffad1248d17c4135ee56f"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_responses.json"))

        await typeform_get_responses(GetResponsesParams(form_id="abc123"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await typeform_get_responses(GetResponsesParams(form_id="abc123"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_get_responses._tool_definition
        assert defn.name == "typeform_get_responses"
        assert defn.provider == "typeform"
        assert defn.scopes == ["responses:read"]
        assert defn.api_docs_url == "https://www.typeform.com/developers/responses/reference/retrieve-responses/"
