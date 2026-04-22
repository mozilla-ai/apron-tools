"""Tests for the shared string utility helpers."""

import pytest

from apron_tools._utils import parse_csv_ids


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
