"""Pure unit tests for .docx format manipulation.

No mocks — creates real .docx bytes and verifies their content.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from docx import Document
from lxml import etree

from apron_tools import _ooxml
from apron_tools._ooxml import OfficePackageError
from apron_tools.providers.microsoft.powerpoint.presentation import build_pptx
from apron_tools.providers.microsoft.word.document import (
    append_content,
    build_docx,
    extract_text,
)


def _package(name: str, data: bytes, *, declared_compression: int = zipfile.ZIP_STORED) -> bytes:
    """Build a one-part package whose central directory declares the given compression method."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, data)
        zf.infolist()[0].compress_type = declared_compression
    return buf.getvalue()


def _replace_part(package: bytes, name: str, data: bytes) -> bytes:
    """Return a copy of a package with one part's content replaced."""
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as src, zipfile.ZipFile(buf, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, data if info.filename == name else src.read(info))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# build_docx
# ---------------------------------------------------------------------------


class TestBuildDocx:
    def test_empty(self) -> None:
        data = build_docx()
        doc = Document(io.BytesIO(data))
        assert len(doc.paragraphs) == 0

    def test_with_content(self) -> None:
        data = build_docx("Hello World\nSecond line")
        doc = Document(io.BytesIO(data))
        texts = [p.text for p in doc.paragraphs]
        assert "Hello World" in texts
        assert "Second line" in texts

    def test_single_line(self) -> None:
        data = build_docx("Just one paragraph")
        doc = Document(io.BytesIO(data))
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].text == "Just one paragraph"

    def test_empty_string_creates_empty_doc(self) -> None:
        data = build_docx("")
        doc = Document(io.BytesIO(data))
        assert len(doc.paragraphs) == 0


# ---------------------------------------------------------------------------
# extract_text
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_not_truncated_within_limit(self) -> None:
        result = extract_text(build_docx("Hello World"))
        assert result["truncated"] is False

    def test_truncates_text_over_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_TEXT_CHARS", 10)
        doc = Document()
        doc.add_paragraph("Hello World")
        doc.add_paragraph("Second")
        table = doc.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "Cell"
        buf = io.BytesIO()
        doc.save(buf)

        result = extract_text(buf.getvalue())

        assert result["paragraphs"] == ["Hello Worl"]
        assert result["tables"] == []
        assert result["truncated"] is True

    def test_truncates_inside_table(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_TEXT_CHARS", 7)
        doc = Document()
        doc.add_paragraph("Intro")
        table = doc.add_table(rows=2, cols=1)
        table.cell(0, 0).text = "Alpha"
        table.cell(1, 0).text = "Beta"
        buf = io.BytesIO()
        doc.save(buf)

        result = extract_text(buf.getvalue())

        assert result["paragraphs"] == ["Intro"]
        assert result["tables"] == [[["Al"]]]
        assert result["truncated"] is True

    def test_basic_extraction(self) -> None:
        data = build_docx("Hello World")
        result = extract_text(data)
        assert "Hello World" in result["paragraphs"]
        assert result["tables"] == []

    def test_empty_document(self) -> None:
        data = build_docx()
        result = extract_text(data)
        assert result["paragraphs"] == []
        assert result["tables"] == []

    def test_multi_paragraph(self) -> None:
        data = build_docx("First\nSecond\nThird")
        result = extract_text(data)
        assert len(result["paragraphs"]) == 3
        assert result["paragraphs"][0] == "First"
        assert result["paragraphs"][1] == "Second"
        assert result["paragraphs"][2] == "Third"

    def test_table_extraction(self) -> None:
        """Build a document with a table and verify extraction."""
        doc = Document()
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "A1"
        table.cell(0, 1).text = "B1"
        table.cell(1, 0).text = "A2"
        table.cell(1, 1).text = "B2"
        buf = io.BytesIO()
        doc.save(buf)

        result = extract_text(buf.getvalue())
        assert len(result["tables"]) == 1
        assert result["tables"][0][0] == ["A1", "B1"]
        assert result["tables"][0][1] == ["A2", "B2"]

    def test_paragraphs_and_tables(self) -> None:
        """Document with both paragraphs and a table."""
        doc = Document()
        doc.add_paragraph("Before table")
        table = doc.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Col1"
        table.cell(0, 1).text = "Col2"
        doc.add_paragraph("After table")
        buf = io.BytesIO()
        doc.save(buf)

        result = extract_text(buf.getvalue())
        assert "Before table" in result["paragraphs"]
        assert "After table" in result["paragraphs"]
        assert len(result["tables"]) == 1


# ---------------------------------------------------------------------------
# append_content
# ---------------------------------------------------------------------------


class TestAppendContent:
    def test_append_to_empty(self) -> None:
        data = build_docx()
        updated = append_content(data, "New content")
        doc = Document(io.BytesIO(updated))
        texts = [p.text for p in doc.paragraphs]
        assert "New content" in texts

    def test_append_preserves_existing(self) -> None:
        data = build_docx("Original")
        updated = append_content(data, "Appended")
        doc = Document(io.BytesIO(updated))
        texts = [p.text for p in doc.paragraphs]
        assert "Original" in texts
        assert "Appended" in texts

    def test_append_multi_line(self) -> None:
        data = build_docx("First")
        updated = append_content(data, "Second\nThird")
        doc = Document(io.BytesIO(updated))
        texts = [p.text for p in doc.paragraphs]
        assert "First" in texts
        assert "Second" in texts
        assert "Third" in texts

    def test_returns_different_bytes(self) -> None:
        original = build_docx("Start")
        updated = append_content(original, "End")
        assert original != updated


# ---------------------------------------------------------------------------
# invalid packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(build_pptx("Title"), id="wrong-format"),
        pytest.param(_package("part.xml", b"<x/>"), id="missing-parts"),
        pytest.param(
            _package("[Content_Types].xml", b"\xff" * 16, declared_compression=zipfile.ZIP_DEFLATED),
            id="corrupt-part",
        ),
        pytest.param(_replace_part(build_docx("Text"), "word/document.xml", b"<not-closed"), id="malformed-main-part"),
        pytest.param(
            _replace_part(build_docx("Text"), "[Content_Types].xml", b"<not-closed"), id="malformed-content-types"
        ),
    ],
)
class TestInvalidPackage:
    def test_extract_text_rejects_package(self, data: bytes) -> None:
        with pytest.raises(OfficePackageError, match="not a valid Word document"):
            extract_text(data)

    def test_append_content_rejects_package(self, data: bytes) -> None:
        with pytest.raises(OfficePackageError, match="not a valid Word document"):
            append_content(data, "Text")


@pytest.mark.parametrize("part", ["word/document.xml", "[Content_Types].xml"])
def test_malformed_xml_part_keeps_parse_error_as_cause(part: str) -> None:
    data = _replace_part(build_docx("Title"), part, b"<not-closed")
    with pytest.raises(OfficePackageError) as exc_info:
        extract_text(data)
    assert isinstance(exc_info.value.__cause__, etree.XMLSyntaxError)
