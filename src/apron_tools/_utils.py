"""Shared string utilities for provider tool implementations."""

from __future__ import annotations

from urllib.parse import quote


def parse_csv_ids(value: str) -> list[str]:
    """Split a comma-separated string into a list of non-empty, stripped tokens.

    Args:
        value: A comma-separated string (e.g. ``"abc,def , ghi"``).

    Returns:
        A list of stripped, non-empty strings.
        Returns an empty list when *value* is empty or contains only whitespace.

    Examples:
        >>> parse_csv_ids("abc123,def456")
        ['abc123', 'def456']
        >>> parse_csv_ids("abc123, def456 , ghi789")
        ['abc123', 'def456', 'ghi789']
        >>> parse_csv_ids("")
        []
        >>> parse_csv_ids("  ,  ")
        []
    """
    return [item.strip() for item in value.split(",") if item.strip()]


def quote_path_segment(value: str) -> str:
    """Percent-encode a value for use as a single URL path segment.

    All characters reserved in URLs, including "/", are encoded
    so the value cannot alter the path structure, query, or fragment of the surrounding URL.

    Args:
        value: The raw value to embed in a URL path.

    Returns:
        The percent-encoded path segment.

    Examples:
        >>> quote_path_segment("msg-001")
        'msg-001'
        >>> quote_path_segment("a/b c")
        'a%2Fb%20c'
    """
    return quote(value, safe="")
