"""Tests for Salesforce tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from apron_tools.providers.salesforce.tools import (
    _instance_url_cache,
    salesforce_create_record,
    salesforce_explore_org,
    salesforce_get_record,
    salesforce_query_records,
    salesforce_search_records,
    salesforce_update_records,
)
from apron_tools.providers.salesforce.types import (
    CreateRecordParams,
    CreateRecordResult,
    ExploreOrgParams,
    ExploreOrgResult,
    GetRecordParams,
    GetRecordResult,
    QueryRecordsParams,
    QueryRecordsResult,
    SearchRecordsParams,
    SearchRecordsResult,
    UpdateRecordsParams,
    UpdateRecordsResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "sf_test_token_abc123"
_USERINFO_URL = "https://login.salesforce.com/services/oauth2/userinfo"
_INSTANCE_URL = "https://mycompany.my.salesforce.com"
_API_BASE = f"{_INSTANCE_URL}/services/data/v62.0"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


def _mock_userinfo(httpx_mock: HTTPXMock) -> None:
    """Register a mock response for the Salesforce userinfo endpoint."""
    httpx_mock.add_response(
        url=_USERINFO_URL,
        json=_load_json("userinfo.json"),
    )


@pytest.fixture(autouse=True)
def _clear_instance_url_cache() -> None:
    """Clear the instance URL cache before each test."""
    _instance_url_cache.clear()


# ---------------------------------------------------------------------------
# salesforce_explore_org
# ---------------------------------------------------------------------------


class TestExploreOrg:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_BASE}/sobjects",
            json=_load_json("explore_org.json"),
        )

        result = await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, ExploreOrgResult)
        assert result.success is True
        assert len(result.sobjects) == 2
        assert result.sobjects[0].name == "Account"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_BASE}/sobjects",
            json=_load_json("explore_org.json"),
        )

        await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert api_request.headers["authorization"] == f"Bearer {_TOKEN}"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(
            url=f"{_API_BASE}/sobjects",
            status_code=403,
            text="Forbidden",
        )

        result = await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert result.error is not None
        assert "403" in result.error

    async def test_userinfo_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_USERINFO_URL, status_code=401, text="Unauthorized")

        result = await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert "instance URL" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_explore_org._tool_definition
        assert defn.name == "salesforce_explore_org"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "describeGlobal" in defn.api_docs_url


# ---------------------------------------------------------------------------
# salesforce_query_records
# ---------------------------------------------------------------------------


class TestQueryRecords:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("query_records.json"))

        result = await salesforce_query_records(
            QueryRecordsParams(soql="SELECT Id, Name FROM Contact"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, QueryRecordsResult)
        assert result.success is True
        assert result.total_size == 2
        assert result.done is True
        assert len(result.records) == 2
        assert result.records[0]["Id"] == "003-001"

    async def test_soql_in_query_param(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("query_records.json"))

        await salesforce_query_records(
            QueryRecordsParams(soql="SELECT Id FROM Account"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert "q=SELECT" in str(api_request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await salesforce_query_records(
            QueryRecordsParams(soql="INVALID SOQL"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_query_records._tool_definition
        assert defn.name == "salesforce_query_records"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "resources_query" in defn.api_docs_url


# ---------------------------------------------------------------------------
# salesforce_get_record
# ---------------------------------------------------------------------------


class TestGetRecord:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("get_record.json"))

        result = await salesforce_get_record(
            GetRecordParams(object_type="Account", record_id="001-001"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, GetRecordResult)
        assert result.success is True
        assert result.record["Id"] == "001-001"
        assert result.record["Name"] == "Acme Corp"
        assert result.record["Industry"] == "Technology"

    async def test_url_construction(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("get_record.json"))

        await salesforce_get_record(
            GetRecordParams(object_type="Account", record_id="001-001"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert "/sobjects/Account/001-001" in str(api_request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await salesforce_get_record(
            GetRecordParams(object_type="Account", record_id="missing"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_get_record._tool_definition
        assert defn.name == "salesforce_get_record"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "dome_get_field_values" in defn.api_docs_url


# ---------------------------------------------------------------------------
# salesforce_create_record
# ---------------------------------------------------------------------------


class TestCreateRecord:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("create_record.json"))

        result = await salesforce_create_record(
            CreateRecordParams(object_type="Account", fields={"Name": "New Corp"}),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, CreateRecordResult)
        assert result.success is True
        assert result.id == "001-002"
        assert result.errors == []

    async def test_sends_json_body(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("create_record.json"))

        await salesforce_create_record(
            CreateRecordParams(object_type="Account", fields={"Name": "Test"}),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert api_request.method == "POST"
        assert json.loads(api_request.content) == {"Name": "Test"}

    async def test_url_construction(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("create_record.json"))

        await salesforce_create_record(
            CreateRecordParams(object_type="Lead", fields={"LastName": "Smith"}),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert "/sobjects/Lead" in str(api_request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=400, text="Required field missing")

        result = await salesforce_create_record(
            CreateRecordParams(object_type="Account", fields={}),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_create_record._tool_definition
        assert defn.name == "salesforce_create_record"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "resources_sobject_basic_info" in defn.api_docs_url


# ---------------------------------------------------------------------------
# salesforce_update_records
# ---------------------------------------------------------------------------


class TestUpdateRecords:
    async def test_single_record(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=204)

        result = await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Account",
                record_ids="001-001",
                fields={"Name": "Updated Corp"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, UpdateRecordsResult)
        assert result.success is True
        assert result.object_type == "Account"
        assert len(result.items) == 1
        assert result.items[0].record_id == "001-001"
        assert result.items[0].success is True

    async def test_multiple_records(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=204)
        httpx_mock.add_response(status_code=204)

        result = await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Account",
                record_ids="001-001, 001-002",
                fields={"Industry": "Finance"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is True
        assert [item.record_id for item in result.items] == ["001-001", "001-002"]
        assert all(item.success for item in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=204)
        httpx_mock.add_response(status_code=404, text="Entity not found")

        result = await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Account",
                record_ids="001-001,missing",
                fields={"Name": "X"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "404" in result.items[1].error

    async def test_empty_record_ids(self) -> None:
        result = await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Account",
                record_ids=" , ",
                fields={"Name": "X"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert result.error == "No record IDs provided."

    async def test_sends_patch_with_json(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=204)

        await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Account",
                record_ids="001-001",
                fields={"Industry": "Finance"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert api_request.method == "PATCH"
        assert json.loads(api_request.content) == {"Industry": "Finance"}

    async def test_url_construction(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=204)

        await salesforce_update_records(
            UpdateRecordsParams(
                object_type="Contact",
                record_ids="003-001",
                fields={"Email": "new@example.com"},
            ),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert "/sobjects/Contact/003-001" in str(api_request.url)

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_update_records._tool_definition
        assert defn.name == "salesforce_update_records"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "resources_sobject_update" in defn.api_docs_url


# ---------------------------------------------------------------------------
# salesforce_search_records
# ---------------------------------------------------------------------------


class TestSearchRecords:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("search_records.json"))

        result = await salesforce_search_records(
            SearchRecordsParams(sosl="FIND {Acme} IN ALL FIELDS RETURNING Account(Id)"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert isinstance(result, SearchRecordsResult)
        assert result.success is True
        assert len(result.search_records) == 2
        assert result.search_records[0]["Id"] == "001-001"

    async def test_sosl_in_query_param(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("search_records.json"))

        await salesforce_search_records(
            SearchRecordsParams(sosl="FIND {Test} IN ALL FIELDS"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        requests = httpx_mock.get_requests()
        api_request = requests[-1]
        assert "q=FIND" in str(api_request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(status_code=400, text="Malformed SOSL")

        result = await salesforce_search_records(
            SearchRecordsParams(sosl="INVALID"),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = salesforce_search_records._tool_definition
        assert defn.name == "salesforce_search_records"
        assert defn.provider == "salesforce"
        assert defn.service == "salesforce"
        assert defn.scopes == ["api"]
        assert "resources_search" in defn.api_docs_url


# ---------------------------------------------------------------------------
# Instance URL caching
# ---------------------------------------------------------------------------


class TestInstanceUrlCaching:
    async def test_caches_instance_url(self, httpx_mock: HTTPXMock) -> None:
        _mock_userinfo(httpx_mock)
        httpx_mock.add_response(json=_load_json("explore_org.json"))
        httpx_mock.add_response(json=_load_json("explore_org.json"))

        await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )
        await salesforce_explore_org(
            ExploreOrgParams(),
            token=_TOKEN,
            userinfo_url=_USERINFO_URL,
        )

        # Userinfo should only be called once due to caching.
        userinfo_requests = [r for r in httpx_mock.get_requests() if "userinfo" in str(r.url)]
        assert len(userinfo_requests) == 1
