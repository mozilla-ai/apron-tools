"""Pure synchronous functions for .pptx format manipulation.

No network calls, no tokens. Takes bytes in, returns bytes out.
Independently testable by creating real .pptx content in memory.
"""

from __future__ import annotations

import io
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager

from lxml import etree  # ty: ignore[unresolved-import]
from pptx import Presentation as NewPresentation
from pptx.exc import InvalidXmlError
from pptx.presentation import Presentation
from pptx.util import Inches

from apron_tools._ooxml import OfficePackageError, TextBudget, check_package

# Default layout index mapping for the standard python-pptx template.
_LAYOUT_PRESETS: dict[str, int] = {
    "blank": 6,
    "title": 0,
    "title_and_content": 1,
    "section_header": 2,
    "two_content": 3,
    "title_only": 5,
}


_INVALID_PRESENTATION_ERRORS = (
    AttributeError,
    IndexError,
    InvalidXmlError,
    KeyError,
    TypeError,
    ValueError,
    etree.XMLSyntaxError,
    zipfile.BadZipFile,
    zlib.error,
)


@contextmanager
def _invalid_presentation_errors() -> Iterator[None]:
    """Report a presentation that the parser cannot read, or whose XML has an unexpected structure, as invalid.

    The parser reports unexpected structure through the errors that its object model raises,
    such as a missing attribute or child, so these errors are treated as an invalid presentation.

    NOTE: An error from another cause, such as a defect or caller text that XML cannot hold, is also reported this way.
    The original error is kept as the cause.
    This trade-off is worth re-reviewing if the parser starts to validate the structure when it opens a file.

    Raises:
        OfficePackageError: If the presentation is not a valid PowerPoint presentation.
    """
    try:
        yield
    # NOTE: OfficePackageError is a ValueError, so it must pass through before the broader catch.
    except OfficePackageError:
        raise
    except _INVALID_PRESENTATION_ERRORS as exc:
        raise OfficePackageError("The file is not a valid PowerPoint presentation.") from exc


@_invalid_presentation_errors()
def _open_presentation(pptx_bytes: bytes) -> Presentation:
    """Open a PowerPoint presentation from untrusted bytes.

    Args:
        pptx_bytes: Raw .pptx file bytes.

    Returns:
        The open presentation.

    Raises:
        OfficePackageError: If the package is not a valid PowerPoint presentation or is over the size limits.
    """
    check_package(pptx_bytes)
    return NewPresentation(io.BytesIO(pptx_bytes))


def resolve_layout_index(prs: Presentation, layout: str) -> int:
    """Resolve a layout name to an index in the presentation's slide layouts.

    Tries an exact name match (case-insensitive, underscores/hyphens/spaces
    normalized) against the layouts that actually exist in the file first.
    Falls back to the preset map, then to index 0.

    Args:
        prs: An open Presentation object.
        layout: Layout name string (e.g. "title_and_content", "blank").

    Returns:
        The integer index into prs.slide_layouts.
    """
    normalized = layout.lower().replace(" ", "_").replace("-", "_")

    for idx, sl in enumerate(prs.slide_layouts):
        sl_normalized = sl.name.lower().replace(" ", "_").replace("-", "_")
        if sl_normalized == normalized:
            return idx

    if normalized in _LAYOUT_PRESETS:
        preset_idx = _LAYOUT_PRESETS[normalized]
        if preset_idx < len(prs.slide_layouts):
            return preset_idx

    return 0


def build_pptx(title: str = "") -> bytes:
    """Create a new presentation with an optional title slide.

    Args:
        title: If non-empty, creates a Title Slide layout with this text.
            Otherwise, creates a single blank slide.

    Returns:
        The .pptx file content as bytes.
    """
    prs = NewPresentation()

    if title:
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        if slide.shapes.title:
            slide.shapes.title.text = title
    else:
        slide_layout = prs.slide_layouts[6]
        prs.slides.add_slide(slide_layout)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


