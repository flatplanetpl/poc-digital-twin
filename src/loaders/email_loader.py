"""Loader for email files (EML, MBOX)."""

import email
import mailbox
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class EmailLoader(BaseLoader):
    """Loader for email files in EML and MBOX formats."""

    def __init__(self):
        super().__init__(source_type="email")

    def supported_extensions(self) -> list[str]:
        return [".eml", ".mbox"]

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse email file(s) and yield content with metadata.

        Args:
            file_path: Path to the email file

        Yields:
            Tuple of (content, metadata) for each email
        """
        if file_path.suffix == ".eml":
            yield from self._parse_eml(file_path)
        elif file_path.suffix == ".mbox":
            yield from self._parse_mbox(file_path)

    def _parse_eml(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse a single EML file."""
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f)
            yield self._extract_email_data(msg)

    def _parse_mbox(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse MBOX file containing multiple emails."""
        mbox = mailbox.mbox(str(file_path))
        for msg in mbox:
            yield self._extract_email_data(msg)

    def _extract_email_data(
        self, msg: email.message.Message
    ) -> tuple[str, dict]:
        """Extract content and metadata from email message.

        Args:
            msg: Email message object

        Returns:
            Tuple of (body_text, metadata_dict)
        """
        # Extract headers
        subject = self._decode_header(msg.get("Subject", ""))
        sender = self._decode_header(msg.get("From", ""))
        recipient = self._decode_header(msg.get("To", ""))
        date_str = msg.get("Date", "")

        # Parse date
        try:
            date = parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            date = datetime.now()

        # Extract body
        body = self._extract_body(msg)

        metadata = {
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "date": date.isoformat(),
        }

        # Build content with context
        content_parts = []
        if subject:
            content_parts.append(f"Subject: {subject}")
        if sender:
            content_parts.append(f"From: {sender}")
        if recipient:
            content_parts.append(f"To: {recipient}")
        content_parts.append("")
        content_parts.append(body)

        return "\n".join(content_parts), metadata

    def _decode_header(self, header: str) -> str:
        """Decode email header handling various encodings."""
        if not header:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(
                        part.decode(encoding or "utf-8", errors="replace")
                    )
                except (LookupError, UnicodeDecodeError):
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(part)

        return " ".join(decoded_parts)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract text body from email message."""
        body_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            body_parts.append(
                                payload.decode(charset, errors="replace")
                            )
                        except (LookupError, UnicodeDecodeError):
                            body_parts.append(
                                payload.decode("utf-8", errors="replace")
                            )
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    body_parts.append(payload.decode(charset, errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    body_parts.append(payload.decode("utf-8", errors="replace"))

        return "\n".join(body_parts)
