"""Loader for plain text files (TXT, MD)."""

import os
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class TextLoader(BaseLoader):
    """Loader for plain text and markdown files."""

    def __init__(self):
        super().__init__(source_type="text")

    def supported_extensions(self) -> list[str]:
        return [".txt", ".md", ".markdown"]

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse a text file and yield its content with metadata.

        Args:
            file_path: Path to the text file

        Yields:
            Tuple of (content, metadata)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        # Extract file modification time as document date
        mtime = os.path.getmtime(file_path)
        file_date = datetime.fromtimestamp(mtime)

        metadata = {
            "date": file_date.isoformat(),
            "file_type": file_path.suffix.lstrip("."),
            "char_count": len(content),
        }

        # For markdown files, try to extract title from first heading
        if file_path.suffix in [".md", ".markdown"]:
            title = self._extract_markdown_title(content)
            if title:
                metadata["title"] = title

        yield content, metadata

    def _extract_markdown_title(self, content: str) -> str | None:
        """Extract title from first markdown heading.

        Args:
            content: Markdown content

        Returns:
            Title string or None if not found
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None
