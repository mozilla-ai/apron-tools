"""Shared string utilities for provider tool implementations."""

from __future__ import annotations


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
