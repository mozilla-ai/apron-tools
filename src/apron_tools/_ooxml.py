"""Checks for untrusted Office Open XML (OOXML) packages before they are parsed.

An OOXML file (``.docx``, ``.pptx``, ``.xlsx``) is a zip archive.
A small archive can unpack to a very large size.
Packages are checked for part count, declared unpacked size, compression method, and encryption before they are parsed.
"""

from __future__ import annotations

import io
import zipfile

_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_ENCRYPTED_FLAG = 0x1
_MAX_PARTS = 10_000
_MAX_UNPACKED_BYTES = 200 * 1024 * 1024
_SUPPORTED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})


class OfficePackageError(ValueError):
    """An Office document cannot be opened within the package limits."""


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
