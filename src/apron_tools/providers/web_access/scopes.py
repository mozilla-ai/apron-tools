"""Capability-based scope definitions for web_access tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class WebAccessScope(Scope):
    """Capability scopes for the web_access provider.

    web_access is backed by the Tabstack service API (service token auth),
    not OAuth. Scopes model the capabilities granted to the caller so they
    can be surfaced alongside OAuth-based providers in the registry.
    """

    RESEARCH = (
        "research",
        "Research the Web",
        "Run multi-step web research queries that browse and synthesise public web content",
        "read",
        False,
    )
    EXTRACT = (
        "extract",
        "Extract Structured Data",
        "Fetch a URL and extract structured JSON matching a caller-provided schema",
        "read",
        False,
    )


SCOPES: dict[str, list[WebAccessScope]] = {
    "web_access_research": [WebAccessScope.RESEARCH],
    "web_access_extract_json": [WebAccessScope.EXTRACT],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="web_access",
    display_name="Web Access",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
