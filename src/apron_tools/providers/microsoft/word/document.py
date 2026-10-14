"""Pure synchronous functions for .docx format manipulation.

No network calls, no tokens. Takes bytes in, returns bytes out.
Independently testable by creating real .docx content in memory.
"""

from __future__ import annotations

import io
import zipfile
import zlib

from docx import Document
from docx.document import Document as DocxDocument

from apron_tools._ooxml import OfficePackageError, TextBudget, check_package


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
    try:
        return Document(io.BytesIO(docx_bytes))
    except (KeyError, ValueError, zipfile.BadZipFile, zlib.error) as exc:
        raise OfficePackageError("The file is not a valid Word document.") from exc


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