@_invalid_presentation_errors()
def extract_slides(
    pptx_bytes: bytes,
    include_notes: bool = False,
) -> dict:
    """Extract structured text data from the slides in a presentation, up to the text limit.

    Args:
        pptx_bytes: Raw .pptx file bytes.
        include_notes: Whether to include speaker notes.

    Returns:
        A dict containing:
        - slides: list of dicts, one per slide, each containing
          number, title, texts (list of str), and notes (str).
        - truncated: whether text was cut at the text limit.
          Slides after the cut are omitted.

    Raises:
        OfficePackageError: If the package is not valid or is over the size limits.
    """
    prs = _open_presentation(pptx_bytes)
    budget = TextBudget()
    slides: list[dict] = []

    for i, slide in enumerate(prs.slides):
        if budget.exhausted:
            break
        slide_data: dict = {
            "number": i + 1,
            "title": "",
            "texts": [],
            "notes": "",
        }

        title = ""
        title_shape = slide.shapes.title
        if title_shape and title_shape.has_text_frame:
            title = title_shape.text_frame.text.strip()
            slide_data["title"] = budget.take(title)

        for shape in slide.shapes:
            if budget.exhausted:
                break
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text and text != title and (kept := budget.take(text)):
                    slide_data["texts"].append(kept)

        if include_notes and slide.has_notes_slide and not budget.exhausted:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()
            if notes_text:
                slide_data["notes"] = budget.take(notes_text)

        slides.append(slide_data)

    return {"slides": slides, "truncated": budget.exhausted}


@_invalid_presentation_errors()
def add_slide(
    pptx_bytes: bytes,
    layout: str,
    title: str,
    content: str,
) -> tuple[bytes, int]:
    """Add a slide to an existing presentation.

    Args:
        pptx_bytes: Raw .pptx file bytes.
        layout: Layout name (e.g. "blank", "title_and_content").
        title: Title text for the new slide (if layout supports it).
        content: Body text for the new slide (if layout supports it).

    Returns:
        A tuple of (updated .pptx bytes, total slide count after insertion).

    Raises:
        OfficePackageError: If the package is not valid or is over the size limits.
    """
    prs = _open_presentation(pptx_bytes)

    layout_idx = resolve_layout_index(prs, layout)
    slide_layout = prs.slide_layouts[layout_idx]
    slide = prs.slides.add_slide(slide_layout)

    # Placeholder idx 0 = title, idx 1 = body in the standard template.
    # A more robust approach would use ph.placeholder_format.type
    # (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.BODY) which is template-independent,
    # but not all custom templates set placeholder types correctly.
    # Using numeric indices for now as it works reliably with standard layouts.
    for ph in slide.placeholders:
        idx = ph.placeholder_format.idx
        if idx == 0 and title:
            ph.text = title
        elif idx == 1 and content:
            ph.text = content

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue(), len(prs.slides)


@_invalid_presentation_errors()
def update_text(
    pptx_bytes: bytes,
    slide_number: int,
    text: str,
    shape_index: int,
) -> tuple[bytes, str, str | None]:
    """Update text in a shape on the given slide.

    If the target slide has no text shapes, a new text box is created.

    Args:
        pptx_bytes: Raw .pptx file bytes.
        slide_number: 1-based slide number.
        text: New text content.
        shape_index: 0-based index among text-bearing shapes on the slide.

    Returns:
        A tuple of (updated bytes, shape name, error string or None).

    Raises:
        OfficePackageError: If the package is not valid or is over the size limits.
    """
    prs = _open_presentation(pptx_bytes)

    if slide_number < 1 or slide_number > len(prs.slides):
        return (
            pptx_bytes,
            "",
            f"Slide number {slide_number} is out of range (1-{len(prs.slides)})",
        )

    slide = prs.slides[slide_number - 1]
    text_shapes = [s for s in slide.shapes if s.has_text_frame]

    if not text_shapes:
        txbox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1.5))
        txbox.text_frame.text = text
        shape_name = txbox.name
    elif shape_index < 0 or shape_index >= len(text_shapes):
        return (
            pptx_bytes,
            "",
            (
                f"Shape index {shape_index} is out of range "
                f"(0-{len(text_shapes) - 1}). "
                f"Slide {slide_number} has {len(text_shapes)} text shape(s)."
            ),
        )
    else:
        shape = text_shapes[shape_index]
        shape.text_frame.text = text
        shape_name = shape.name

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue(), shape_name, None
