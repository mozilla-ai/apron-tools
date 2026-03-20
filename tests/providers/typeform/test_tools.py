"""Tests for Typeform tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.typeform.tools import (
    typeform_create_form,
    typeform_explore_workspace,
    typeform_get_form_details,
    typeform_get_form_responses,
    typeform_update_form,
)
from apron_tools.providers.typeform.types import (
    CreateFormParams,
    CreateFormResult,
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetFormDetailsParams,
    GetFormDetailsResult,
    GetFormResponsesParams,
    GetFormResponsesResult,
    UpdateFormParams,
    UpdateFormResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "tfp_test_token_abc123"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# explore_workspace
# ---------------------------------------------------------------------------


class TestExploreWorkspace:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("explore_workspace.json")
        httpx_mock.add_response(json=data, url="https://api.typeform.com/forms?page=1&page_size=10")

        result = await typeform_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN)

        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True
        assert result.total_items == 2
        assert len(result.items) == 2
        assert result.items[0].id == "abc123"
        assert result.items[0].title == "Customer Feedback"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("explore_workspace.json"))

        await typeform_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await typeform_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_explore_workspace._tool_definition
        assert defn.name == "typeform_explore_workspace"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:read"]


# ---------------------------------------------------------------------------
# get_form_details
# ---------------------------------------------------------------------------


class TestGetFormDetails:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("get_form_details.json")
        httpx_mock.add_response(json=data, url="https://api.typeform.com/forms/abc123")

        result = await typeform_get_form_details(GetFormDetailsParams(form_id="abc123"), token=_TOKEN)

        assert isinstance(result, GetFormDetailsResult)
        assert result.success is True
        assert result.id == "id"
        assert result.title == "title"
        assert result.language == "en"

    async def test_form_id_in_url(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_form_details.json"))

        await typeform_get_form_details(GetFormDetailsParams(form_id="my_form_99"), token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        assert "/forms/my_form_99" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await typeform_get_form_details(GetFormDetailsParams(form_id="missing"), token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_get_form_details._tool_definition
        assert defn.name == "typeform_get_form_details"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:read"]


# ---------------------------------------------------------------------------
# create_form
# ---------------------------------------------------------------------------


class TestCreateForm:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_form.json"))

        params = CreateFormParams(
            title="Customer Survey",
            fields=[{"ref": "q1", "title": "Your name?", "type": "short_text"}],
        )
        result = await typeform_create_form(params, token=_TOKEN)

        assert isinstance(result, CreateFormResult)
        assert result.success is True
        assert result.id == "new-form-001"
        assert result.title == "Customer Survey"
        assert result.url == "https://example.typeform.com/to/new-form-001"
        assert "Customer Survey" in str(result)

    async def test_sends_correct_payload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_form.json"))

        params = CreateFormParams(
            title="Test Form",
            fields=[{"type": "short_text", "title": "Name?"}],
            workspace_id="ws-001",
            language="es",
        )
        await typeform_create_form(params, token=_TOKEN)

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["title"] == "Test Form"
        assert body["settings"]["language"] == "es"
        assert "ws-001" in body["workspace"]["href"]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        params = CreateFormParams(title="Bad", fields=[])
        result = await typeform_create_form(params, token=_TOKEN)

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_create_form._tool_definition
        assert defn.name == "typeform_create_form"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:write"]


# ---------------------------------------------------------------------------
# update_form
# ---------------------------------------------------------------------------


class TestUpdateForm:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        # GET existing form.
        httpx_mock.add_response(json=_load_json("get_form_details.json"))
        # PUT updated form.
        httpx_mock.add_response(json=_load_json("update_form.json"))

        params = UpdateFormParams(form_id="existing-form-001", title="Updated Survey")
        result = await typeform_update_form(params, token=_TOKEN)

        assert isinstance(result, UpdateFormResult)
        assert result.success is True
        assert result.id == "existing-form-001"
        assert result.title == "Updated Survey"

        # Verify PUT was sent with merged payload.
        requests = httpx_mock.get_requests()
        put_req = [r for r in requests if r.method == "PUT"]
        assert len(put_req) == 1
        body = json.loads(put_req[0].content)
        assert body["title"] == "Updated Survey"

    async def test_get_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        params = UpdateFormParams(form_id="missing", title="X")
        result = await typeform_update_form(params, token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_put_failure(self, httpx_mock: HTTPXMock) -> None:
        # GET succeeds.
        httpx_mock.add_response(json=_load_json("get_form_details.json"))
        # PUT fails.
        httpx_mock.add_response(status_code=403, text="Forbidden")

        params = UpdateFormParams(form_id="form-001", title="Nope")
        result = await typeform_update_form(params, token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_update_form._tool_definition
        assert defn.name == "typeform_update_form"
        assert defn.provider == "typeform"
        assert defn.scopes == ["forms:write"]


# ---------------------------------------------------------------------------
# get_form_responses
# ---------------------------------------------------------------------------


class TestGetFormResponses:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        data = _load_json("get_form_responses.json")
        httpx_mock.add_response(
            json=data,
            url="https://api.typeform.com/forms/abc123/responses?page_size=25",
        )

        result = await typeform_get_form_responses(GetFormResponsesParams(form_id="abc123"), token=_TOKEN)

        assert isinstance(result, GetFormResponsesResult)
        assert result.success is True
        assert result.total_items == 4
        assert len(result.items) == 4
        assert result.items[0].response_id == "21085286190ffad1248d17c4135ee56f"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await typeform_get_form_responses(GetFormResponsesParams(form_id="abc123"), token=_TOKEN)

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = typeform_get_form_responses._tool_definition
        assert defn.name == "typeform_get_form_responses"
        assert defn.provider == "typeform"
        assert defn.scopes == ["responses:read"]
