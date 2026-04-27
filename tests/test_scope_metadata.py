"""Tests for the Scope base class and CapabilityGroup metadata helper.

Verifies that ``Scope`` enum members carry consent-UI metadata while
remaining drop-in ``str`` substitutes — passing them to libraries that
expect raw scope strings (``urlencode``, ``" ".join(...)``, httpx form
bodies, JSON serialisation) must produce the bare scope value with no
``ScopeName.`` prefix leaking into the wire format.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from urllib.parse import urlencode

import httpx
import pytest

import apron_tools.providers as _providers_pkg
from apron_tools.types import AccessType, CapabilityGroup, Scope, ScopeMetadata


class FakeScope(Scope):
    """Local enum used to exercise the ``Scope`` base class in isolation."""

    READ = ("scope:read", "Read", "Read access", "read", False)
    WRITE = ("scope:write", "Write", "Write access", "write", False)
    REQUIRED = ("scope:id", "Identity", "Required for identity", "read", True)


class TestScopeBaseClass:
    def test_member_is_str_subclass(self):
        assert isinstance(FakeScope.READ, str)
        assert isinstance(FakeScope.READ, Scope)

    def test_str_value_is_raw_scope(self):
        assert str(FakeScope.READ) == "scope:read"
        assert FakeScope.READ.value == "scope:read"

    def test_metadata_attributes(self):
        assert FakeScope.READ.label == "Read"
        assert FakeScope.READ.description == "Read access"
        assert FakeScope.READ.access_type == "read"
        assert FakeScope.READ.required is False

    def test_required_flag(self):
        assert FakeScope.REQUIRED.required is True

    def test_equality_with_raw_string(self):
        assert FakeScope.READ == "scope:read"
        assert "scope:read" == FakeScope.READ.value  # noqa: SIM300

    def test_join_produces_raw_strings(self):
        joined = " ".join([FakeScope.READ, FakeScope.WRITE])
        assert joined == "scope:read scope:write"

    def test_urlencode_uses_raw_value(self):
        encoded = urlencode({"scope": FakeScope.READ})
        assert encoded == "scope=scope%3Aread"

    def test_urlencode_join_matches_oauth_authorize_pattern(self):
        encoded = urlencode({"scope": " ".join([FakeScope.READ, FakeScope.WRITE])})
        assert encoded == "scope=scope%3Aread+scope%3Awrite"

    def test_httpx_form_body_uses_raw_string(self):
        request = httpx.Request("POST", "https://example.test/oauth/token", data={"scope": FakeScope.READ})
        assert request.content == b"scope=scope%3Aread"

    def test_httpx_form_body_with_joined_scopes(self):
        request = httpx.Request(
            "POST",
            "https://example.test/oauth/token",
            data={"scope": " ".join([FakeScope.READ, FakeScope.WRITE])},
        )
        assert request.content == b"scope=scope%3Aread+scope%3Awrite"

    def test_json_serialisation_strips_enum_class_prefix(self):
        payload = json.dumps({"scopes": [FakeScope.READ, FakeScope.WRITE]})
        assert json.loads(payload) == {"scopes": ["scope:read", "scope:write"]}

    def test_iteration_yields_metadata_bearing_members(self):
        members = list(FakeScope)
        assert {m.value for m in members} == {"scope:read", "scope:write", "scope:id"}
        for member in members:
            assert hasattr(member, "label")
            assert hasattr(member, "access_type")

    def test_access_type_is_one_of_literals(self):
        valid: set[AccessType] = {"read", "write", "admin"}
        for member in FakeScope:
            assert member.access_type in valid


class TestScopeMetadata:
    def test_from_scope_roundtrip(self):
        meta = ScopeMetadata.from_scope(FakeScope.READ)
        assert meta == ScopeMetadata(
            scope="scope:read",
            label="Read",
            description="Read access",
            access_type="read",
            required=False,
        )

    def test_required_propagates(self):
        meta = ScopeMetadata.from_scope(FakeScope.REQUIRED)
        assert meta.required is True


class TestCapabilityGroupMetadata:
    def test_metadata_method_returns_one_entry_per_scope(self):
        group = CapabilityGroup(
            provider="fake",
            display_name="Fake",
            scopes=sorted({FakeScope.READ, FakeScope.WRITE, FakeScope.REQUIRED}),
        )
        meta = group.metadata()
        assert len(meta) == 3
        by_scope = {m.scope: m for m in meta}
        assert by_scope["scope:read"].access_type == "read"
        assert by_scope["scope:write"].access_type == "write"
        assert by_scope["scope:id"].required is True

    def test_metadata_falls_back_for_raw_strings(self):
        group = CapabilityGroup(
            provider="raw",
            display_name="Raw",
            scopes=["foo:read", "bar:write"],
        )
        meta = group.metadata()
        assert len(meta) == 2
        assert meta[0] == ScopeMetadata(
            scope="foo:read",
            label="foo:read",
            description="foo:read",
            access_type="read",
            required=False,
        )

    def test_metadata_handles_mixed_scope_types(self):
        group = CapabilityGroup(
            provider="mixed",
            display_name="Mixed",
            scopes=[FakeScope.READ, "raw:scope"],
        )
        meta = group.metadata()
        assert meta[0].label == "Read"
        assert meta[1].label == "raw:scope"


def _collect_scopes_modules() -> list[str]:
    modules: list[str] = []
    for _imp, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
        if not is_pkg:
            continue
        pkg_path = f"apron_tools.providers.{name}"
        pkg = importlib.import_module(pkg_path)
        for _imp2, sub_name, sub_is_pkg in pkgutil.iter_modules(pkg.__path__):
            if sub_name == "scopes" and not sub_is_pkg:
                modules.append(f"{pkg_path}.scopes")
            elif sub_is_pkg:
                sub_pkg_path = f"{pkg_path}.{sub_name}"
                sub_pkg = importlib.import_module(sub_pkg_path)
                for _imp3, leaf_name, leaf_is_pkg in pkgutil.iter_modules(sub_pkg.__path__):
                    if leaf_name == "scopes" and not leaf_is_pkg:
                        modules.append(f"{sub_pkg_path}.scopes")
    return modules


def _all_scope_enums() -> list[type[Scope]]:
    enums: list[type[Scope]] = []
    for module_path in _collect_scopes_modules():
        module = importlib.import_module(module_path)
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, Scope) and obj is not Scope:
                enums.append(obj)
    return enums


class TestProviderScopeMetadataCoverage:
    """Acceptance check: every member of every provider scope enum has metadata."""

    @pytest.mark.parametrize("scope_enum", _all_scope_enums(), ids=lambda e: e.__name__)
    def test_every_member_has_metadata(self, scope_enum: type[Scope]):
        assert len(scope_enum) > 0, f"{scope_enum.__name__} has no members"
        for member in scope_enum:
            assert isinstance(member.label, str) and member.label, f"{member!r} missing label"
            assert isinstance(member.description, str) and member.description, f"{member!r} missing description"
            assert member.access_type in {"read", "write", "admin"}, (
                f"{member!r} has invalid access_type {member.access_type!r}"
            )
            assert isinstance(member.required, bool), f"{member!r} required is not bool"

    @pytest.mark.parametrize("scope_enum", _all_scope_enums(), ids=lambda e: e.__name__)
    def test_every_member_is_str(self, scope_enum: type[Scope]):
        for member in scope_enum:
            assert isinstance(member, str)
            assert str(member) == member.value
