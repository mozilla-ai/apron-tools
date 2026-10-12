"""Tests for Office Open XML (OOXML) package checks."""

from __future__ import annotations

import io
import zipfile

import pytest

from apron_tools import _ooxml
from apron_tools._ooxml import OfficePackageError, check_package
from apron_tools.providers.microsoft.powerpoint.presentation import build_pptx
from apron_tools.providers.microsoft.word.document import build_docx

_LIMIT = 1024 * 1024


def _zip(entries: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    """Build a zip archive in memory from part names and their contents."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class TestCheckPackage:
    def test_accepts_word_document(self) -> None:
        check_package(build_docx("Hello"))

    def test_accepts_powerpoint_presentation(self) -> None:
        check_package(build_pptx("Title"))

    def test_rejects_bytes_that_are_not_a_package(self) -> None:
        with pytest.raises(OfficePackageError, match="not a valid Office document"):
            check_package(b"not a zip file")

    def test_rejects_too_many_parts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_PARTS", 3)
        data = _zip({f"part{i}.xml": b"<x/>" for i in range(4)})

        with pytest.raises(OfficePackageError, match="more than 3 parts"):
            check_package(data)

    def test_counts_parts_before_opening_the_archive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_PARTS", 3)

        with pytest.raises(OfficePackageError, match="more than 3 parts"):
            check_package(b"PK\x01\x02" * 4)

    def test_rejects_encrypted_part(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("part.xml", b"<x/>")
            zf.infolist()[0].flag_bits |= 0x1

        with pytest.raises(OfficePackageError, match="encrypted"):
            check_package(buf.getvalue())

    def test_rejects_unpacked_size_over_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_UNPACKED_BYTES", _LIMIT)
        data = _zip({"bomb.xml": b"\0" * (_LIMIT + 1)})

        assert len(data) < _LIMIT // 100
        with pytest.raises(OfficePackageError, match="1 MB limit when unpacked"):
            check_package(data)

    def test_accepts_unpacked_size_at_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_ooxml, "_MAX_UNPACKED_BYTES", _LIMIT)

        check_package(_zip({"a.xml": b"\0" * (_LIMIT // 2), "b.xml": b"\0" * (_LIMIT // 2)}))

    def test_rejects_unsupported_compression(self) -> None:
        data = _zip({"part.xml": b"<x/>"}, compression=zipfile.ZIP_BZIP2)

        with pytest.raises(OfficePackageError, match="unsupported compression"):
            check_package(data)

    def test_zipfile_stops_at_declared_part_size(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("part.xml", b"\0" * 10_000)
            zf.infolist()[0].file_size = 10

        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf, pytest.raises(zipfile.BadZipFile):
            zf.read("part.xml")
