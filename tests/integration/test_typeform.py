"""Integration tests for Typeform tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    TYPEFORM_TOKEN=xxx \
    uv run pytest -m integration -k typeform -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.typeform import typeform_explore_workspace, typeform_get_form_details
from apron_tools.providers.typeform.types import (
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetFormDetailsParams,
    GetFormDetailsResult,
)

pytestmark = pytest.mark.integration


@pytest.fixture()
def typeform_token() -> str:
    """Retrieve Typeform token from environment or skip."""
    token = os.environ.get("TYPEFORM_TOKEN", "")
    if not token:
        pytest.skip("TYPEFORM_TOKEN required")
    return token


class TestTypeformExploreWorkspace:
    async def test_returns_valid_result(self, typeform_token: str) -> None:
        result = await typeform_explore_workspace(ExploreWorkspaceParams(page_size=5), token=typeform_token)
        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True

    async def test_str_output(self, typeform_token: str) -> None:
        result = await typeform_explore_workspace(ExploreWorkspaceParams(page_size=5), token=typeform_token)
        assert str(result)


class TestTypeformGetFormDetails:
    async def test_invalid_form_returns_error(self, typeform_token: str) -> None:
        result = await typeform_get_form_details(
            GetFormDetailsParams(form_id="nonexistent_form_id"),
            token=typeform_token,
        )
        assert isinstance(result, GetFormDetailsResult)
        assert result.success is False
