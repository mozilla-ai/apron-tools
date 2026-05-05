"""Pydantic models for Slack API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import Base64Bytes, BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreWorkspaceParams(BaseModel):
    """Parameters for exploring the Slack workspace."""


class ListMyConversationsParams(BaseModel):
    """Parameters for listing the caller's Slack conversations."""

    types: str = "im,mpim,public_channel,private_channel"
    exclude_archived: bool = True
    limit: int = Field(default=200, gt=0, le=1000)


class SendChannelMessageParams(BaseModel):
    """Parameters for sending a message to a Slack channel."""

    channel_id: str
    message: str
    thread_ts: str | None = None


class SendUserMessageParams(BaseModel):
    """Parameters for sending a direct message to a Slack user."""

    user_id: str
    message: str


class ReadChannelMessagesParams(BaseModel):
    """Parameters for reading messages from a Slack channel."""

    channel_id: str
    limit: int = 20
    oldest: str | None = None
    latest: str | None = None


class GetChannelInfoParams(BaseModel):
    """Parameters for getting information about a Slack channel."""

    channel_id: str


class ReadThreadParams(BaseModel):
    """Parameters for reading replies in a Slack thread."""

    channel_id: str
    thread_ts: str
    oldest: str | None = None
    latest: str | None = None


class JoinChannelParams(BaseModel):
    """Parameters for joining a Slack channel."""

    channel_id: str


class EditMessageParams(BaseModel):
    """Parameters for editing a previously sent Slack message."""

    channel_id: str
    message_ts: str
    new_text: str


class GetPermalinkParams(BaseModel):
    """Parameters for getting a permanent URL for a Slack message."""

    channel_id: str
    message_ts: str


class GetFileInfoParams(BaseModel):
    """Parameters for getting metadata about a Slack file."""

    file_id: str


class DownloadFileParams(BaseModel):
    """Parameters for downloading a file from Slack."""

    url: str
    max_size_mb: int = 10


class SaveFileForUploadParams(BaseModel):
    """Parameters for saving a Slack file for cross-tool upload.

    The URL should be a ``url_private_download`` value from
    ``slack_get_file_info``. The file is downloaded with the caller's
    Slack token and returned as raw bytes with metadata, ready to be
    passed to another tool's ``FileInput``.
    """

    url: str
    max_size_mb: int = Field(default=10, gt=0)


class GetReactionsParams(BaseModel):
    """Parameters for getting reactions on a Slack message or file."""

    channel_id: str | None = None
    timestamp: str | None = None
    file_id: str | None = None
    file_comment_id: str | None = None
    full: bool = False


class AddReactionsParams(BaseModel):
    """Parameters for adding the same reaction to one or more Slack messages.

    ``timestamps`` accepts a comma-separated list of message timestamps to
    support bulk operations.
    """

    channel_id: str
    timestamps: str
    reaction_name: str


class SearchMessagesParams(BaseModel):
    """Parameters for searching Slack messages the caller has access to."""

    query: str = Field(min_length=1)
    count: int = Field(default=20, gt=0, le=100)
    sort: str = "timestamp"
    sort_dir: str = "desc"


class ListSavedItemsParams(BaseModel):
    """Parameters for listing the caller's saved (bookmarked) Slack items.

    ``limit`` is hard-capped at 999 to match Slack's documented constraint
    of "limit value under 1000" on the underlying ``stars.list`` endpoint.
    Slack also recommends no more than 200 per call; that is left as caller
    guidance rather than enforced here.
    """

    limit: int = Field(default=100, gt=0, lt=1000)


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class SlackChannel(BaseModel):
    """A Slack channel summary."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    is_private: bool = False
    num_members: int = 0


class SlackConversation(BaseModel):
    """A Slack conversation summary (channels, DMs, and group DMs)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    is_im: bool = False
    is_mpim: bool = False
    is_private: bool = False
    user: str | None = None
    updated: int = 0


