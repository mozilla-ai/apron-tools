"""Tests for HubSpot tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_httpx import HTTPXMock

from apron_tools.providers.hubspot.tools import (
    hubspot_create_company,
    hubspot_create_contact,
    hubspot_create_deal,
    hubspot_create_note,
    hubspot_create_task,
    hubspot_list_owners,
    hubspot_list_pipelines,
    hubspot_log_activity,
    hubspot_search_calls,
    hubspot_search_companies,
    hubspot_search_contacts,
    hubspot_search_deals,
    hubspot_search_emails,
    hubspot_search_meetings,
    hubspot_search_notes,
    hubspot_search_tasks,
    hubspot_update_company,
    hubspot_update_contact,
    hubspot_update_deal,
    hubspot_update_note,
    hubspot_update_task,
)
from apron_tools.providers.hubspot.types import (
    CreateCompanyParams,
    CreateContactParams,
    CreateDealParams,
    CreateNoteParams,
    CreateResult,
    CreateTaskParams,
    ListOwnersParams,
    ListOwnersResult,
    ListPipelinesParams,
    ListPipelinesResult,
    LogActivityParams,
    SearchCallsParams,
    SearchCompaniesParams,
    SearchContactsParams,
    SearchDealsParams,
    SearchEmailsParams,
    SearchMeetingsParams,
    SearchNotesParams,
    SearchResult,
    SearchTasksParams,
    UpdateCompanyParams,
    UpdateContactParams,
    UpdateDealParams,
    UpdateNoteParams,
    UpdateResult,
    UpdateTaskParams,
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


# ---------------------------------------------------------------------------
# hubspot_search_companies
# ---------------------------------------------------------------------------


class TestSearchCompanies:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/search",
            method="POST",
            json=_load_json("search_companies.json"),
        )

        result = await hubspot_search_companies(
            SearchCompaniesParams(query="acme"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "801"
        assert result.results[0].properties["name"] == "Acme Corp"

    async def test_sends_payload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/search",
            method="POST",
            json=_load_json("search_companies.json"),
        )

        await hubspot_search_companies(
            SearchCompaniesParams(
                query="acme",
                limit=50,
                properties=["name", "industry"],
            ),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {
            "query": "acme",
            "limit": 50,
            "properties": ["name", "industry"],
        }

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/search",
            method="POST",
            status_code=403,
            text="Forbidden",
        )

        result = await hubspot_search_companies(
            SearchCompaniesParams(query="acme"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_companies._tool_definition
        assert defn.name == "hubspot_search_companies"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.companies.read"]


# ---------------------------------------------------------------------------
# hubspot_create_company
# ---------------------------------------------------------------------------


class TestCreateCompany:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies",
            method="POST",
            status_code=201,
            json=_load_json("create_company.json"),
        )

        result = await hubspot_create_company(
            CreateCompanyParams(
                properties={"name": "Acme Corp", "domain": "acme.com"},
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "801"
        assert result.properties["domain"] == "acme.com"

    async def test_sends_properties_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies",
            method="POST",
            status_code=201,
            json=_load_json("create_company.json"),
        )

        await hubspot_create_company(
            CreateCompanyParams(properties={"name": "Acme Corp"}),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"properties": {"name": "Acme Corp"}}

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies",
            method="POST",
            status_code=400,
            text="Bad Request",
        )

        result = await hubspot_create_company(
            CreateCompanyParams(properties={}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_create_company._tool_definition
        assert defn.name == "hubspot_create_company"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.companies.write"]


# ---------------------------------------------------------------------------
# hubspot_update_company
# ---------------------------------------------------------------------------


class TestUpdateCompany:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/801",
            method="PATCH",
            json=_load_json("update_company.json"),
        )

        result = await hubspot_update_company(
            UpdateCompanyParams(
                record_id="801",
                properties={"industry": "Software"},
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateResult)
        assert result.success is True
        assert result.id == "801"

    async def test_sends_patch_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/801",
            method="PATCH",
            json=_load_json("update_company.json"),
        )

        await hubspot_update_company(
            UpdateCompanyParams(
                record_id="801",
                properties={"industry": "Software"},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_requests()[-1]
        assert request.method == "PATCH"
        assert json.loads(request.content) == {
            "properties": {"industry": "Software"},
        }

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/companies/missing",
            method="PATCH",
            status_code=404,
            text="Not Found",
        )

        result = await hubspot_update_company(
            UpdateCompanyParams(record_id="missing", properties={"industry": "x"}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_update_company._tool_definition
        assert defn.name == "hubspot_update_company"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.companies.write"]


# ---------------------------------------------------------------------------
# hubspot_search_deals
# ---------------------------------------------------------------------------


class TestSearchDeals:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/search",
            method="POST",
            json=_load_json("search_deals.json"),
        )

        result = await hubspot_search_deals(
            SearchDealsParams(query="enterprise"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "1402"
        assert result.results[0].properties["dealname"] == "Q1 Enterprise Deal"

    async def test_sends_payload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/search",
            method="POST",
            json=_load_json("search_deals.json"),
        )

        await hubspot_search_deals(
            SearchDealsParams(query="enterprise", limit=5),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body["query"] == "enterprise"
        assert body["limit"] == 5

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/search",
            method="POST",
            status_code=500,
            text="Internal Server Error",
        )

        result = await hubspot_search_deals(
            SearchDealsParams(query="enterprise"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_deals._tool_definition
        assert defn.name == "hubspot_search_deals"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.deals.read"]


# ---------------------------------------------------------------------------
# hubspot_create_deal
# ---------------------------------------------------------------------------


class TestCreateDeal:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals",
            method="POST",
            status_code=201,
            json=_load_json("create_deal.json"),
        )

        result = await hubspot_create_deal(
            CreateDealParams(
                properties={
                    "dealname": "Q1 Enterprise Deal",
                    "dealstage": "appointmentscheduled",
                    "pipeline": "default",
                    "amount": "50000",
                },
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "1402"
        assert result.properties["dealname"] == "Q1 Enterprise Deal"

    async def test_sends_properties_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals",
            method="POST",
            status_code=201,
            json=_load_json("create_deal.json"),
        )

        await hubspot_create_deal(
            CreateDealParams(properties={"dealname": "Q1 Enterprise Deal"}),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"properties": {"dealname": "Q1 Enterprise Deal"}}

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals",
            method="POST",
            status_code=400,
            text="Missing required property: pipeline",
        )

        result = await hubspot_create_deal(
            CreateDealParams(properties={}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_create_deal._tool_definition
        assert defn.name == "hubspot_create_deal"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.deals.write"]


# ---------------------------------------------------------------------------
# hubspot_update_deal
# ---------------------------------------------------------------------------


class TestUpdateDeal:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/1402",
            method="PATCH",
            json=_load_json("update_deal.json"),
        )

        result = await hubspot_update_deal(
            UpdateDealParams(
                record_id="1402",
                properties={"dealstage": "closedwon", "amount": "75000"},
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateResult)
        assert result.success is True
        assert result.id == "1402"

    async def test_sends_patch_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/1402",
            method="PATCH",
            json=_load_json("update_deal.json"),
        )

        await hubspot_update_deal(
            UpdateDealParams(
                record_id="1402",
                properties={"dealstage": "closedwon"},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_requests()[-1]
        assert request.method == "PATCH"
        assert json.loads(request.content) == {
            "properties": {"dealstage": "closedwon"},
        }

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/deals/missing",
            method="PATCH",
            status_code=404,
            text="Not Found",
        )

        result = await hubspot_update_deal(
            UpdateDealParams(record_id="missing", properties={"amount": "1"}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_update_deal._tool_definition
        assert defn.name == "hubspot_update_deal"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.deals.write"]


# ---------------------------------------------------------------------------
# hubspot_search_notes
# ---------------------------------------------------------------------------


class TestSearchNotes:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes/search",
            method="POST",
            json=_load_json("search_notes.json"),
        )

        result = await hubspot_search_notes(
            SearchNotesParams(query="roadmap"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "2001"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes/search",
            method="POST",
            status_code=401,
            text="Unauthorized",
        )

        result = await hubspot_search_notes(
            SearchNotesParams(query="roadmap"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_notes._tool_definition
        assert defn.name == "hubspot_search_notes"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]


# ---------------------------------------------------------------------------
# hubspot_create_note
# ---------------------------------------------------------------------------


class TestCreateNote:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes",
            method="POST",
            status_code=201,
            json=_load_json("create_note.json"),
        )

        result = await hubspot_create_note(
            CreateNoteParams(
                properties={
                    "hs_note_body": "Discussed Q1 roadmap and budget",
                    "hs_timestamp": "2024-04-10T12:00:00.000Z",
                },
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "2001"

    async def test_sends_properties_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes",
            method="POST",
            status_code=201,
            json=_load_json("create_note.json"),
        )

        await hubspot_create_note(
            CreateNoteParams(properties={"hs_note_body": "Interview summary"}),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"properties": {"hs_note_body": "Interview summary"}}

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_create_note._tool_definition
        assert defn.name == "hubspot_create_note"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_update_note
# ---------------------------------------------------------------------------


class TestUpdateNote:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes/2001",
            method="PATCH",
            json=_load_json("update_note.json"),
        )

        result = await hubspot_update_note(
            UpdateNoteParams(
                record_id="2001",
                properties={"hs_note_body": "Updated note body"},
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.id == "2001"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/notes/missing",
            method="PATCH",
            status_code=404,
            text="Not Found",
        )

        result = await hubspot_update_note(
            UpdateNoteParams(record_id="missing", properties={"hs_note_body": "x"}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_update_note._tool_definition
        assert defn.name == "hubspot_update_note"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_search_tasks
# ---------------------------------------------------------------------------


class TestSearchTasks:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks/search",
            method="POST",
            json=_load_json("search_tasks.json"),
        )

        result = await hubspot_search_tasks(
            SearchTasksParams(query="proposal"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "3101"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks/search",
            method="POST",
            status_code=401,
            text="Unauthorized",
        )

        result = await hubspot_search_tasks(
            SearchTasksParams(query="proposal"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_tasks._tool_definition
        assert defn.name == "hubspot_search_tasks"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]


# ---------------------------------------------------------------------------
# hubspot_create_task
# ---------------------------------------------------------------------------


class TestCreateTask:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks",
            method="POST",
            status_code=201,
            json=_load_json("create_task.json"),
        )

        result = await hubspot_create_task(
            CreateTaskParams(
                properties={
                    "hs_task_subject": "Follow up on proposal",
                    "hs_task_priority": "HIGH",
                    "hs_task_status": "NOT_STARTED",
                },
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "3101"

    async def test_sends_properties_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks",
            method="POST",
            status_code=201,
            json=_load_json("create_task.json"),
        )

        await hubspot_create_task(
            CreateTaskParams(properties={"hs_task_subject": "Follow up"}),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"properties": {"hs_task_subject": "Follow up"}}

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_create_task._tool_definition
        assert defn.name == "hubspot_create_task"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_update_task
# ---------------------------------------------------------------------------


class TestUpdateTask:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks/3101",
            method="PATCH",
            json=_load_json("update_task.json"),
        )

        result = await hubspot_update_task(
            UpdateTaskParams(
                record_id="3101",
                properties={"hs_task_status": "COMPLETED"},
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.id == "3101"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/tasks/missing",
            method="PATCH",
            status_code=404,
            text="Not Found",
        )

        result = await hubspot_update_task(
            UpdateTaskParams(record_id="missing", properties={"hs_task_status": "x"}),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_update_task._tool_definition
        assert defn.name == "hubspot_update_task"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_search_calls
# ---------------------------------------------------------------------------


class TestSearchCalls:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/calls/search",
            method="POST",
            json=_load_json("search_calls.json"),
        )

        result = await hubspot_search_calls(
            SearchCallsParams(query="renewal"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "4201"

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_calls._tool_definition
        assert defn.name == "hubspot_search_calls"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]


# ---------------------------------------------------------------------------
# hubspot_search_emails
# ---------------------------------------------------------------------------


class TestSearchEmails:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/emails/search",
            method="POST",
            json=_load_json("search_emails.json"),
        )

        result = await hubspot_search_emails(
            SearchEmailsParams(query="proposal"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "4301"

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_emails._tool_definition
        assert defn.name == "hubspot_search_emails"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]


# ---------------------------------------------------------------------------
# hubspot_search_meetings
# ---------------------------------------------------------------------------


class TestSearchMeetings:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/meetings/search",
            method="POST",
            json=_load_json("search_meetings.json"),
        )

        result = await hubspot_search_meetings(
            SearchMeetingsParams(query="planning"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.results) == 1
        assert result.results[0].id == "4401"

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_search_meetings._tool_definition
        assert defn.name == "hubspot_search_meetings"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.read"]


# ---------------------------------------------------------------------------
# hubspot_log_activity
# ---------------------------------------------------------------------------


class TestLogActivity:
    async def test_logs_call(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/calls",
            method="POST",
            status_code=201,
            json=_load_json("log_activity_call.json"),
        )

        result = await hubspot_log_activity(
            LogActivityParams(
                activity_type="calls",
                properties={
                    "hs_call_title": "Q1 Review Call",
                    "hs_call_duration": "1800000",
                    "hs_call_status": "COMPLETED",
                },
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateResult)
        assert result.success is True
        assert result.id == "4201"

    async def test_normalizes_activity_type_casing(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/objects/emails",
            method="POST",
            status_code=201,
            json={"id": "e1", "properties": {}},
        )

        result = await hubspot_log_activity(
            LogActivityParams(
                activity_type=" Emails ",
                properties={"hs_email_subject": "hi"},
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.id == "e1"

    async def test_rejects_invalid_activity_type(self, httpx_mock: HTTPXMock) -> None:
        result = await hubspot_log_activity(
            LogActivityParams(
                activity_type="letters",
                properties={"hs_call_title": "Intro call"},
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "activity_type must be one of calls, emails, or meetings." in result.error
        assert httpx_mock.get_requests() == []

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_log_activity._tool_definition
        assert defn.name == "hubspot_log_activity"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.contacts.write"]


# ---------------------------------------------------------------------------
# hubspot_list_pipelines
# ---------------------------------------------------------------------------


class TestListPipelines:
    async def test_success_default_deals(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/pipelines/deals",
            method="GET",
            json=_load_json("list_pipelines.json"),
        )

        result = await hubspot_list_pipelines(
            ListPipelinesParams(),
            token=_TOKEN,
        )

        assert isinstance(result, ListPipelinesResult)
        assert result.success is True
        assert result.object_type == "deals"
        assert len(result.pipelines) == 1
        pipeline = result.pipelines[0]
        assert pipeline.id == "default"
        assert pipeline.label == "Sales Pipeline"
        assert len(pipeline.stages) == 2
        assert pipeline.stages[0].id == "appointmentscheduled"
        assert pipeline.stages[0].label == "Appointment Scheduled"

    async def test_rejects_non_deal_object_types(self) -> None:
        with pytest.raises(ValidationError):
            ListPipelinesParams(object_type="tickets")  # type: ignore[arg-type]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/pipelines/deals",
            method="GET",
            status_code=403,
            text="Forbidden",
        )

        result = await hubspot_list_pipelines(
            ListPipelinesParams(),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_list_pipelines._tool_definition
        assert defn.name == "hubspot_list_pipelines"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.deals.read"]


# ---------------------------------------------------------------------------
# hubspot_list_owners
# ---------------------------------------------------------------------------


class TestListOwners:
    async def test_success_returns_all(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/owners?archived=false",
            method="GET",
            json=_load_json("list_owners.json"),
        )

        result = await hubspot_list_owners(
            ListOwnersParams(),
            token=_TOKEN,
        )

        assert isinstance(result, ListOwnersResult)
        assert result.success is True
        assert len(result.owners) == 2
        assert result.owners[0].email == "owner@example.com"
        assert result.owners[0].first_name == "Casey"
        assert result.owners[0].user_id == 42

    async def test_query_filters_case_insensitively(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/owners?archived=false",
            method="GET",
            json=_load_json("list_owners.json"),
        )

        result = await hubspot_list_owners(
            ListOwnersParams(query="OWNER@example.com"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.owners) == 1
        assert result.owners[0].email == "owner@example.com"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE_URL}/crm/v3/owners?archived=false",
            method="GET",
            status_code=401,
            text="Unauthorized",
        )

        result = await hubspot_list_owners(
            ListOwnersParams(),
            token=_TOKEN,
        )

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = hubspot_list_owners._tool_definition
        assert defn.name == "hubspot_list_owners"
        assert defn.provider == "hubspot"
        assert defn.scopes == ["crm.objects.owners.read"]
