"""Integration tests for Typeform tools against the real API.

Skipped by default. To run::

    ANY_TOOL_INTEGRATION_TESTS=1 TYPEFORM_TOKEN=xxx uv run pytest -m integration -v
"""

from __future__ import annotations

import os

import pytest

from any_tool.providers.typeform.tools import typeform_get_form, typeform_get_responses, typeform_list_forms
from any_tool.providers.typeform.types import (
    GetFormParams,
    GetFormResult,
    GetResponsesParams,
    GetResponsesResult,
    ListFormsParams,
    ListFormsResult,
)

pytestmark = pytest.mark.integration


@pytest.fixture()
def typeform_token() -> str:
    """Retrieve the Typeform API token from the environment."""
    token = os.environ.get("TYPEFORM_TOKEN", "")
    if not token:
        pytest.skip("TYPEFORM_TOKEN not set")
    return token


class TestListFormsIntegration:
    async def test_returns_valid_result(self, typeform_token: str):
        result = await typeform_list_forms(ListFormsParams(page_size=5), token=typeform_token)
        assert isinstance(result, ListFormsResult)
        assert result.success is True
        assert result.total_items >= 0

    async def test_str_output(self, typeform_token: str):
        result = await typeform_list_forms(ListFormsParams(page_size=5), token=typeform_token)
        text = str(result)
        assert "form" in text.lower()


class TestGetFormIntegration:
    async def test_returns_valid_result(self, typeform_token: str):
        forms = await typeform_list_forms(ListFormsParams(page_size=1), token=typeform_token)
        if not forms.items:
            pytest.skip("No forms available in account")
        form_id = forms.items[0].id

        result = await typeform_get_form(GetFormParams(form_id=form_id), token=typeform_token)
        assert isinstance(result, GetFormResult)
        assert result.success is True
        assert result.id == form_id


class TestGetResponsesIntegration:
    async def test_returns_valid_result(self, typeform_token: str):
        forms = await typeform_list_forms(ListFormsParams(page_size=1), token=typeform_token)
        if not forms.items:
            pytest.skip("No forms available in account")
        form_id = forms.items[0].id

        result = await typeform_get_responses(
            GetResponsesParams(form_id=form_id, page_size=5),
            token=typeform_token,
        )
        assert isinstance(result, GetResponsesResult)
        assert result.success is True
        assert result.total_items >= 0