class SlackUser(BaseModel):
    """A Slack user summary."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    real_name: str | None = None
    deleted: bool = False


class SlackMessage(BaseModel):
    """A single Slack message."""

    model_config = ConfigDict(extra="ignore")

    user: str | None = None
    text: str = ""
    ts: str = ""
    reply_count: int | None = None
    files: list[dict[str, Any]] | None = None


class SlackReaction(BaseModel):
    """A single reaction on a Slack item."""

    model_config = ConfigDict(extra="ignore")

    name: str
    count: int = 0
    users: list[str] = []


class SlackSearchHit(BaseModel):
    """A single message match returned by ``search.messages``.

    For human-authored messages ``user`` carries the user ID and
    ``username`` carries the display name. For bot, app, or integration
    posts ``user`` is typically empty and only ``username`` is set.
    """

    model_config = ConfigDict(extra="ignore")

    channel_id: str = ""
    channel_name: str = ""
    is_im: bool = False
    user: str = ""
    username: str = ""
    text: str = ""
    ts: str = ""
    permalink: str = ""


class SlackSavedItem(BaseModel):
    """A single item the caller has saved in Slack.

    Flattens ``stars.list``'s per-type item shapes (``message``, ``file``,
    ``file_comment``, ``channel``, ``im``, ``group``) into a common surface
    so callers do not need to branch on item type. ``text`` and
    ``message_ts`` are populated for ``message``-typed items; for
    channel/file types they remain empty and only ``type`` and
    ``channel_id`` carry meaning.

    A per-item identifier suitable for un-saving is intentionally omitted
    because no tool mutates saved state today — worth re-introducing as a
    typed field if a "remove saved item" tool is added.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = ""
    channel_id: str = ""
    message_ts: str = ""
    text: str = ""


class SlackFile(BaseModel):
    """Metadata for a Slack file."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""
    title: str = ""
    filetype: str = ""
    pretty_type: str = ""
    mimetype: str = ""
    size: int = 0
    created: int = 0
    user: str = ""
    url_private_download: str = ""


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreWorkspaceResult(ToolResult):
    """Result of exploring the Slack workspace."""

    model_config = ConfigDict(extra="ignore")

    workspace_name: str = ""
    channels: list[SlackChannel] = []
    users: list[SlackUser] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the workspace."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"# {self.workspace_name}"]
        lines.append("## Channels")
        if self.channels:
            for ch in self.channels:
                lines.append(f"- {ch.name} ({ch.id})")
        else:
            lines.append("- (no channels found)")
        lines.append("## Users")
        active = [u for u in self.users if not u.deleted]
        if active:
            for u in active:
                display = u.real_name or u.name
                lines.append(f"- {display} ({u.id})")
        else:
            lines.append("- (no users found)")
        return "\n".join(lines)


class ListMyConversationsResult(ToolResult):
    """Result of listing the caller's Slack conversations."""

    model_config = ConfigDict(extra="ignore")

    conversations: list[SlackConversation] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of conversations."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.conversations:
            return "No conversations found."

        lines: list[str] = []
        for c in self.conversations:
            if c.is_im:
                label = f"DM ({c.user or 'unknown'})"
            elif c.is_mpim:
                label = f"Group DM {c.name}" if c.name else "Group DM"
            elif c.name:
                label = f"#{c.name}"
            else:
                label = c.id
            lines.append(f"- {label} ({c.id})")
        return "\n".join(lines)


class SendChannelMessageResult(ToolResult):
    """Result of sending a message to a Slack channel."""

    model_config = ConfigDict(extra="ignore")

    channel: str = ""
    ts: str = ""
    message: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when the API response indicates ok."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent message."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Message sent to channel {self.channel} at {self.ts}."


class SendUserMessageResult(ToolResult):
    """Result of sending a direct message to a Slack user."""

    model_config = ConfigDict(extra="ignore")

    channel: str = ""
    ts: str = ""
    message: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when the API response indicates ok."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent DM."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Direct message sent to channel {self.channel} at {self.ts}."


