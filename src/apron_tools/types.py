"""Core types for apron-tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import Base64Bytes, BaseModel, Field, HttpUrl

AccessType = Literal["read", "write", "admin"]
"""Access level granted by a scope.

Used by consent UIs to visually group scopes (e.g. read tools under
one heading, write tools under another) and by static audits to
enforce least-privilege: a read-only tool must not declare a scope
whose ``access_type`` is ``"write"`` or ``"admin"``.

For scopes that implicitly cover both reading and writing
(e.g. Google's ``gmail.modify``), use ``"write"`` and call out the
read implication in the description so the consent screen wording
matches what the user will actually see at the provider.
"""


class Scope(StrEnum):
    """Base class for OAuth/capability scope enums with consent-UI metadata.

    Members carry their value (the raw scope string) plus four metadata
    attributes used by consent pickers: ``label``, ``description``,
    ``access_type``, and ``required``. Members remain ``str``-equivalent —
    libraries that consume scope strings (``urlencode``, ``" ".join(...)``,
    ``httpx`` form bodies, Authlib) accept them directly with no
    ``ScopeName.`` prefix leaking into the wire format.

    Subclass and define members as tuples:

    .. code-block:: python

        class GmailScope(Scope):
            READONLY = (
                "https://www.googleapis.com/auth/gmail.readonly",
                "Read Emails",
                "View and search your Gmail messages",
                "read",
                False,
            )
    """

    label: str
    description: str
    access_type: AccessType
    required: bool

    def __new__(
        cls,
        value: str,
        label: str,
        description: str,
        access_type: AccessType,
        required: bool = False,  # noqa: FBT001, FBT002
    ) -> Self:
        """Create a scope member carrying consent-UI metadata."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        member.description = description
        member.access_type = access_type
        member.required = required
        return member


@dataclass(frozen=True)
class ScopeMetadata:
    """Plain-dataclass view of a :class:`Scope` member.

    Useful for serialising scope metadata (e.g. to JSON for a consent UI)
    or passing it across boundaries where the original enum class is not
    importable.
    """

    scope: str
    label: str
    description: str
    access_type: AccessType
    required: bool

    @classmethod
    def from_scope(cls, scope: Scope) -> ScopeMetadata:
        """Build a ``ScopeMetadata`` from a :class:`Scope` enum member."""
        return cls(
            scope=str(scope),
            label=scope.label,
            description=scope.description,
            access_type=scope.access_type,
            required=scope.required,
        )


class ToolResult(BaseModel):
    """Base for all tool outputs.

    Subclasses define provider-specific fields and implement ``__str__``
    for LLM-readable output. Consumers choose their access level:

    - ``str(result)`` for text (what the LLM reads).
    - ``result.field`` for typed attribute access.
    - ``result.model_dump()`` for dict.
    - ``result.model_dump_json()`` for JSON.
    """

    success: bool
    error: str | None = None

    def __str__(self) -> str:
        """Return a human/LLM-readable string representation."""
        raise NotImplementedError("Subclasses must implement __str__.")


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata for a single tool, used by any-identity's registry."""

    name: str
    """Tool name, e.g. ``typeform_explore_workspace``."""

    provider: str
    """OAuth provider / company, e.g. ``google``, ``atlassian``, ``slack``."""

    service: str
    """Specific product, e.g. ``google_sheets``, ``atlassian_jira``, ``slack``."""

    integration: str
    """Same as service. Kept for Octonous compatibility."""

    description: str
    """Human-readable description of what the tool does."""

    input_schema: dict[str, Any]
    """JSON Schema for the tool's input parameters."""

    output_schema: dict[str, Any]
    """JSON Schema for the tool's output."""

    scopes: list[str]
    """OAuth scopes required to call this tool."""

    api_docs_url: str
    """URL to the provider's API documentation for this endpoint."""


@dataclass(frozen=True)
class CapabilityGroup:
    """Provider-level metadata for the tool registry.

    Represents an integration that can be connected via OAuth,
    with the aggregate scopes required across all its tools.

    ``scopes`` typically holds :class:`Scope` enum members so the
    per-scope metadata travels with the group. ``str`` is accepted for
    callers that build a group manually from raw scope strings; those
    entries simply have no metadata available via :meth:`metadata`.
    """

    provider: str
    """Provider identifier, e.g. ``typeform``."""

    display_name: str
    """Human-readable name, e.g. ``Typeform``."""

    scopes: list[Scope | str]
    """Union of all OAuth scopes required by this provider's tools.

    Members are :class:`Scope` instances when sourced from a provider
    scope enum, or raw ``str`` for ad-hoc groups. Lists may freely mix
    the two: :meth:`metadata` falls back to defaults for raw strings.
    """

    def metadata(self) -> list[ScopeMetadata]:
        """Return per-scope consent-UI metadata for this group.

        Scope members that are :class:`Scope` enum instances yield full
        metadata. Raw string entries fall back to defaults: the scope
        string is used as both the label and the description, with
        ``access_type="read"`` and ``required=False``. Callers building
        a least-privilege consent picker should prefer scope enums so
        the read/write split and required-scope semantics are accurate.
        """
        result: list[ScopeMetadata] = []
        for s in self.scopes:
            if isinstance(s, Scope):
                result.append(ScopeMetadata.from_scope(s))
            else:
                result.append(
                    ScopeMetadata(
                        scope=str(s),
                        label=str(s),
                        description=str(s),
                        access_type="read",
                        required=False,
                    )
                )
        return result


# ---------------------------------------------------------------------------
# File input types for upload tools
# ---------------------------------------------------------------------------


class FileFromBytes(BaseModel):
    """File provided as raw bytes.

    For programmatic callers that already have file data in memory.
    Data is base64-encoded when serialised to JSON, ensuring binary
    content round-trips safely across language boundaries.
    """

    type: Literal["bytes"] = "bytes"
    data: Base64Bytes
    """File content. Accepts base64 strings (JSON callers) or raw bytes (Python callers)."""

    filename: str
    """Filename for the uploaded file."""

    mime_type: str
    """MIME type of the file content."""


class FileFromUrl(BaseModel):
    """File to be fetched from a URL.

    The tool function downloads the file before uploading to the provider.
    Filename and MIME type are inferred from the HTTP response when not provided.

    .. warning:: Security consideration

        URLs are fetched as-is with no network filtering. The library does
        not block private, loopback, or link-local addresses, and does not
        enforce a maximum download size. This is by design — the library
        has no knowledge of the caller's network topology or resource
        constraints.

        If you expose tool functions to untrusted input (e.g. an LLM
        generating URLs), apply your own URL validation and size limits
        before passing the URL to a tool. Hosted services consuming this
        library should enforce their own SSRF and resource-exhaustion
        policies at the service boundary.
    """

    type: Literal["url"] = "url"
    url: HttpUrl
    """HTTP(S) URL to fetch the file from."""

    filename: str | None = None
    """Override filename. Inferred from the URL or Content-Disposition header if not provided."""

    mime_type: str | None = None
    """Override MIME type. Inferred from the Content-Type header if not provided."""


FileInput = Annotated[
    FileFromBytes | FileFromUrl,
    Field(discriminator="type"),
]
"""File input for upload tools.

A discriminated union: provide either a URL to fetch from or raw bytes.
LLM callers typically use ``FileFromUrl``; programmatic callers may use either.
"""
