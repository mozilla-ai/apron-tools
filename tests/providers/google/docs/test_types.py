"""Tests for Google Docs provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.google.docs.types import (
    Comment,
    CopyDocumentParams,
    CopyDocumentResult,
    CreateCommentParams,
    CreateCommentResult,
    CreateDocumentParams,
    CreateDocumentResult,
    DateElement,
    DocumentFile,
    ListDocumentsParams,
    ListDocumentsResult,
    ParagraphElement,
    Person,
    ReadCommentsParams,
    ReadCommentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    ReplyToCommentParams,
    ReplyToCommentResult,
    RichLink,
    UpdateDocumentParams,
    UpdateDocumentResult,
    UpdateTableCellParams,
    UpdateTableCellResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListDocumentsParams:
    def test_defaults(self):
        params = ListDocumentsParams()
        assert params.max_results == 20

    def test_custom(self):
        params = ListDocumentsParams(max_results=5)
        assert params.max_results == 5


class TestCreateDocumentParams:
    def test_required(self):
        params = CreateDocumentParams(title="Meeting Notes")
        assert params.title == "Meeting Notes"
        assert params.content == ""

    def test_with_content(self):
        params = CreateDocumentParams(title="Notes", content="# Hello")
        assert params.content == "# Hello"


class TestReadDocumentParams:
    def test_required(self):
        params = ReadDocumentParams(document_id="doc-001")
        assert params.document_id == "doc-001"
        assert params.include_metadata is False

    def test_custom(self):
        params = ReadDocumentParams(document_id="doc-001", include_metadata=True)
        assert params.include_metadata is True


class TestUpdateDocumentParams:
    def test_required(self):
        params = UpdateDocumentParams(
            document_id="doc-001",
            requests=[{"insertText": {"location": {"index": 1}, "text": "Hello\n"}}],
        )
        assert params.document_id == "doc-001"
        assert len(params.requests) == 1

    def test_multiple_requests(self):
        params = UpdateDocumentParams(
            document_id="doc-001",
            requests=[
                {"insertText": {"location": {"index": 1}, "text": "Hello\n"}},
                {"replaceAllText": {"containsText": {"text": "old"}, "replaceText": "new"}},
            ],
        )
        assert len(params.requests) == 2


class TestCopyDocumentParams:
    def test_required(self):
        params = CopyDocumentParams(document_id="doc-001", new_title="Copy")
        assert params.document_id == "doc-001"
        assert params.new_title == "Copy"


# ---------------------------------------------------------------------------
# ListDocumentsResult
# ---------------------------------------------------------------------------


class TestListDocumentsResult:
    def test_parse_files(self):
        data = _load_json("list_documents.json")
        files = [DocumentFile.model_validate(f) for f in data["files"]]
        result = ListDocumentsResult(success=True, files=files)

        assert result.success is True
        assert len(result.files) == 2

    def test_file_fields(self):
        data = _load_json("list_documents.json")
        f = DocumentFile.model_validate(data["files"][0])

        assert f.id == "doc-001"
        assert f.name == "Meeting Notes"
        assert f.created_time == "2024-01-15T10:00:00Z"
        assert f.modified_time == "2024-03-10T14:22:00Z"

    def test_str_output(self):
        data = _load_json("list_documents.json")
        files = [DocumentFile.model_validate(f) for f in data["files"]]
        result = ListDocumentsResult(success=True, files=files)
        text = str(result)

        assert "2 document(s)" in text
        assert "Meeting Notes" in text
        assert "Project Brief" in text

    def test_str_on_error(self):
        result = ListDocumentsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListDocumentsResult(success=True, files=[])
        assert str(result) == "No documents found."


# ---------------------------------------------------------------------------
# CreateDocumentResult
# ---------------------------------------------------------------------------


class TestCreateDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_document.json")
        result = CreateDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert result.title == "Meeting Notes"
        assert result.revision_id == "revision-001"

    def test_str_output(self):
        data = _load_json("create_document.json")
        result = CreateDocumentResult.model_validate(data)
        text = str(result)

        assert "Meeting Notes" in text
        assert "doc-001" in text
        assert "https://docs.google.com/document/d/doc-001/edit" in text

    def test_str_on_error(self):
        result = CreateDocumentResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# Smart chip paragraph elements
# ---------------------------------------------------------------------------


class TestPerson:
    def test_renders_name_and_email(self):
        chip = Person.model_validate({"personProperties": {"name": "Ada Lovelace", "email": "ada@example.com"}})
        assert chip.text_content == "Ada Lovelace <ada@example.com>"

    def test_renders_email_alone_without_a_name(self):
        chip = Person.model_validate({"personProperties": {"email": "ada@example.com"}})
        assert chip.text_content == "ada@example.com"

    def test_renders_name_alone_without_an_email(self):
        chip = Person.model_validate({"personProperties": {"name": "Ada Lovelace"}})
        assert chip.text_content == "Ada Lovelace"

    def test_renders_empty_without_either_value(self):
        assert Person().text_content == ""


class TestRichLink:
    def test_renders_a_markdown_link(self):
        chip = RichLink.model_validate(
            {"richLinkProperties": {"title": "Kickoff Spec", "uri": "https://example.com/spec"}}
        )
        assert chip.text_content == "[Kickoff Spec](https://example.com/spec)"

    def test_renders_title_alone_without_a_uri(self):
        chip = RichLink.model_validate({"richLinkProperties": {"title": "Kickoff Spec"}})
        assert chip.text_content == "Kickoff Spec"

    def test_renders_uri_alone_without_a_title(self):
        chip = RichLink.model_validate({"richLinkProperties": {"uri": "https://example.com/spec"}})
        assert chip.text_content == "https://example.com/spec"

    def test_renders_empty_without_either_value(self):
        assert RichLink().text_content == ""


class TestDateElement:
    def test_prefers_display_text(self):
        chip = DateElement.model_validate(
            {"dateElementProperties": {"displayText": "3 March 2026", "timestamp": "2026-03-03T00:00:00Z"}}
        )
        assert chip.text_content == "3 March 2026"

    def test_falls_back_to_the_timestamp_without_display_text(self):
        chip = DateElement.model_validate({"dateElementProperties": {"timestamp": "2026-03-03T00:00:00Z"}})
        assert chip.text_content == "2026-03-03T00:00:00Z"

    def test_renders_empty_without_either_value(self):
        assert DateElement().text_content == ""


class TestParagraphElement:
    def test_renders_text_run_content(self):
        element = ParagraphElement.model_validate({"textRun": {"content": "Owner: "}})
        assert element.text_content == "Owner: "

    def test_renders_empty_for_an_unmodeled_element(self):
        element = ParagraphElement.model_validate({"horizontalRule": {}})
        assert element.text_content == ""


# ---------------------------------------------------------------------------
# ReadDocumentResult
# ---------------------------------------------------------------------------


class TestReadDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert result.title == "Meeting Notes"
        assert result.revision_id == "revision-001"

    def test_text_content(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)
        text = result.text_content

        assert "Meeting Notes" in text
        assert "Discussion points for today." in text

    def test_text_content_renders_smart_chips(self):
        data = _load_json("read_document_smart_chips.json")
        result = ReadDocumentResult.model_validate(data)

        assert result.text_content == (
            "Owner: Ada Lovelace <ada@example.com>\n"
            "Spec: [Kickoff Spec](https://docs.google.com/document/d/spec-001/edit)\n"
            "Due: 3 March 2026\n"
            "Contact: grace@example.com\n"
        )

    def test_smart_chip_values_are_available_unrendered(self):
        data = _load_json("read_document_smart_chips.json")
        result = ReadDocumentResult.model_validate(data)
        elements = result.body.content[1].paragraph.elements

        assert elements[1].person is not None
        assert elements[1].person.person_properties.email == "ada@example.com"

    def test_str_output(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)
        text = str(result)

        assert "Meeting Notes" in text
        assert "chars" in text

    def test_str_empty_document(self):
        result = ReadDocumentResult(
            success=True,
            document_id="doc-001",
            title="Empty Doc",
        )
        assert "empty" in str(result).lower()

    def test_str_on_error(self):
        result = ReadDocumentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# UpdateDocumentResult
# ---------------------------------------------------------------------------


class TestUpdateDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("update_document.json")
        result = UpdateDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert len(result.replies) == 1
        assert result.write_control.required_revision_id == "revision-002"

    def test_str_output(self):
        data = _load_json("update_document.json")
        result = UpdateDocumentResult.model_validate(data)
        text = str(result)

        assert "doc-001" in text
        assert "revision-002" in text

    def test_str_on_error(self):
        result = UpdateDocumentResult(success=False, error="Permission denied")
        assert str(result) == "Error: Permission denied"


# ---------------------------------------------------------------------------
# CopyDocumentResult
# ---------------------------------------------------------------------------


class TestCopyDocumentResult:
    def test_success(self):
        result = CopyDocumentResult(
            success=True,
            id="doc-003",
            name="Copy of Meeting Notes",
            original_name="Meeting Notes",
        )

        assert result.success is True
        assert result.id == "doc-003"
        assert result.name == "Copy of Meeting Notes"
        assert result.original_name == "Meeting Notes"

    def test_str_output(self):
        result = CopyDocumentResult(
            success=True,
            id="doc-003",
            name="Copy of Meeting Notes",
            original_name="Meeting Notes",
        )
        text = str(result)

        assert "copied" in text.lower()
        assert "Meeting Notes" in text
        assert "Copy of Meeting Notes" in text
        assert "doc-003" in text

    def test_str_on_error(self):
        result = CopyDocumentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# UpdateTableCell
# ---------------------------------------------------------------------------


class TestUpdateTableCellParams:
    def test_defaults(self):
        params = UpdateTableCellParams(document_id="doc-001", table_index=0, row=0, column=0)
        assert params.text == ""

    def test_rejects_negative_indices(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UpdateTableCellParams(document_id="doc-001", table_index=-1, row=0, column=0)
        with pytest.raises(ValidationError):
            UpdateTableCellParams(document_id="doc-001", table_index=0, row=-1, column=0)
        with pytest.raises(ValidationError):
            UpdateTableCellParams(document_id="doc-001", table_index=0, row=0, column=-1)


class TestUpdateTableCellResult:
    def test_str_success(self):
        result = UpdateTableCellResult(
            success=True,
            document_id="doc-001",
            title="Weekly Report",
            table_index=0,
            row=1,
            column=2,
        )
        text = str(result)
        assert "row: 1" in text
        assert "column: 2" in text
        assert "Weekly Report" in text

    def test_str_on_error(self):
        result = UpdateTableCellResult(success=False, error="not found")
        assert str(result) == "Error: not found"


# ---------------------------------------------------------------------------
# ReadComments
# ---------------------------------------------------------------------------


class TestReadCommentsParams:
    def test_defaults(self):
        params = ReadCommentsParams(document_id="doc-001")
        assert params.max_results == 20
        assert params.include_resolved is False


class TestReadCommentsResult:
    def test_parse_and_render_comments(self):
        data = _load_json("read_comments.json")
        comments = [Comment.model_validate(c) for c in data["comments"]]
        result = ReadCommentsResult(
            success=True,
            document_id="doc-001",
            title="Project Proposal",
            comments=comments,
        )
        text = str(result)
        assert "Project Proposal" in text
        assert "cmt-001" in text
        assert "Alice" in text
        assert "Bob" in text
        assert "Quoted text" in text

    def test_str_on_error(self):
        result = ReadCommentsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty_open(self):
        result = ReadCommentsResult(success=True, document_id="doc-001", title="Project")
        assert "No open comments" in str(result)

    def test_str_empty_include_resolved(self):
        result = ReadCommentsResult(
            success=True,
            document_id="doc-001",
            title="Project",
            include_resolved=True,
        )
        assert "No comments" in str(result)

    def test_has_more_notice(self):
        data = _load_json("read_comments.json")
        comments = [Comment.model_validate(c) for c in data["comments"]]
        result = ReadCommentsResult(
            success=True,
            document_id="doc-001",
            title="Project",
            comments=comments,
            has_more=True,
        )
        assert "More comments exist" in str(result)


# ---------------------------------------------------------------------------
# CreateComment
# ---------------------------------------------------------------------------


class TestCreateCommentParams:
    def test_required_only(self):
        params = CreateCommentParams(document_id="doc-001", comment="Hi")
        assert params.quoted_text == ""


class TestCreateCommentResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_comment.json")
        result = CreateCommentResult.model_validate(data)

        assert result.success is True
        assert result.id == "cmt-003"
        assert result.author.display_name == "Alice"
        assert result.quoted_file_content is not None
        assert result.quoted_file_content.value == "the text I am anchoring to"

    def test_str_output_includes_anchor(self):
        data = _load_json("create_comment.json")
        result = CreateCommentResult.model_validate(data)
        text = str(result)
        assert "cmt-003" in text
        assert "Alice" in text
        assert "Anchored to" in text

    def test_str_on_error(self):
        result = CreateCommentResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# ReplyToComment
# ---------------------------------------------------------------------------


class TestReplyToCommentParams:
    def test_required(self):
        params = ReplyToCommentParams(document_id="doc-001", comment_id="cmt-001", reply="Thanks")
        assert params.reply == "Thanks"


class TestReplyToCommentResult:
    def test_parse_real_api_response(self):
        data = _load_json("reply_to_comment.json")
        result = ReplyToCommentResult.model_validate(data)

        assert result.success is True
        assert result.id == "rep-002"
        assert result.author.display_name == "Bob"

    def test_str_output(self):
        data = _load_json("reply_to_comment.json")
        result = ReplyToCommentResult.model_validate(data)
        text = str(result)
        assert "rep-002" in text
        assert "Bob" in text

    def test_str_on_error(self):
        result = ReplyToCommentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"
