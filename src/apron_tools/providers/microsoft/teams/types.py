"""Pydantic models for Microsoft Teams Graph API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreWorkspaceParams(BaseModel):
    """Parameters for exploring the Teams workspace."""


class GetChannelInfoParams(BaseModel):
    """Parameters for getting channel information."""

    team_id: str
    channel_id: str


class ListChatsParams(BaseModel):
    """Parameters for listing user chats."""

    limit: int = 25


class ReadChatMessagesParams(BaseModel):
    """Parameters for reading chat messages."""

    chat_id: str
    limit: int = 20


class ReadChannelMessagesParams(BaseModel):
    """Parameters for reading channel messages."""

    team_id: str
    channel_id: str
    limit: int = 20


class ReadMessageRepliesParams(BaseModel):
    """Parameters for reading replies to a channel message."""

    team_id: str
    channel_id: str
    message_id: str


class SendChatMessageParams(BaseModel):
    """Parameters for sending a message in a chat."""

    chat_id: str
    message: str


class SendChannelMessageParams(BaseModel):
    """Parameters for sending a message to a channel."""

    team_id: str
    channel_id: str
    message: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TeamInfo(BaseModel):
    """A joined team from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    display_name: str = Field(default="", alias="displayName")
    description: str | None = None
    is_archived: bool = Field(default=False, alias="isArchived")


class ChannelInfo(BaseModel):
    """A channel within a team."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    display_name: str = Field(default="", alias="displayName")
    description: str | None = None
    membership_type: str = Field(default="standard", alias="membershipType")


class MemberInfo(BaseModel):
    """A team member."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    display_name: str = Field(default="", alias="displayName")
    user_id: str = Field(default="", alias="userId")
    email: str = ""
    roles: list[str] = []


class ChatInfo(BaseModel):
    """A chat from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    chat_type: str = Field(default="", alias="chatType")
    topic: str | None = None
    created_date_time: str | None = Field(default=None, alias="createdDateTime")
    last_updated_date_time: str | None = Field(default=None, alias="lastUpdatedDateTime")


class MessageBody(BaseModel):
    """The body of a chat message."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    content_type: str = Field(default="text", alias="contentType")
    content: str = ""


class MessageUser(BaseModel):
    """User information within a message sender."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    display_name: str = Field(default="", alias="displayName")


class MessageFrom(BaseModel):
    """Sender information for a chat message."""

    model_config = ConfigDict(extra="ignore")

    user: MessageUser | None = None


class MessageInfo(BaseModel):
    """A chat or channel message."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    created_date_time: str | None = Field(default=None, alias="createdDateTime")
    message_type: str = Field(default="message", alias="messageType")
    body: MessageBody = MessageBody()
    from_: MessageFrom | None = Field(default=None, alias="from")
    importance: str = "normal"


# ---------------------------------------------------------------------------
# Team workspace nested result models
# ---------------------------------------------------------------------------


class TeamWorkspaceEntry(BaseModel):
    """A team with its channels and members for workspace exploration."""

    team: TeamInfo
    channels: list[ChannelInfo] = []
    members: list[MemberInfo] = []


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreWorkspaceResult(ToolResult):
    """Result of exploring the Teams workspace."""

    model_config = ConfigDict(extra="ignore")

    teams: list[TeamWorkspaceEntry] = []

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
        if not self.teams:
            return "No teams found."
        lines = [f"Found {len(self.teams)} team(s):"]
        for entry in self.teams:
            lines.append(f"  - {entry.team.display_name} (id={entry.team.id})")
            for ch in entry.channels:
                lines.append(f"    - #{ch.display_name} (id={ch.id})")
            for m in entry.members:
                lines.append(f"    - @{m.display_name}")
        return "\n".join(lines)


class GetChannelInfoResult(ToolResult):
    """Result of getting channel information."""

    model_config = ConfigDict(extra="ignore")

    channel: ChannelInfo | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the channel."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.channel:
            return "No channel information."
        ch = self.channel
        parts = [f"Channel: {ch.display_name} (id={ch.id})"]
        if ch.description:
            parts.append(f"Description: {ch.description}")
        parts.append(f"Type: {ch.membership_type}")
        return "\n".join(parts)


class ListChatsResult(ToolResult):
    """Result of listing user chats."""

    model_config = ConfigDict(extra="ignore")

    chats: list[ChatInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the chats."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.chats:
            return "No chats found."
        lines = [f"Found {len(self.chats)} chat(s):"]
        for c in self.chats:
            label = c.topic or c.chat_type
            lines.append(f"  - {label} (id={c.id})")
        return "\n".join(lines)


class ReadChatMessagesResult(ToolResult):
    """Result of reading chat messages."""

    model_config = ConfigDict(extra="ignore")

    messages: list[MessageInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of chat messages."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.messages:
            return "No messages found."
        lines = [f"Found {len(self.messages)} message(s):"]
        for msg in self.messages:
            sender = ""
            if msg.from_ and msg.from_.user:
                sender = msg.from_.user.display_name
            content = msg.body.content
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"  - [{msg.id}] {sender}: {content}")
        return "\n".join(lines)


class ReadChannelMessagesResult(ToolResult):
    """Result of reading channel messages."""

    model_config = ConfigDict(extra="ignore")

    messages: list[MessageInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of channel messages."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.messages:
            return "No messages found."
        lines = [f"Found {len(self.messages)} message(s):"]
        for msg in self.messages:
            sender = ""
            if msg.from_ and msg.from_.user:
                sender = msg.from_.user.display_name
            content = msg.body.content
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"  - [{msg.id}] {sender}: {content}")
        return "\n".join(lines)


class ReadMessageRepliesResult(ToolResult):
    """Result of reading message replies."""

    model_config = ConfigDict(extra="ignore")

    parent: MessageInfo | None = None
    replies: list[MessageInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the message replies."""
        if not self.success:
            return f"Error: {self.error}"
        lines: list[str] = []
        if self.parent:
            sender = ""
            if self.parent.from_ and self.parent.from_.user:
                sender = self.parent.from_.user.display_name
            lines.append(f"Parent [{self.parent.id}] {sender}: {self.parent.body.content}")
        if not self.replies:
            lines.append("No replies found.")
            return "\n".join(lines)
        lines.append(f"Found {len(self.replies)} reply/replies:")
        for msg in self.replies:
            sender = ""
            if msg.from_ and msg.from_.user:
                sender = msg.from_.user.display_name
            content = msg.body.content
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"  - [{msg.id}] {sender}: {content}")
        return "\n".join(lines)


class SendChatMessageResult(ToolResult):
    """Result of sending a chat message."""

    model_config = ConfigDict(extra="ignore")

    message_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent message."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Message sent successfully. Message ID: {self.message_id}"


class SendChannelMessageResult(ToolResult):
    """Result of sending a channel message."""

    model_config = ConfigDict(extra="ignore")

    message_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent message."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Message sent to channel. Message ID: {self.message_id}"
