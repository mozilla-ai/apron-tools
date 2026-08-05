"""Tests for the shared string utility helpers."""

import pytest

from apron_tools._utils import parse_csv_ids, quote_path_segment


class TestParseCsvIds:
    def test_single_id(self):
        assert parse_csv_ids("abc123") == ["abc123"]

    def test_multiple_ids(self):
        assert parse_csv_ids("abc123,def456,ghi789") == ["abc123", "def456", "ghi789"]

    def test_strips_whitespace(self):
        assert parse_csv_ids(" abc123 , def456 , ghi789 ") == [
            "abc123",
            "def456",
            "ghi789",
        ]

    def test_empty_string(self):
        assert parse_csv_ids("") == []

    def test_whitespace_only(self):
        assert parse_csv_ids("   ") == []

    def test_whitespace_and_commas(self):
        assert parse_csv_ids(" , , ") == []

    def test_trailing_comma(self):
        assert parse_csv_ids("abc123,") == ["abc123"]

    def test_leading_comma(self):
        assert parse_csv_ids(",abc123") == ["abc123"]

    def test_double_comma(self):
        assert parse_csv_ids("abc123,,def456") == ["abc123", "def456"]

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("STARRED", ["STARRED"]),
            ("Label_123,STARRED,UNREAD", ["Label_123", "STARRED", "UNREAD"]),
            ("123,456,789", ["123", "456", "789"]),
        ],
    )
    def test_various_formats(self, value: str, expected: list[str]):
        assert parse_csv_ids(value) == expected


class TestQuotePathSegment:
    def test_passes_through_unreserved_characters(self) -> None:
        assert quote_path_segment("msg-001_abc.XYZ~") == "msg-001_abc.XYZ~"

    def test_encodes_slash(self) -> None:
        assert quote_path_segment("a/b") == "a%2Fb"

    def test_encodes_query_and_fragment_delimiters(self) -> None:
        assert quote_path_segment("id?x=1#frag") == "id%3Fx%3D1%23frag"

    def test_encodes_whitespace(self) -> None:
        assert quote_path_segment("a b") == "a%20b"

    def test_encodes_percent(self) -> None:
        assert quote_path_segment("100%2F") == "100%252F"

    def test_empty_string(self) -> None:
        assert quote_path_segment("") == ""
