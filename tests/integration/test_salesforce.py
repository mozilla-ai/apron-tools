"""Integration tests for Salesforce tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    SALESFORCE_TOKEN=... \
    uv run pytest -m integration -k salesforce -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.salesforce import salesforce_explore_org
from apron_tools.providers.salesforce.types import ExploreOrgParams, ExploreOrgResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def salesforce_token() -> str:
    """Retrieve Salesforce OAuth token from environment or skip."""
    token = os.environ.get("SALESFORCE_TOKEN", "")
    if not token:
        pytest.skip("SALESFORCE_TOKEN required")
    return token


class TestSalesforceExploreOrg:
    async def test_returns_valid_result(self, salesforce_token: str) -> None:
        result = await salesforce_explore_org(ExploreOrgParams(), token=salesforce_token)
        assert isinstance(result, ExploreOrgResult)
        assert result.success is True

    async def test_str_output(self, salesforce_token: str) -> None:
        result = await salesforce_explore_org(ExploreOrgParams(), token=salesforce_token)
        assert str(result)
