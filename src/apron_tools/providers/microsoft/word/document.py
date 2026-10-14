"""Pure synchronous functions for .docx format manipulation.

No network calls, no tokens. Takes bytes in, returns bytes out.
Independently testable by creating real .docx content in memory.
"""

from __future__ import annotations

import io
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager

from docx import Document
from docx.document import Document as DocxDocument
from docx.exceptions import InvalidXmlError
from lxml import etree  # ty: ignore[unresolved-import]

from apron_tools._ooxml import OfficePackageError, TextBudget, check_package

_INVALID_DOCUMENT_ERRORS = (
    AttributeError,
    IndexError,
    InvalidXmlError,
    KeyError,
    NotImplementedError,
    TypeError,
    ValueError,
    etree.XMLSyntaxError,
    zipfile.BadZipFile,
    zlib.error,
)


@contextmanager
def _as_invalid_document_error() -> Iterator[None]:
    """Report a document that the parser cannot read, or whose XML has an unexpected structure, as invalid.

    The parser reports unexpected structure through the errors that its object model raises,
    such as a missing attribute or child, so these errors are treated as an invalid document.

    NOTE: An error from another cause, such as a defect or caller text that XML cannot hold, is also reported this way.
    The original error is kept as the cause.
    This trade-off is worth re-reviewing if the parser starts to validate the structure when it opens a file.

    Raises:
        OfficePackageError: If the document is not a valid Word document.
    """
    try:
        yield
    # NOTE: OfficePackageError is a ValueError, so it must pass through before the broader catch.
    except OfficePackageError:
        raise
    except _INVALID_DOCUMENT_ERRORS as exc:
        raise OfficePackageError("The file is not a valid Word document.") from exc


@_as_invalid_document_error()
def _open_document(docx_bytes: bytes) -> DocxDocument:
    """Open a Word document from untrusted bytes.

    Args:
        docx_bytes: Raw .docx file bytes.

    Returns:
        The open document.

    Raises:
        OfficePackageError: If the package is not a valid Word document or is over the size limits.
    """
    check_package(docx_bytes)
    return Document(io.BytesIO(docx_bytes))


def build_docx(content: str = "") -> bytes:
    """Create a new Word document with optional paragraph content.

    Args:
        content: If non-empty, each line becomes a paragraph.
            Otherwise, creates an empty document.

    Returns:
        The .docx file content as bytes.
    """
    doc = Document()

    if content:
        for line in content.splitlines():
            doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@_as_invalid_document_error()
def extract_text(docx_bytes: bytes) -> dict:
    """Extract plain text from paragraphs and tables in a Word document, up to the text limit.

    Args:
        docx_bytes: Raw .docx file bytes.

    Returns:
        A dict containing:
        - paragraphs: list of paragraph text strings.
        - tables: list of tables, each a list of rows, each a list of cell strings.
        - truncated: whether text was cut at the text limit.

    Raises:
        OfficePackageError: If the package is not valid or is over the size limits.
    """
    doc = _open_document(docx_bytes)
    budget = TextBudget()

    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = budget.take(para.text.strip())
        if text:
            paragraphs.append(text)
        if budget.exhausted:
            break

    tables: list[list[list[str]]] = []
    for table in doc.tables:
        if budget.exhausted:
            break
        table_data: list[list[str]] = []
        for row in table.rows:
            seen_cells: set[int] = set()
            row_data: list[str] = []
            for cell in row.cells:
                cell_id = id(cell._element)
                if cell_id in seen_cells:
                    continue
                seen_cells.add(cell_id)
                row_data.append(budget.take(cell.text.strip()))
                if budget.exhausted:
                    break
            table_data.append(row_data)
            if budget.exhausted:
                break
        tables.append(table_data)

    return {
        "paragraphs": paragraphs,
        "tables": tables,
        "truncated": budget.exhausted,
    }


@_as_invalid_document_error()
def append_content(docx_bytes: bytes, content: str) -> bytes:
    """Append paragraphs to an existing Word document.

    Args:
        docx_bytes: Raw .docx file bytes.
        content: Text to append; each line becomes a new paragraph.

    Returns:
        The updated .docx file content as bytes.

    Raises:
        OfficePackageError: If the package is not valid or is over the size limits.
    """
    doc = _open_document(docx_bytes)

    for line in content.splitlines():
        doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
