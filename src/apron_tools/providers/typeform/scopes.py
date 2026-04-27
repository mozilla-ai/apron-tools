"""OAuth scope definitions for Typeform tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class TypeformScope(Scope):
    """OAuth scopes for Typeform API access."""

    FORMS_READ = (
        "forms:read",
        "View Forms",
        "View your Typeform forms and questions",
        "read",
        False,
    )
    FORMS_WRITE = (
        "forms:write",
        "Edit Forms",
        "Create and modify your Typeform forms",
        "write",
        False,
    )
    RESPONSES_READ = (
        "responses:read",
        "View Responses",
        "View form submissions and responses",
        "read",
        False,
    )


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
