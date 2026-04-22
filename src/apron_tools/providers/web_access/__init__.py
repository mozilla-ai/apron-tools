"""web_access provider.

Tabstack-backed web research and structured extraction.

API docs: https://github.com/Mozilla-Ocho/tabstack-python/blob/main/api.md
"""

from .tools import web_access_extract_json, web_access_research

__all__ = [
    "web_access_extract_json",
    "web_access_research",
]
