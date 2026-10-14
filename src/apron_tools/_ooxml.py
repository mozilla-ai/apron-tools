"""Limits for reading untrusted Office Open XML (OOXML) packages.

An OOXML file (``.docx``, ``.pptx``, ``.xlsx``) is a zip archive.
A small archive can unpack to a very large size.
Packages are checked for part count, declared unpacked size, compression method, and encryption before they are parsed.
Text extracted from a package is also capped, so a very long document gives a truncated read.
Text to be written into a package can be checked for characters that XML cannot hold.
"""

from __future__ import annotations

import io
import re
import zipfile

_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_ENCRYPTED_FLAG = 0x1
_MAX_PARTS = 10_000
_MAX_TEXT_CHARS = 100_000
_MAX_UNPACKED_BYTES = 200 * 1024 * 1024
_NON_XML_CHAR = re.compile("[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")
_SUPPORTED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})


class OfficePackageError(ValueError):
    """An Office document cannot be opened within the package limits."""


class TextBudget:
    """Track how much extracted text one read may still return."""

    def __init__(self) -> None:
        """Start a budget at the text limit."""
        self.remaining = _MAX_TEXT_CHARS
        self.exhausted = False

    def take(self, text: str) -> str:
        """Return the part of the text that fits in the budget, and mark the budget exhausted if any text is cut.

        Args:
            text: Extracted text to add to the read.

        Returns:
            The text, cut at the remaining budget.
        """
        if len(text) > self.remaining:
            text = text[: self.remaining]
            self.exhausted = True
        self.remaining -= len(text)
        return text


def check_package(data: bytes) -> None:
    """Check that an OOXML package is within the package limits.

    The checks cover the part count, the declared unpacked size, the compression method, and encryption.
    They do not bound the memory that a parser uses for the XML in the parts.

    NOTE: The unpacked size limit uses the sizes that the archive declares.
    This is sound because ``zipfile`` stops reading a part at its declared size,
    and only stored and deflated parts are accepted.

    Args:
        data: Raw package bytes.

    Raises:
        OfficePackageError: If the data is not a valid package, has too many parts,
            uses an unsupported compression method, is encrypted, or is too large when unpacked.
    """
    # NOTE: Each central directory entry starts with this signature, so the count bounds the parts before parsing.
    if data.count(_CENTRAL_DIRECTORY_SIGNATURE) > _MAX_PARTS:
        raise OfficePackageError(f"The document has more than {_MAX_PARTS:,} parts.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            parts = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise OfficePackageError("The file is not a valid Office document.") from exc

    if any(part.flag_bits & _ENCRYPTED_FLAG for part in parts):
        raise OfficePackageError("The document is encrypted.")
    if any(part.compress_type not in _SUPPORTED_COMPRESSION for part in parts):
        raise OfficePackageError("The document uses an unsupported compression method.")
    if sum(part.file_size for part in parts) > _MAX_UNPACKED_BYTES:
        limit_mb = _MAX_UNPACKED_BYTES // (1024 * 1024)
        raise OfficePackageError(f"The document is larger than the {limit_mb} MB limit when unpacked.")


def validate_xml_text(text: str) -> str:
    """Check that text holds only characters that an XML document can store.

    Args:
        text: Text to store in a document.

    Returns:
        The text, unchanged.

    Raises:
        ValueError: If the text holds a character that XML cannot store.
    """
    if match := _NON_XML_CHAR.search(text):
        raise ValueError(f"The text contains U+{ord(match.group()):04X}, which a document cannot hold.")
    return text
