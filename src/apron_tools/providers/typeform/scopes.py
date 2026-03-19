"""OAuth scope definitions for Typeform tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class TypeformScope(StrEnum):
    """OAuth scopes for Typeform API access."""

    FORMS_READ = "forms:read"
    RESPONSES_READ = "responses:read"


SCOPES: dict[str, list[TypeformScope]] = {
    "typeform_list_forms": [TypeformScope.FORMS_READ],
    "typeform_get_form": [TypeformScope.FORMS_READ],
    "typeform_get_responses": [TypeformScope.RESPONSES_READ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="typeform",
    display_name="Typeform",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
