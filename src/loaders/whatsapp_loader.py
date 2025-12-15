"""Loader for WhatsApp chat exports (TXT format)."""

import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class WhatsAppLoader(BaseLoader):
    """Loader for WhatsApp chat exports in TXT format.

    Handles the standard WhatsApp export format:
    [DD/MM/YYYY, HH:MM:SS] Sender: Message
    or
    DD/MM/YYYY, HH:MM - Sender: Message
    """

    # Common WhatsApp export patterns
    PATTERNS = [
        # [DD/MM/YYYY, HH:MM:SS] Sender: Message
        re.compile(
            r"\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^:]+):\s*(.*)"
        ),
        # DD/MM/YYYY, HH:MM - Sender: Message
        re.compile(
            r"(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*-\s*([^:]+):\s*(.*)"
        ),
        # MM/DD/YY, HH:MM AM/PM - Sender: Message (US format)
        re.compile(
            r"(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*-\s*([^:]+):\s*(.*)",
            re.IGNORECASE,
        ),
    ]

    def __init__(self, group_messages: bool = True, group_window_minutes: int = 30):
        """Initialize WhatsApp loader.

        Args:
            group_messages: If True, group consecutive messages from same sender
            group_window_minutes: Time window for grouping messages (in minutes)
        """
        super().__init__(source_type="whatsapp")
        self.group_messages = group_messages
        self.group_window_minutes = group_window_minutes

    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse WhatsApp export file.

        Args:
            file_path: Path to the WhatsApp export file

        Yields:
            Tuple of (content, metadata) for each message/group
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="utf-8-sig")

        messages = self._parse_messages(content)

        if not messages:
            return

        # Extract chat name from filename (e.g., "WhatsApp Chat with John.txt")
        chat_name = self._extract_chat_name(file_path.stem)

        if self.group_messages:
            yield from self._yield_grouped_messages(messages, chat_name)
        else:
            yield from self._yield_individual_messages(messages, chat_name)

    def _parse_messages(
        self, content: str
    ) -> list[dict]:
        """Parse raw content into structured messages.

        Args:
            content: Raw file content

        Returns:
            List of message dictionaries
        """
        messages = []
        current_message = None

        for line in content.split("\n"):
            parsed = self._parse_line(line)

            if parsed:
                if current_message:
                    messages.append(current_message)
                current_message = parsed
            elif current_message:
                # Continuation of previous message
                current_message["text"] += "\n" + line

        if current_message:
            messages.append(current_message)

        return messages

    def _parse_line(self, line: str) -> dict | None:
        """Try to parse a line as a new message.

        Args:
            line: Line of text to parse

        Returns:
            Message dict or None if not a new message
        """
        for pattern in self.PATTERNS:
            match = pattern.match(line.strip())
            if match:
                date_str, time_str, sender, text = match.groups()
                timestamp = self._parse_timestamp(date_str, time_str)
                return {
                    "timestamp": timestamp,
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
        return None

    def _parse_timestamp(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime.

        Args:
            date_str: Date string (various formats)
            time_str: Time string

        Returns:
            Parsed datetime object
        """
        # Try common date formats
        date_formats = [
            "%d/%m/%Y",
            "%d/%m/%y",
            "%m/%d/%Y",
            "%m/%d/%y",
        ]

        # Clean time string
        time_str = time_str.strip().upper()
        has_ampm = "AM" in time_str or "PM" in time_str

        if has_ampm:
            time_formats = ["%I:%M %p", "%I:%M:%S %p", "%I:%M%p"]
        else:
            time_formats = ["%H:%M", "%H:%M:%S"]

        for date_fmt in date_formats:
            for time_fmt in time_formats:
                try:
                    full_str = f"{date_str} {time_str}"
                    full_fmt = f"{date_fmt} {time_fmt}"
                    return datetime.strptime(full_str, full_fmt)
                except ValueError:
                    continue

        # Fallback to current time
        return datetime.now()

    def _extract_chat_name(self, filename: str) -> str:
        """Extract chat participant name from filename.

        Args:
            filename: Filename without extension

        Returns:
            Extracted chat name or original filename
        """
        # Handle "WhatsApp Chat with X" format
        patterns = [
            r"WhatsApp Chat with (.+)",
            r"Chat WhatsApp z (.+)",  # Polish
            r"WhatsApp-chat met (.+)",  # Dutch
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)

        return filename

    def _yield_grouped_messages(
        self, messages: list[dict], chat_name: str
    ) -> Iterator[tuple[str, dict]]:
        """Yield messages grouped by sender within time window.

        Args:
            messages: List of parsed messages
            chat_name: Name of the chat

        Yields:
            Tuple of (grouped_content, metadata)
        """
        if not messages:
            return

        current_group = [messages[0]]

        for msg in messages[1:]:
            prev_msg = current_group[-1]

            # Check if should continue grouping
            same_sender = msg["sender"] == prev_msg["sender"]
            time_diff = (msg["timestamp"] - prev_msg["timestamp"]).total_seconds() / 60
            within_window = time_diff <= self.group_window_minutes

            if same_sender and within_window:
                current_group.append(msg)
            else:
                yield self._format_message_group(current_group, chat_name)
                current_group = [msg]

        # Don't forget the last group
        yield self._format_message_group(current_group, chat_name)

    def _yield_individual_messages(
        self, messages: list[dict], chat_name: str
    ) -> Iterator[tuple[str, dict]]:
        """Yield each message individually.

        Args:
            messages: List of parsed messages
            chat_name: Name of the chat

        Yields:
            Tuple of (content, metadata) for each message
        """
        for msg in messages:
            content = f"{msg['sender']}: {msg['text']}"
            metadata = {
                "date": msg["timestamp"].isoformat(),
                "sender": msg["sender"],
                "chat_name": chat_name,
            }
            yield content, metadata

    def _format_message_group(
        self, messages: list[dict], chat_name: str
    ) -> tuple[str, dict]:
        """Format a group of messages into content and metadata.

        Args:
            messages: List of messages from same sender
            chat_name: Name of the chat

        Returns:
            Tuple of (formatted_content, metadata)
        """
        sender = messages[0]["sender"]
        start_time = messages[0]["timestamp"]
        end_time = messages[-1]["timestamp"]

        # Format content
        texts = [msg["text"] for msg in messages]
        content = f"{sender}: " + " ".join(texts)

        metadata = {
            "date": start_time.isoformat(),
            "sender": sender,
            "chat_name": chat_name,
            "message_count": len(messages),
        }

        if start_time != end_time:
            metadata["date_end"] = end_time.isoformat()

        return content, metadata
