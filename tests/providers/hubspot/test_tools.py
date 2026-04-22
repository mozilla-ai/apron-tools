"""Tests for HubSpot tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.hubspot.tools import (
    hubspot_create_contact,
    hubspot_search_contacts,
    hubspot_update_contact,
)
from apron_tools.providers.hubspot.types import (
    CreateContactParams,
    CreateResult,
    SearchContactsParams,
    SearchResult,
    UpdateContactParams,
    UpdateResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "hs_test_token_abc123"
_BASE_URL = "https://api.hubapi.com"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# hubspot_search_contacts
# ---------------------------------------------------------------------------


class TestSearchContacts:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/search",
            method="POST",
            json=_load_json("search_contacts.json"),
        )

        result = await hubspot_search_contacts(
            SearchContactsParams(query="ada@example.com"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "151"
        assert result.results[0].properties["firstname"] == "Ada"

    async def test_sends_payload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/search",
            method="POST",
            json=_load_json("search_contacts.json"),
        )

        await hubspot_search_contacts(
            SearchContactsParams(
                query="ada",
                limit=25,
                properties=["email", "firstname"],
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_requests()[-1]
        body = json.loads(request.content)
        assert body == {
            "query": "ada",
            "limit": 25,
            "properties": ["email", "firstname"],
        }
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_limit_clamped_to_api_max(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/search",
            method="POST",
            json=_load_json("search_contacts.json"),
        )

        await hubspot_search_contacts(
            SearchContactsParams(query="ada", limit=500),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body["limit"] == 100

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/search",
            method="POST",
            status_code=401,
            text="Unauthorized",
        )

        result = await hubspot_search_contacts(
            SearchContactsParams(query="ada"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_contacts._tool_definition
        assert defn.name == "hubspot_search_contacts"
        assert defn.provider == "hubspot"
        assert defn.service == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]
        assert "search" in defn.api_docs_url


# ---------------------------------------------------------------------------
# hubspot_create_contact
# ---------------------------------------------------------------------------


class TestCreateContact:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts",
            method="POST",
            status_code=201,
            json=_load_json("create_contact.json"),
        )

        result = await hubspot_create_contact(
            CreateContactParams(
                properties={
                    "email": "ada@example.com",
                    "firstname": "Ada",
                    "lastname": "Lovelace",
                },
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "151"
        assert result.properties["email"] == "ada@example.com"

    async def test_sends_properties_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts",
            method="POST",
            status_code=201,
            json=_load_json("create_contact.json"),
        )

        await hubspot_create_contact(
            CreateContactParams(properties={"email": "ada@example.com"}),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"properties": {"email": "ada@example.com"}}

    async def test_includes_associations(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts",
            method="POST",
            status_code=201,
            json=_load_json("create_contact.json"),
        )

        await hubspot_create_contact(
            CreateContactParams(
                properties={"email": "ada@example.com"},
                associations=[
                    {
                        "to": {"id": "501"},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 279,
                            }
                        ],
                    }
                ],
            ),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body["associations"] == [
            {
                "to": {"id": "501"},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 279,
                    }
                ],
            }
        ]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts",
            method="POST",
            status_code=400,
            text="Missing required property",
        )

        result = await hubspot_create_contact(
            CreateContactParams(properties={}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_create_contact._tool_definition
        assert defn.name == "hubspot_create_contact"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_update_contact
# ---------------------------------------------------------------------------


class TestUpdateContact:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/151",
            method="PATCH",
            json=_load_json("update_contact.json"),
        )

        result = await hubspot_update_contact(
            UpdateContactParams(
                record_id="151",
                properties={"jobtitle": "Senior Engineer"},
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateResult)
        assert result.success is True
        assert result.id == "151"

    async def test_sends_patch_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/151",
            method="PATCH",
            json=_load_json("update_contact.json"),
        )

        await hubspot_update_contact(
            UpdateContactParams(
                record_id="151",
                properties={"jobtitle": "Senior Engineer"},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_requests()[-1]
        assert request.method == "PATCH"
        assert json.loads(request.content) == {
            "properties": {"jobtitle": "Senior Engineer"},
        }

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/contacts/missing",
            method="PATCH",
            status_code=404,
            text="Not Found",
        )

        result = await hubspot_update_contact(
            UpdateContactParams(record_id="missing", properties={"jobtitle": "x"}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_update_contact._tool_definition
        assert defn.name == "hubspot_update_contact"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]
