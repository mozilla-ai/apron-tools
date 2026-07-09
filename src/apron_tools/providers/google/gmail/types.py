"""Pydantic models for Gmail API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import Base64Bytes, BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListEmailsParams(BaseModel):
    """Parameters for listing Gmail messages."""

    query: str = ""
    max_results: int = Field(default=25, ge=1, le=100)


class ReadEmailParams(BaseModel):
    """Parameters for reading a single Gmail message."""

    message_id: str


class GetAttachmentParams(BaseModel):
    """Parameters for downloading a Gmail message attachment.

    ``attachment_id`` is the ``body.attachmentId`` found on a message's
    MIME parts (available from a full message read). Gmail's attachment
    endpoint returns only the raw bytes and size — never the filename or
    MIME type — so pass ``filename`` and ``mime_type`` when they are known
    from the part headers to enrich the result for a downstream upload.
    """

    message_id: str
    attachment_id: str
    filename: str | None = None
    mime_type: str | None = None


class SendEmailParams(BaseModel):
    """Parameters for sending an email via Gmail."""

    to: str
    subject: str
    body: str
    cc: str | None = None
    bcc: str | None = None


class CreateDraftParams(BaseModel):
    """Parameters for creating a Gmail draft."""

    to: str
    subject: str
    body: str
    cc: str | None = None
    bcc: str | None = None


class EditDraftParams(BaseModel):
    """Parameters for editing an existing Gmail draft."""

    draft_id: str
    to: str | None = None
    subject: str | None = None
    body: str | None = None
    cc: str | None = None
    bcc: str | None = None


class ReplyToEmailParams(BaseModel):
    """Parameters for replying to an email in the same thread."""

    message_id: str
    body: str
    cc: str | None = None
    bcc: str | None = None


class GetThreadRepliesParams(BaseModel):
    """Parameters for retrieving all messages in a thread."""

    thread_id: str


class ListLabelsParams(BaseModel):
    """Parameters for listing Gmail labels."""


class AddLabelsToEmailsParams(BaseModel):
    """Parameters for adding labels to one or more messages.

    Both fields accept comma-separated IDs to support bulk operations.
    """

    message_ids: str
    label_ids: str


class RemoveLabelsFromEmailsParams(BaseModel):
    """Parameters for removing labels from one or more messages.

    Both fields accept comma-separated IDs to support bulk operations.
    """

    message_ids: str
    label_ids: str


class CreateLabelParams(BaseModel):
    """Parameters for creating a new user-defined Gmail label."""

    name: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class EmailSummary(BaseModel):
    """Summary of a single email returned by list_emails."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    thread_id: str = Field(default="", alias="threadId")
    subject: str = ""
    from_address: str = ""
    to_address: str = ""
    date: str = ""
    snippet: str = ""


class ThreadMessage(BaseModel):
    """A message within a thread summary."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    from_address: str = ""
    to_address: str = ""
    date: str = ""
    snippet: str = ""


class GmailLabel(BaseModel):
    """A Gmail label entry."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""
    type: str = ""


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListEmailsResult(ToolResult):
    """Result of listing Gmail messages."""

    model_config = ConfigDict(extra="ignore")

    emails: list[EmailSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the emails."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.emails:
            return "No emails found."
        lines = [f"Found {len(self.emails)} email(s):"]
        for e in self.emails:
            lines.append(f"  - [{e.id}] {e.subject} (from: {e.from_address})")
        return "\n".join(lines)


class ReadEmailResult(ToolResult):
    """Result of reading a single Gmail message."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    thread_id: str = ""
    subject: str = ""
    from_address: str = ""
    to_address: str = ""
    cc: str = ""
    date: str = ""
    body: str = ""
    label_ids: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the email."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [
            f"Subject: {self.subject}",
            f"From: {self.from_address}",
            f"To: {self.to_address}",
        ]
        if self.cc:
            lines.append(f"Cc: {self.cc}")
        lines.append(f"Date: {self.date}")
        lines.append("")
        lines.append(self.body)
        return "\n".join(lines)


class GetAttachmentResult(ToolResult):
    """Result of downloading a Gmail message attachment.

    Carries the raw attachment bytes (base64-encoded for JSON transport),
    filename, MIME type, and size — the fields needed to construct a
    ``FileFromBytes`` for another tool's ``FileInput``.
    """

    model_config = ConfigDict(extra="ignore")

    data: Base64Bytes = b""
    filename: str = ""
    mime_type: str = ""
    size: int = 0

    def __str__(self) -> str:
        """Return an LLM-readable summary of the downloaded attachment."""
        if not self.success:
            return f"Error: {self.error}"
        size_kb = self.size / 1024
        return f"Attachment downloaded.\nFilename: {self.filename}\nType: {self.mime_type}\nSize: {size_kb:.1f} KB"


class SendEmailResult(ToolResult):
    """Result of sending an email."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    thread_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the sent message."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Email sent. Message ID: {self.id}"


class CreateDraftResult(ToolResult):
    """Result of creating a Gmail draft."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    message_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            data["message_id"] = data.get("message", {}).get("id", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created draft."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Draft created. Draft ID: {self.id}, Message ID: {self.message_id}"


class EditDraftResult(ToolResult):
    """Result of editing a Gmail draft."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    message_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            data["message_id"] = data.get("message", {}).get("id", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the edited draft."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Draft updated. Draft ID: {self.id}, Message ID: {self.message_id}"


class ReplyToEmailResult(ToolResult):
    """Result of replying to an email."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    thread_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the reply."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Reply sent. Message ID: {self.id}, Thread ID: {self.thread_id}"


class GetThreadRepliesResult(ToolResult):
    """Result of getting all messages in a thread."""

    model_config = ConfigDict(extra="ignore")

    thread_id: str = ""
    subject: str = ""
    messages: list[ThreadMessage] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the thread."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.messages:
            return f"Thread {self.thread_id}: no messages."
        lines = [
            f"Thread {self.thread_id}: {self.subject}",
            f"{len(self.messages)} message(s):",
        ]
        for m in self.messages:
            lines.append(f"  - [{m.id}] {m.from_address} ({m.date}): {m.snippet}")
        return "\n".join(lines)


class ListLabelsResult(ToolResult):
    """Result of listing Gmail labels."""

    model_config = ConfigDict(extra="ignore")

    labels: list[GmailLabel] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the labels."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.labels:
            return "No labels found."
        lines = [f"Found {len(self.labels)} label(s):"]
        for lbl in self.labels:
            lines.append(f"  - {lbl.name} (id={lbl.id}, type={lbl.type})")
        return "\n".join(lines)


class ModifyLabelsItem(BaseModel):
    """Per-message outcome of a bulk label modification."""

    model_config = ConfigDict(extra="ignore")

    message_id: str
    label_ids: list[str] = []
    success: bool = True
    error: str | None = None


class ModifyLabelsResult(ToolResult):
    """Result of adding or removing labels across one or more messages."""

    model_config = ConfigDict(extra="ignore")

    items: list[ModifyLabelsItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk label modification."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No messages processed."
        lines: list[str] = []
        for item in self.items:
            if item.success:
                label_str = ", ".join(item.label_ids)
                lines.append(f"- {item.message_id}: Labels updated. Label IDs: {label_str}")
            else:
                lines.append(f"- {item.message_id}: Failed: {item.error}")
        return "\n".join(lines)


class CreateLabelResult(ToolResult):
    """Result of creating a new Gmail label."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""
    type: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created label."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Label created. Name: {self.name}, ID: {self.id}"
