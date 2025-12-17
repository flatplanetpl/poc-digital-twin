"""Loader for Facebook friends and contacts exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class ContactsLoader(BaseLoader):
    """Loader for Facebook friends and phone contacts exports.

    Parses:
    - connections/friends/your_friends.json - Facebook friends with timestamps
    - personal_information/other_personal_information/contacts_uploaded_from_your_phone.json

    Creates one document per contact for granular deletion capability.
    """

    def __init__(self):
        """Initialize Contacts loader."""
        super().__init__(source_type="contacts")

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def _fix_encoding(self, text: str) -> str:
        """Fix Facebook's mojibake encoding (latin-1 stored as UTF-8).

        Args:
            text: Text with potential encoding issues

        Returns:
            Properly decoded UTF-8 text
        """
        if not isinstance(text, str):
            return str(text) if text else ""
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    def _normalize_name(self, name: str) -> str:
        """Normalize contact name for matching.

        Args:
            name: Original contact name

        Returns:
            Lowercase, stripped name for fuzzy matching
        """
        return name.lower().strip()

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Facebook contacts/friends JSON file.

        Args:
            file_path: Path to the JSON file

        Yields:
            Tuple of (content, metadata) for each contact
        """
        filename = file_path.name

        # Route to appropriate parser
        if filename == "your_friends.json":
            yield from self._parse_friends(file_path)
        elif filename == "contacts_uploaded_from_your_phone.json":
            yield from self._parse_phone_contacts(file_path)

    def _parse_friends(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Facebook friends list.

        Args:
            file_path: Path to your_friends.json

        Yields:
            Tuple of (content, metadata) for each friend
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    data = json.load(f)
            except Exception:
                return

        friends = data.get("friends_v2", [])
        if not friends:
            return

        for friend in friends:
            name = self._fix_encoding(friend.get("name", ""))
            if not name:
                continue

            timestamp = friend.get("timestamp", 0)
            friendship_date = datetime.fromtimestamp(timestamp) if timestamp else None

            content = f"Facebook friend: {name}"
            if friendship_date:
                content += f" (friends since {friendship_date.strftime('%Y-%m-%d')})"

            metadata = {
                "contact_name": name,
                "normalized_name": self._normalize_name(name),
                "contact_type": "friend",
                "document_category": "contact",
            }

            if friendship_date:
                metadata["friendship_date"] = friendship_date.isoformat()
                metadata["date"] = friendship_date.isoformat()

            yield content, metadata

    def _parse_phone_contacts(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse uploaded phone contacts.

        Args:
            file_path: Path to contacts_uploaded_from_your_phone.json

        Yields:
            Tuple of (content, metadata) for each contact
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    data = json.load(f)
            except Exception:
                return

        # Handle both list format and wrapped format
        contacts = data if isinstance(data, list) else data.get("contacts_v2", data.get("contacts", []))

        for contact in contacts:
            # Extract name from label_values structure
            name = ""
            phone = ""
            email = ""
            creation_time = None

            label_values = contact.get("label_values", [])
            for lv in label_values:
                label = lv.get("label", "")
                value = lv.get("value", "")

                if label in ("Nazwa", "Name") and value:
                    name = self._fix_encoding(value)
                elif label in ("Imię", "First name") and value and not name:
                    name = self._fix_encoding(value)
                elif "phone" in label.lower() and value:
                    phone = value
                elif "email" in label.lower() and value:
                    email = value
                elif label in ("Czas utworzenia", "Creation time"):
                    ts = lv.get("timestamp_value", 0)
                    if ts:
                        creation_time = datetime.fromtimestamp(ts)

            # Skip contacts without name
            if not name:
                continue

            content_parts = [f"Phone contact: {name}"]
            if phone:
                content_parts.append(f"Phone: {phone}")
            if email:
                content_parts.append(f"Email: {email}")

            content = ", ".join(content_parts)

            metadata = {
                "contact_name": name,
                "normalized_name": self._normalize_name(name),
                "contact_type": "phone_contact",
                "document_category": "contact",
            }

            if phone:
                metadata["phone"] = phone
            if email:
                metadata["email"] = email
            if creation_time:
                metadata["date"] = creation_time.isoformat()

            yield content, metadata
