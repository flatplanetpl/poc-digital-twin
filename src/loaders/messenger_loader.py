"""Loader for Facebook Messenger JSON exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class MessengerLoader(BaseLoader):
    """Loader for Facebook Messenger JSON exports.

    Facebook exports messages in JSON format from "Download Your Information".
    Structure:
    - inbox/<conversation_name>/message_1.json (and message_2.json, etc.)
    - Each file contains: participants, messages[], title, thread_path

    Messages have: sender_name, timestamp_ms, content, type, photos[], etc.
    """

    # Metadata length limits to prevent chunk_size overflow
    MAX_PARTICIPANTS_DISPLAY = 3
    MAX_CHAT_NAME_LENGTH = 100

    def __init__(self, group_messages: bool = True, group_window_minutes: int = 30):
        """Initialize Messenger loader.

        Args:
            group_messages: If True, group consecutive messages from same sender
            group_window_minutes: Time window for grouping messages (in minutes)
        """
        super().__init__(source_type="messenger")
        self.group_messages = group_messages
        self.group_window_minutes = group_window_minutes

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def _truncate_participants(self, participants: list[str]) -> str:
        """Truncate participant list to avoid metadata overflow.

        For group chats with many participants, storing all names in metadata
        can exceed LlamaIndex's chunk_size limit. This method limits the
        displayed names while preserving the total count.

        Args:
            participants: Full list of participant names

        Returns:
            Truncated string like "Alice, Bob, Carol (+7 others)"
        """
        if len(participants) <= self.MAX_PARTICIPANTS_DISPLAY:
            return ", ".join(participants)

        displayed = participants[: self.MAX_PARTICIPANTS_DISPLAY]
        remaining = len(participants) - self.MAX_PARTICIPANTS_DISPLAY
        return f"{', '.join(displayed)} (+{remaining} others)"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Messenger JSON export file.

        Args:
            file_path: Path to the message JSON file

        Yields:
            Tuple of (content, metadata) for each message/group
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Try with different encoding (Facebook sometimes uses latin-1)
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    data = json.load(f)
            except Exception:
                return

        # Validate structure - must have messages array
        if not isinstance(data, dict) or "messages" not in data:
            return

        messages = data.get("messages", [])
        if not messages:
            return

        # Extract conversation metadata
        participants = data.get("participants", [])
        participant_names = [p.get("name", "Unknown") for p in participants]
        thread_title = data.get("title", "Unknown Chat")

        # Parse messages (Facebook stores them in reverse chronological order)
        parsed_messages = []
        for msg in reversed(messages):
            parsed = self._parse_message(msg)
            if parsed:
                parsed_messages.append(parsed)

        if not parsed_messages:
            return

        # Build chat context
        chat_context = {
            "chat_name": thread_title,
            "participants": participant_names,
        }

        if self.group_messages:
            yield from self._yield_grouped_messages(parsed_messages, chat_context)
        else:
            yield from self._yield_individual_messages(parsed_messages, chat_context)

    def _parse_message(self, msg: dict) -> dict | None:
        """Parse a single message from Messenger format.

        Args:
            msg: Message dictionary from JSON

        Returns:
            Parsed message dict or None if invalid/unsupported
        """
        # Skip non-text messages (photos, stickers, etc. without content)
        content = msg.get("content")
        if not content:
            # Check for special message types
            if msg.get("photos"):
                content = "[Photo]"
            elif msg.get("sticker"):
                content = "[Sticker]"
            elif msg.get("videos"):
                content = "[Video]"
            elif msg.get("audio_files"):
                content = "[Audio]"
            elif msg.get("gifs"):
                content = "[GIF]"
            elif msg.get("share"):
                share = msg.get("share", {})
                link = share.get("link", "")
                content = f"[Shared: {link}]" if link else "[Shared content]"
            else:
                return None

        # Facebook encodes text in latin-1 but stores as UTF-8
        # This causes mojibake - need to fix encoding
        if isinstance(content, str):
            try:
                content = content.encode("latin-1").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass  # Keep original if conversion fails

        sender = msg.get("sender_name", "Unknown")
        # Fix sender name encoding too
        try:
            sender = sender.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

        timestamp_ms = msg.get("timestamp_ms", 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000)

        return {
            "sender": sender,
            "content": content,
            "timestamp": timestamp,
            "type": msg.get("type", "Generic"),
        }

    def _yield_grouped_messages(
        self, messages: list[dict], chat_context: dict
    ) -> Iterator[tuple[str, dict]]:
        """Yield messages grouped by sender within time window.

        Args:
            messages: List of parsed messages
            chat_context: Chat metadata (name, participants)

        Yields:
            Tuple of (grouped_content, metadata)
        """
        if not messages:
            return

        current_group = [messages[0]]

        for msg in messages[1:]:
            prev_msg = current_group[-1]

            same_sender = msg["sender"] == prev_msg["sender"]
            time_diff = (msg["timestamp"] - prev_msg["timestamp"]).total_seconds() / 60
            within_window = time_diff <= self.group_window_minutes

            if same_sender and within_window:
                current_group.append(msg)
            else:
                yield self._format_message_group(current_group, chat_context)
                current_group = [msg]

        # Don't forget the last group
        yield self._format_message_group(current_group, chat_context)

    def _yield_individual_messages(
        self, messages: list[dict], chat_context: dict
    ) -> Iterator[tuple[str, dict]]:
        """Yield each message individually.

        Args:
            messages: List of parsed messages
            chat_context: Chat metadata

        Yields:
            Tuple of (content, metadata) for each message
        """
        for msg in messages:
            content = f"{msg['sender']}: {msg['content']}"
            metadata = {
                "date": msg["timestamp"].isoformat(),
                "sender": msg["sender"],
                "chat_name": self._truncate_text(
                    chat_context["chat_name"], self.MAX_CHAT_NAME_LENGTH
                ),
                "participants": self._truncate_participants(chat_context["participants"]),
                "participant_count": len(chat_context["participants"]),
            }
            yield content, metadata

    def _format_message_group(
        self, messages: list[dict], chat_context: dict
    ) -> tuple[str, dict]:
        """Format a group of messages into content and metadata.

        Args:
            messages: List of messages from same sender
            chat_context: Chat metadata

        Returns:
            Tuple of (formatted_content, metadata)
        """
        sender = messages[0]["sender"]
        start_time = messages[0]["timestamp"]
        end_time = messages[-1]["timestamp"]

        # Format content
        texts = [msg["content"] for msg in messages]
        content = f"{sender}: " + " ".join(texts)

        metadata = {
            "date": start_time.isoformat(),
            "sender": sender,
            "chat_name": self._truncate_text(
                chat_context["chat_name"], self.MAX_CHAT_NAME_LENGTH
            ),
            "participants": self._truncate_participants(chat_context["participants"]),
            "message_count": len(messages),
            "participant_count": len(chat_context["participants"]),
        }

        if start_time != end_time:
            metadata["date_end"] = end_time.isoformat()

        return content, metadata
