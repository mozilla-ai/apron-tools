"""Tests for Salesforce provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

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
    UpdateRecordItem,
    UpdateRecordsParams,
    UpdateRecordsResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreOrgParams:
    def test_no_required_fields(self):
        params = ExploreOrgParams()
        assert params is not None


class TestQueryRecordsParams:
    def test_required_soql(self):
        params = QueryRecordsParams(soql="SELECT Id FROM Account")
        assert params.soql == "SELECT Id FROM Account"


class TestGetRecordParams:
    def test_required_fields(self):
        params = GetRecordParams(object_type="Account", record_id="001-001")
        assert params.object_type == "Account"
        assert params.record_id == "001-001"


class TestCreateRecordParams:
    def test_required_fields(self):
        params = CreateRecordParams(
            object_type="Account",
            fields={"Name": "Acme Corp"},
        )
        assert params.object_type == "Account"
        assert params.fields == {"Name": "Acme Corp"}


class TestUpdateRecordsParams:
    def test_required_fields(self):
        params = UpdateRecordsParams(
            object_type="Account",
            record_ids="001-001",
            fields={"Name": "Acme Inc"},
        )
        assert params.object_type == "Account"
        assert params.record_ids == "001-001"
        assert params.fields == {"Name": "Acme Inc"}

    def test_multiple_ids(self):
        params = UpdateRecordsParams(
            object_type="Account",
            record_ids="001-001,001-002",
            fields={"Name": "Acme Inc"},
        )
        assert params.record_ids == "001-001,001-002"


class TestSearchRecordsParams:
    def test_required_sosl(self):
        params = SearchRecordsParams(sosl="FIND {Acme} IN ALL FIELDS")
        assert params.sosl == "FIND {Acme} IN ALL FIELDS"


# ---------------------------------------------------------------------------
# ExploreOrgResult
# ---------------------------------------------------------------------------


class TestExploreOrgResult:
    def test_parse_api_response(self):
        data = _load_json("explore_org.json")
        result = ExploreOrgResult.model_validate(data)

        assert result.success is True
        assert result.error is None
        assert len(result.sobjects) == 2

    def test_sobject_fields(self):
        data = _load_json("explore_org.json")
        result = ExploreOrgResult.model_validate(data)
        account = result.sobjects[0]

        assert account.name == "Account"
        assert account.label == "Account"
        assert account.label_plural == "Accounts"
        assert account.key_prefix == "001"
        assert account.queryable is True
        assert account.searchable is True
        assert account.createable is True
        assert account.custom is False

    def test_custom_object(self):
        data = _load_json("explore_org.json")
        result = ExploreOrgResult.model_validate(data)
        invoice = result.sobjects[1]

        assert invoice.name == "Invoice__c"
        assert invoice.custom is True

    def test_str_output(self):
        data = _load_json("explore_org.json")
        result = ExploreOrgResult.model_validate(data)
        text = str(result)

        assert "2 object(s)" in text
        assert "Account" in text
        assert "Invoice" in text
        assert "queryable" in text

    def test_str_on_error(self):
        result = ExploreOrgResult(success=False, error="Connection refused")
        assert str(result) == "Error: Connection refused"


# ---------------------------------------------------------------------------
# QueryRecordsResult
# ---------------------------------------------------------------------------


class TestQueryRecordsResult:
    def test_parse_api_response(self):
        data = _load_json("query_records.json")
        result = QueryRecordsResult.model_validate(data)

        assert result.success is True
        assert result.total_size == 2
        assert result.done is True
        assert len(result.records) == 2

    def test_record_fields(self):
        data = _load_json("query_records.json")
        result = QueryRecordsResult.model_validate(data)
        record = result.records[0]

        assert record["Id"] == "003-001"
        assert record["Name"] == "John Smith"

    def test_str_output(self):
        data = _load_json("query_records.json")
        result = QueryRecordsResult.model_validate(data)
        text = str(result)

        assert "2 record(s)" in text
        assert "John Smith" in text
        assert "Jane Doe" in text

    def test_str_on_error(self):
        result = QueryRecordsResult(success=False, error="Invalid SOQL")
        assert str(result) == "Error: Invalid SOQL"


# ---------------------------------------------------------------------------
# GetRecordResult
# ---------------------------------------------------------------------------


class TestGetRecordResult:
    def test_parse_api_response(self):
        data = _load_json("get_record.json")
        result = GetRecordResult(success=True, record=data)

        assert result.success is True
        assert result.record["Id"] == "001-001"
        assert result.record["Name"] == "Acme Corp"
        assert result.record["Industry"] == "Technology"

    def test_str_output(self):
        data = _load_json("get_record.json")
        result = GetRecordResult(success=True, record=data)
        text = str(result)

        assert "001-001" in text
        assert "Acme Corp" in text

    def test_str_on_error(self):
        result = GetRecordResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# CreateRecordResult
# ---------------------------------------------------------------------------


class TestCreateRecordResult:
    def test_parse_api_response(self):
        data = _load_json("create_record.json")
        result = CreateRecordResult.model_validate(data)

        assert result.success is True
        assert result.id == "001-002"
        assert result.errors == []

    def test_str_output(self):
        data = _load_json("create_record.json")
        result = CreateRecordResult.model_validate(data)
        text = str(result)

        assert "001-002" in text

    def test_str_on_error(self):
        result = CreateRecordResult(success=False, error="Required field missing")
        assert str(result) == "Error: Required field missing"


# ---------------------------------------------------------------------------
# UpdateRecordsResult
# ---------------------------------------------------------------------------


class TestUpdateRecordsResult:
    def test_success(self):
        result = UpdateRecordsResult(
            success=True,
            object_type="Account",
            items=[UpdateRecordItem(record_id="001-001", success=True)],
        )
        assert result.success is True
        assert "Account 001-001 updated" in str(result)

    def test_partial_failure(self):
        result = UpdateRecordsResult(
            success=True,
            object_type="Account",
            items=[
                UpdateRecordItem(record_id="001-001", success=True),
                UpdateRecordItem(record_id="missing", success=False, error="404"),
            ],
        )
        text = str(result)
        assert "Failed: 404" in text

    def test_str_no_items(self):
        result = UpdateRecordsResult(success=True)
        assert "No records processed" in str(result)

    def test_str_on_error(self):
        result = UpdateRecordsResult(success=False, error="Entity is deleted")
        assert str(result) == "Error: Entity is deleted"


# ---------------------------------------------------------------------------
# SearchRecordsResult
# ---------------------------------------------------------------------------


class TestSearchRecordsResult:
    def test_parse_api_response(self):
        data = _load_json("search_records.json")
        result = SearchRecordsResult.model_validate(data)

        assert result.success is True
        assert len(result.search_records) == 2

    def test_record_fields(self):
        data = _load_json("search_records.json")
        result = SearchRecordsResult.model_validate(data)
        record = result.search_records[0]

        assert record["Id"] == "001-001"
        assert record["attributes"]["type"] == "Account"

    def test_str_output(self):
        data = _load_json("search_records.json")
        result = SearchRecordsResult.model_validate(data)
        text = str(result)

        assert "2 record(s)" in text
        assert "Account" in text
        assert "001-001" in text

    def test_str_on_error(self):
        result = SearchRecordsResult(success=False, error="Malformed SOSL")
        assert str(result) == "Error: Malformed SOSL"
