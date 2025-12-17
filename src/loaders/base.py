"""Base loader class for all data sources."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal

from llama_index.core.schema import Document

# Document categories for priority system (FR-P0-3)
DocumentCategory = Literal[
    "decision", "note", "email", "conversation",
    "profile", "contact", "location", "interests", "search_history"
]


class BaseLoader(ABC):
    """Abstract base class for document loaders.

    All loaders now add these metadata fields:
    - document_id: UUID for tracking and deletion (FR-P0-5)
    - is_pinned: User-pinned as authoritative (FR-P0-3)
    - is_approved: User-verified content (FR-P0-3)
    - document_category: For priority weighting (FR-P0-3)
    """

    # Mapping from source_type to default category
    CATEGORY_MAP: dict[str, DocumentCategory] = {
        "text": "note",
        "email": "email",
        "whatsapp": "conversation",
        "messenger": "conversation",
        "profile": "profile",
        "contacts": "contact",
        "location": "location",
        "interests": "interests",
        "search_history": "search_history",
    }

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
        self,
        content: str,
        metadata: dict,
        file_path: Path,
        document_id: str | None = None,
    ) -> Document:
        """Create a LlamaIndex Document with standard metadata.

        Args:
            content: Text content of the document
            metadata: Additional metadata from parser
            file_path: Source file path
            document_id: Optional pre-assigned document ID

        Returns:
            LlamaIndex Document object with full metadata
        """
        # Generate document_id if not provided
        doc_id = document_id or str(uuid.uuid4())

        # Determine document category from source type
        category = self.CATEGORY_MAP.get(self.source_type, "note")

        base_metadata = {
            # Core identifiers
            "document_id": doc_id,
            "source_type": self.source_type,
            "filename": file_path.name,
            "file_path": f"{file_path.parent.name}/{file_path.name}",
            "indexed_at": datetime.now().isoformat(),
            # Priority fields (FR-P0-3)
            "is_pinned": False,
            "is_approved": False,
            "document_category": category,
        }
        base_metadata.update(metadata)

        return Document(text=content, metadata=base_metadata)

    @staticmethod
    def generate_document_id() -> str:
        """Generate a new document ID.

        Returns:
            UUID string for document identification
        """
        return str(uuid.uuid4())
