"""Pydantic models for Microsoft Outlook Graph API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListEmailsParams(BaseModel):
    """Parameters for listing emails."""

    query: str = ""
    limit: int = 25


class ReadEmailParams(BaseModel):
    """Parameters for reading a single email."""

    message_id: str


class SendEmailParams(BaseModel):
    """Parameters for sending an email."""

    to: list[str]
    subject: str
    body: str
    cc: list[str] = []
    bcc: list[str] = []


class CreateDraftParams(BaseModel):
    """Parameters for creating a draft email."""

    to: list[str]
    subject: str
    body: str
    cc: list[str] = []
    bcc: list[str] = []


class SendDraftParams(BaseModel):
    """Parameters for sending an existing draft."""

    message_id: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class EmailAddress(BaseModel):
    """An email address with optional display name."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = ""
    address: str = ""


class Recipient(BaseModel):
    """A mail recipient containing an email address."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email_address: EmailAddress = Field(default_factory=EmailAddress, alias="emailAddress")


class EmailBody(BaseModel):
    """The body of an email message."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    content_type: str = Field(default="text", alias="contentType")
    content: str = ""


class EmailMessage(BaseModel):
    """An email message from the Graph API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    subject: str = ""
    body_preview: str = Field(default="", alias="bodyPreview")
    body: EmailBody | None = None
    importance: str = "normal"
    is_read: bool = Field(default=False, alias="isRead")
    is_draft: bool = Field(default=False, alias="isDraft")
    has_attachments: bool = Field(default=False, alias="hasAttachments")
    received_date_time: str | None = Field(default=None, alias="receivedDateTime")
    sent_date_time: str | None = Field(default=None, alias="sentDateTime")
    from_: Recipient | None = Field(default=None, alias="from")
    to_recipients: list[Recipient] = Field(default_factory=list, alias="toRecipients")
    cc_recipients: list[Recipient] = Field(default_factory=list, alias="ccRecipients")
    reply_to: list[Recipient] = Field(default_factory=list, alias="replyTo")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListEmailsResult(ToolResult):
    """Result of listing emails."""

    model_config = ConfigDict(extra="ignore")

    emails: list[EmailMessage] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of listed emails."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.emails:
            return "No emails found."
        lines = [f"Found {len(self.emails)} email(s):"]
        for email in self.emails:
            sender = ""
            if email.from_:
                addr = email.from_.email_address
                sender = f"{addr.name} <{addr.address}>" if addr.name else addr.address
            read_status = "" if email.is_read else " [UNREAD]"
            lines.append(f"  - [{email.id}] {email.subject}{read_status} from {sender}")
        return "\n".join(lines)


class ReadEmailResult(ToolResult):
    """Result of reading a single email."""

    model_config = ConfigDict(extra="ignore")

    email: EmailMessage | None = None

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
        if not self.email:
            return "No email found."
        e = self.email
        sender = ""
        if e.from_:
            addr = e.from_.email_address
            sender = f"{addr.name} <{addr.address}>" if addr.name else addr.address
        to_addrs = ", ".join(r.email_address.address for r in e.to_recipients)
        lines = [
            f"Subject: {e.subject}",
            f"From: {sender}",
            f"To: {to_addrs}",
            f"Date: {e.received_date_time or 'Unknown'}",
        ]
        if e.body:
            content = e.body.content
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"Body: {content}")
        return "\n".join(lines)


class SendEmailResult(ToolResult):
    """Result of sending an email."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent email."""
        if not self.success:
            return f"Error: {self.error}"
        return "Email sent successfully."


class CreateDraftResult(ToolResult):
    """Result of creating a draft email."""

    model_config = ConfigDict(extra="ignore")

    draft: EmailMessage | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the created draft."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.draft:
            return "Draft created but no details available."
        return f"Draft created successfully. Draft ID: {self.draft.id}"


class SendDraftResult(ToolResult):
    """Result of sending a draft email."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the sent draft."""
        if not self.success:
            return f"Error: {self.error}"
        return "Draft sent successfully."