class ReadChannelMessagesResult(ToolResult):
    """Result of reading messages from a Slack channel."""

    model_config = ConfigDict(extra="ignore")

    messages: list[SlackMessage] = []
    has_more: bool = False
    user_map: dict[str, str] = {}

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of channel messages."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.messages:
            return "No messages found."
        lines: list[str] = []
        for msg in self.messages:
            user_name = self.user_map.get(msg.user or "", msg.user or "Unknown")
            thread_info = f" [{msg.reply_count} replies]" if msg.reply_count else ""
            file_info = ""
            if msg.files:
                parts = [f'{f.get("id", "")} "{f.get("name", "")}"' for f in msg.files]
                file_info = f" [Files: {', '.join(parts)}]"
            lines.append(f"- [ts:{msg.ts}]{thread_info} {user_name}: {msg.text}{file_info}")
        return "\n".join(lines)


class GetChannelInfoResult(ToolResult):
    """Result of getting information about a Slack channel."""

    model_config = ConfigDict(extra="ignore")

    channel: SlackChannel | None = None
    topic: str = ""
    purpose: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of channel info."""
        if not self.success:
            return f"Error: {self.error}"
        if self.channel is None:
            return "No channel info available."
        lines = [
            f"Name: {self.channel.name}",
            f"Type: {'Private' if self.channel.is_private else 'Public'}",
            f"Members: {self.channel.num_members}",
        ]
        if self.topic:
            lines.append(f"Topic: {self.topic}")
        if self.purpose:
            lines.append(f"Purpose: {self.purpose}")
        return "\n".join(lines)


class ReadThreadResult(ToolResult):
    """Result of reading replies in a Slack thread."""

    model_config = ConfigDict(extra="ignore")

    messages: list[SlackMessage] = []
    user_map: dict[str, str] = {}

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of thread messages."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.messages:
            return "No messages found in thread."
        lines: list[str] = []
        for i, msg in enumerate(self.messages):
            user_name = self.user_map.get(msg.user or "", msg.user or "Unknown")
            prefix = "[Parent]" if i == 0 else "[Reply]"
            file_info = ""
            if msg.files:
                parts = [f'{f.get("id", "")} "{f.get("name", "")}"' for f in msg.files]
                file_info = f" [Files: {', '.join(parts)}]"
            lines.append(f"- {prefix} {user_name}: {msg.text}{file_info}")
        return "\n".join(lines)


class JoinChannelResult(ToolResult):
    """Result of joining a Slack channel."""

    model_config = ConfigDict(extra="ignore")

    channel_id: str = ""
    channel_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of joining the channel."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Successfully joined channel #{self.channel_name} ({self.channel_id})."


class EditMessageResult(ToolResult):
    """Result of editing a Slack message."""

    model_config = ConfigDict(extra="ignore")

    channel: str = ""
    ts: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when the API response indicates ok."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the edited message."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Message edited successfully in channel {self.channel} at {self.ts}."


class GetPermalinkResult(ToolResult):
    """Result of getting a permalink for a Slack message."""

    model_config = ConfigDict(extra="ignore")

    permalink: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when the API response indicates ok."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return the permalink URL or an error message."""
        if not self.success:
            return f"Error: {self.error}"
        return self.permalink


class GetFileInfoResult(ToolResult):
    """Result of getting metadata for a Slack file."""

    model_config = ConfigDict(extra="ignore")

    file: SlackFile | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when the API response indicates ok."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = data.get("ok", False)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the file metadata."""
        if not self.success:
            return f"Error: {self.error}"
        if self.file is None:
            return "No file info available."
        f = self.file
        lines = [
            f"ID: {f.id}",
            f"Name: {f.name}",
            f"Title: {f.title}",
            f"Type: {f.pretty_type or f.filetype}",
            f"MIME type: {f.mimetype}",
            f"Size: {f.size} bytes",
            f"Created: {f.created}",
            f"Uploaded by: {f.user}",
            f"Download URL: {f.url_private_download}",
        ]
        return "\n".join(lines)


