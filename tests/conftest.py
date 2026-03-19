"""Shared test fixtures for apron-tools."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless explicitly opted in.

    Integration tests are marked with @pytest.mark.integration and require
    provider credentials via environment variables. They are skipped by
    default in CI and local runs.

    To run integration tests::

        TYPEFORM_TOKEN=xxx uv run pytest -m integration
    """
    skip_integration = pytest.mark.skip(reason="integration tests require credentials (set provider token env vars)")
    for item in items:
        if "integration" in item.keywords and not os.environ.get("ANY_TOOL_INTEGRATION_TESTS"):
            item.add_marker(skip_integration)
