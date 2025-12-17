"""Loader for Facebook search history exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class SearchHistoryLoader(BaseLoader):
    """Loader for Facebook search history exports.

    Parses:
    - logged_information/search/your_search_history.json

    Groups searches by day/week for context about user interests and behavior.
    """

    def __init__(self, group_by: str = "day"):
        """Initialize Search History loader.

        Args:
            group_by: Grouping strategy - "day", "week", or "none"
        """
        super().__init__(source_type="search_history")
        self.group_by = group_by

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def _fix_encoding(self, text: str) -> str:
        """Fix Facebook's mojibake encoding."""
        if not isinstance(text, str):
            return str(text) if text else ""
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Facebook search history JSON file.

        Args:
            file_path: Path to the JSON file

        Yields:
            Tuple of (content, metadata) for search entries
        """
        if file_path.name != "your_search_history.json":
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    data = json.load(f)
            except Exception:
                return

        searches = data.get("searches_v2", data.get("searches", []))
        if not searches:
            return

        if self.group_by == "none":
            yield from self._yield_individual(searches)
        elif self.group_by == "week":
            yield from self._yield_grouped(searches, "%Y-W%W")
        else:  # day
            yield from self._yield_grouped(searches, "%Y-%m-%d")

    def _extract_search_text(self, search: dict) -> str:
        """Extract search text from various Facebook structures.

        Args:
            search: Search entry dictionary

        Returns:
            Extracted search text
        """
        # Try attachments first
        attachments = search.get("attachments", [])
        for att in attachments:
            data_items = att.get("data", [])
            for item in data_items:
                text = item.get("text", "")
                if text:
                    return self._fix_encoding(text.strip('"'))

        # Try direct data field
        data = search.get("data", [])
        for item in data:
            text = item.get("text", "")
            if text:
                return self._fix_encoding(text)

        # Try title
        title = search.get("title", "")
        if title and ":" in title:
            # Extract search term from title like "Searched for: query"
            return self._fix_encoding(title.split(":")[-1].strip())

        return ""

    def _yield_individual(self, searches: list) -> Iterator[tuple[str, dict]]:
        """Yield each search as individual document.

        Args:
            searches: List of search entries

        Yields:
            Tuple of (content, metadata) for each search
        """
        for search in searches:
            text = self._extract_search_text(search)
            if not text:
                continue

            timestamp = search.get("timestamp", 0)
            dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

            title = self._fix_encoding(search.get("title", "Search"))

            content = f"Facebook search: {text}"
            if "Odwiedzono" in title or "Visited" in title:
                content = f"Facebook visited: {text}"

            metadata = {
                "date": dt.isoformat(),
                "search_query": text[:200],  # Limit length
                "search_type": "visit" if "Odwiedzono" in title else "search",
                "document_category": "search_history",
            }

            yield content, metadata

    def _yield_grouped(
        self,
        searches: list,
        date_format: str,
    ) -> Iterator[tuple[str, dict]]:
        """Yield searches grouped by time period.

        Args:
            searches: List of search entries
            date_format: strftime format for grouping key

        Yields:
            Tuple of (content, metadata) for each group
        """
        groups: dict[str, list] = {}

        for search in searches:
            text = self._extract_search_text(search)
            if not text:
                continue

            timestamp = search.get("timestamp", 0)
            dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
            group_key = dt.strftime(date_format)

            title = self._fix_encoding(search.get("title", ""))
            search_type = "visit" if "Odwiedzono" in title or "Visited" in title else "search"

            if group_key not in groups:
                groups[group_key] = []

            groups[group_key].append({
                "text": text,
                "type": search_type,
                "timestamp": dt,
            })

        for group_key, items in groups.items():
            # Sort by timestamp
            items.sort(key=lambda x: x["timestamp"])

            # Separate searches and visits
            searches_list = [i["text"] for i in items if i["type"] == "search"]
            visits_list = [i["text"] for i in items if i["type"] == "visit"]

            content_parts = [f"Facebook activity for {group_key}:"]

            if searches_list:
                unique_searches = list(dict.fromkeys(searches_list))[:20]  # Dedupe, limit
                content_parts.append(f"Searches: {', '.join(unique_searches)}")

            if visits_list:
                unique_visits = list(dict.fromkeys(visits_list))[:20]
                content_parts.append(f"Profile visits: {', '.join(unique_visits)}")

            content = "\n".join(content_parts)

            # Get date from first item
            first_date = items[0]["timestamp"]

            metadata = {
                "date": first_date.isoformat(),
                "document_category": "search_history",
                "search_count": len(searches_list),
                "visit_count": len(visits_list),
                "period": group_key,
            }

            yield content, metadata