class DownloadFileResult(ToolResult):
    """Result of downloading a Slack file."""

    model_config = ConfigDict(extra="ignore")

    content: str = ""
    mime_type: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return the downloaded file content or an error message."""
        if not self.success:
            return f"Error: {self.error}"
        if self.mime_type.startswith("text/"):
            return self.content
        return f"Content-Type: {self.mime_type}\nEncoding: base64\n\n{self.content}"


class SaveFileForUploadResult(ToolResult):
    """Result of saving a Slack file for cross-tool upload.

    Contains the raw file bytes (base64-encoded for JSON transport),
    filename, and MIME type — the fields needed to construct a
    ``FileFromBytes`` for another tool's ``FileInput``.
    """

    model_config = ConfigDict(extra="ignore")

    data: Base64Bytes = b""
    filename: str = ""
    mime_type: str = ""
    size: int = 0

    def __str__(self) -> str:
        """Return an LLM-readable summary of the saved file."""
        if not self.success:
            return f"Error: {self.error}"
        size_kb = self.size / 1024
        return f"File saved for upload.\nFilename: {self.filename}\nType: {self.mime_type}\nSize: {size_kb:.1f} KB"


class GetReactionsResult(ToolResult):
    """Result of getting reactions for a Slack item."""

    model_config = ConfigDict(extra="ignore")

    reactions: list[SlackReaction] = []
    item_type: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of reactions."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.reactions:
            return "No reactions found."
        lines: list[str] = []
        for r in self.reactions:
            if r.users:
                users_str = ", ".join(r.users)
                lines.append(f":{r.name}: {r.count} ({users_str})")
            else:
                lines.append(f":{r.name}: {r.count}")
        return "\n".join(lines)


class AddReactionItem(BaseModel):
    """Per-message outcome of a bulk Slack add-reactions call."""

    model_config = ConfigDict(extra="ignore")

    timestamp: str
    success: bool = True
    error: str | None = None


class AddReactionsResult(ToolResult):
    """Result of adding a reaction to one or more Slack messages."""

    model_config = ConfigDict(extra="ignore")

    reaction_name: str = ""
    channel_id: str = ""
    items: list[AddReactionItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk reaction add."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No messages processed."
        lines: list[str] = []
        for item in self.items:
            if item.success:
                lines.append(
                    f"- Reaction :{self.reaction_name}: added to message {item.timestamp} in channel {self.channel_id}."
                )
            else:
                lines.append(f"- {item.timestamp}: Failed: {item.error}")
        return "\n".join(lines)


class SearchMessagesResult(ToolResult):
    """Result of searching Slack messages."""

    model_config = ConfigDict(extra="ignore")

    matches: list[SlackSearchHit] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of search hits."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.matches:
            return "No matches found."
        lines: list[str] = []
        for hit in self.matches:
            label = "DM" if hit.is_im else (f"#{hit.channel_name}" if hit.channel_name else hit.channel_id)
            # Show display name plus user ID when both are present so the LLM
            # gets readable attribution and a stable identifier for follow-up
            # tool calls. Bot/integration posts have no user ID, so the name
            # stands alone.
            who = f"{hit.username} ({hit.user})" if hit.username and hit.user else hit.username or hit.user or "unknown"
            lines.append(f"- [{label}] [ts:{hit.ts}] {who}: {hit.text}")
            if hit.permalink:
                lines.append(f"  {hit.permalink}")
        return "\n".join(lines)


class ListSavedItemsResult(ToolResult):
    """Result of listing the caller's saved Slack items."""

    model_config = ConfigDict(extra="ignore")

    items: list[SlackSavedItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of saved items."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No saved items."
        lines: list[str] = []
        for item in self.items:
            location = item.channel_id or "(unknown)"
            ts_part = f" [ts:{item.message_ts}]" if item.message_ts else ""
            type_part = f"[{item.type}] " if item.type else ""
            lines.append(f"- {type_part}{location}{ts_part}: {item.text}")
        return "\n".join(lines)
