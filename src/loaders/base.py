"""Base loader class for all data sources."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Iterator

from llama_index.core.schema import Document


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    def __init__(self, source_type: str):
        """Initialize loader with source type identifier.

        Args:
            source_type: Type identifier for this data source (e.g., "text", "email")
        """
        self.source_type = source_type

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass

    @abstractmethod
    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse a single file and yield (content, metadata) tuples.

        Args:
            file_path: Path to the file to parse

        Yields:
            Tuple of (text_content, metadata_dict)
        """
        pass

    def load(self, directory: Path) -> list[Document]:
        """Load all supported files from directory.

        Args:
            directory: Directory to scan for files

        Returns:
            List of LlamaIndex Document objects
        """
        documents = []
        extensions = self.supported_extensions()

        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    for content, metadata in self._parse_file(file_path):
                        doc = self._create_document(content, metadata, file_path)
                        documents.append(doc)
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")

        return documents

    def _create_document(
        self, content: str, metadata: dict, file_path: Path
    ) -> Document:
        """Create a LlamaIndex Document with standard metadata.

        Args:
            content: Text content of the document
            metadata: Additional metadata from parser
            file_path: Source file path

        Returns:
            LlamaIndex Document object
        """
        base_metadata = {
            "source_type": self.source_type,
            "filename": file_path.name,
            "file_path": str(file_path.absolute()),
            "indexed_at": datetime.now().isoformat(),
        }
        base_metadata.update(metadata)

        return Document(text=content, metadata=base_metadata)
