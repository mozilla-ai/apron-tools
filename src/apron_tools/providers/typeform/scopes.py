"""OAuth scope definitions for Typeform tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class TypeformScope(StrEnum):
    """OAuth scopes for Typeform API access."""

    FORMS_READ = "forms:read"
    FORMS_WRITE = "forms:write"
    RESPONSES_READ = "responses:read"


SCOPES: dict[str, list[TypeformScope]] = {
    "typeform_explore_workspace": [TypeformScope.FORMS_READ],
    "typeform_get_form_details": [TypeformScope.FORMS_READ],
    "typeform_create_form": [TypeformScope.FORMS_WRITE],
    "typeform_update_form": [TypeformScope.FORMS_WRITE],
    "typeform_get_form_responses": [TypeformScope.RESPONSES_READ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="typeform",
    display_name="Typeform",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
