"""Tests for Typeform provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.typeform.types import (
    GetFormParams,
    GetFormResult,
    GetResponsesParams,
    GetResponsesResult,
    ListFormsParams,
    ListFormsResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListFormsParams:
    def test_defaults(self):
        params = ListFormsParams()
        assert params.page == 1
        assert params.page_size == 10
        assert params.search is None
        assert params.workspace_id is None

    def test_custom_values(self):
        params = ListFormsParams(page=2, page_size=50, search="feedback", workspace_id="ws_123")
        assert params.page == 2
        assert params.page_size == 50
        assert params.search == "feedback"
        assert params.workspace_id == "ws_123"


class TestGetFormParams:
    def test_required_form_id(self):
        params = GetFormParams(form_id="abc123")
        assert params.form_id == "abc123"


class TestGetResponsesParams:
    def test_defaults(self):
        params = GetResponsesParams(form_id="abc123")
        assert params.form_id == "abc123"
        assert params.page_size == 25
        assert params.completed is None

    def test_custom_values(self):
        params = GetResponsesParams(
            form_id="abc123",
            page_size=100,
            since="2024-01-01T00:00:00Z",
            completed=True,
        )
        assert params.page_size == 100
        assert params.since == "2024-01-01T00:00:00Z"
        assert params.completed is True


# ---------------------------------------------------------------------------
# ListFormsResult
# ---------------------------------------------------------------------------


class TestListFormsResult:
    def test_parse_real_api_response(self):
        data = _load_json("list_forms.json")
        result = ListFormsResult.model_validate(data)

        assert result.success is True
        assert result.error is None
        assert result.total_items == 2
        assert result.page_count == 1
        assert len(result.items) == 2

    def test_form_summary_fields(self):
        data = _load_json("list_forms.json")
        result = ListFormsResult.model_validate(data)
        form = result.items[0]

        assert form.id == "abc123"
        assert form.title == "Customer Feedback"
        assert form.created_at == "2017-09-01T10:00:00Z"
        assert form.last_updated_at == "2017-09-14T22:38:22Z"

    def test_str_output(self):
        data = _load_json("list_forms.json")
        result = ListFormsResult.model_validate(data)
        text = str(result)

        assert "2 form(s)" in text
        assert "Customer Feedback" in text
        assert "Event Registration" in text
        assert "abc123" in text

    def test_str_on_error(self):
        result = ListFormsResult(success=False, error="API rate limited")
        assert str(result) == "Error: API rate limited"


# ---------------------------------------------------------------------------
# GetFormResult
# ---------------------------------------------------------------------------


class TestGetFormResult:
    def test_parse_real_api_response(self):
        data = _load_json("get_form.json")
        result = GetFormResult.model_validate(data)

        assert result.success is True
        assert result.id == "id"
        assert result.title == "title"
        assert result.language == "en"
        assert len(result.fields) == 1
        assert result.hidden == ["string"]

    def test_settings_preserved(self):
        data = _load_json("get_form.json")
        result = GetFormResult.model_validate(data)

        assert result.settings is not None
        assert result.settings["is_public"] is True

    def test_variables_preserved(self):
        data = _load_json("get_form.json")
        result = GetFormResult.model_validate(data)

        assert result.variables is not None
        assert result.variables["score"] == 0

    def test_str_output(self):
        data = _load_json("get_form.json")
        result = GetFormResult.model_validate(data)
        text = str(result)

        assert "Form: title" in text
        assert "id=id" in text
        assert "Language: en" in text
        assert "Fields: 1" in text
        assert "Hidden fields: string" in text

    def test_str_on_error(self):
        result = GetFormResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# GetResponsesResult
# ---------------------------------------------------------------------------


class TestGetResponsesResult:
    def test_parse_real_api_response(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)

        assert result.success is True
        assert result.total_items == 4
        assert result.page_count == 1
        assert len(result.items) == 4

    def test_response_fields(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        resp = result.items[0]

        assert resp.response_id == "21085286190ffad1248d17c4135ee56f"
        assert resp.submitted_at == "2017-09-14T22:38:22Z"
        assert resp.landed_at == "2017-09-14T22:33:59Z"
        assert resp.token == "test21085286190ffad1248d17c4135ee56f"

    def test_text_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[0]

        assert answer.type == "text"
        assert answer.text == "Job opportunities"
        assert answer.field.id == "hVONkQcnSNRj"
        assert answer.field.type == "dropdown"
        assert answer.value == "Job opportunities"

    def test_boolean_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[1]

        assert answer.type == "boolean"
        assert answer.boolean is False
        assert answer.value is False

    def test_email_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[4]

        assert answer.type == "email"
        assert answer.email == "lian1078@other.com"
        assert answer.value == "lian1078@other.com"

    def test_number_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[5]

        assert answer.type == "number"
        assert answer.number == 1
        assert answer.value == 1

    def test_date_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[11]

        assert answer.type == "date"
        assert answer.date == "2012-03-20T00:00:00Z"
        assert answer.value == "2012-03-20T00:00:00Z"

    def test_choice_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[12]

        assert answer.type == "choice"
        assert answer.choice is not None
        assert answer.choice.label == "A friend's experience in Sydney"
        assert answer.value == "A friend's experience in Sydney"

    def test_choices_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[0].answers[10]

        assert answer.type == "choices"
        assert answer.choices is not None
        assert answer.choices.labels == ["New York", "Tokyo"]
        assert answer.value == ["New York", "Tokyo"]

    def test_file_url_answer(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        answer = result.items[1].answers[1]

        assert answer.type == "file_url"
        assert answer.file_url is not None
        assert "aerial_view" in answer.file_url
        assert answer.value == answer.file_url

    def test_calculated_score(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)

        assert result.items[0].calculated == {"score": 2}
        assert result.items[2].calculated == {"score": 10}

    def test_response_variables(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        variables = result.items[0].variables

        assert variables is not None
        assert len(variables) == 2
        assert variables[0]["key"] == "score"

    def test_empty_answers(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        resp = result.items[3]

        assert len(resp.answers) == 0

    def test_str_output(self):
        data = _load_json("get_responses.json")
        result = GetResponsesResult.model_validate(data)
        text = str(result)

        assert "4 response(s)" in text
        assert "21085286190ffad1248d17c4135ee56f" in text  # pragma: allowlist secret
        assert "0 answer(s)" in text

    def test_str_on_error(self):
        result = GetResponsesResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"
