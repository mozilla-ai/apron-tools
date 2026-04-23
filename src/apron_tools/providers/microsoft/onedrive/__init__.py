"""Microsoft OneDrive provider.

API docs: https://learn.microsoft.com/en-us/graph/api/resources/onedrive

Re-exports shared OneDrive helpers for use by PowerPoint and Word
tools, alongside the public OneDrive tool functions defined in
``tools``.
"""

from apron_tools.providers.microsoft.onedrive._shared import (
    download_file,
    get_file_metadata,
    search_files,
    update_file_content,
    upload_file,
)

__all__ = [
    "download_file",
    "get_file_metadata",
    "search_files",
    "update_file_content",
    "upload_file",
]
