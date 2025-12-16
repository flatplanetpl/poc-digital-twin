"""Document registry for tracking indexed documents.

Provides document tracking infrastructure for:
- FR-P0-5: Forget / Right to Be Forgotten (per-document deletion)
- FR-P2-5: Re-index & Migration (embedding model tracking)
- FR-P3-1: Ingestion Monitoring (document counts)
"""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterator, Literal

from pydantic import BaseModel, Field

from src.config import settings


class DocumentStatus(str, Enum):
    """Status of a tracked document."""

    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"


class TrackedDocument(BaseModel):
    """A document tracked in the registry."""

    id: str  # UUID
    file_path: str
    content_hash: str  # SHA256 of file content
    source_type: str
    chunk_count: int = 0
    embedding_model: str
    metadata_version: int = 1
    first_indexed_at: datetime
    last_indexed_at: datetime
    status: DocumentStatus = DocumentStatus.ACTIVE
    metadata: dict = Field(default_factory=dict)


class DocumentRegistry:
    """Track indexed documents for deletion, re-indexing, and monitoring.

    This registry provides:
    - Document tracking with unique IDs
    - Content hash for change detection
    - Embedding model tracking for re-index detection
    - Soft deletion support for RTBF compliance
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize document registry.

        Args:
            db_path: Path to SQLite database. If None, uses default.
        """
        self.db_path = db_path or settings.storage_dir / "document_registry.db"
        self._ensure_tables()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            # Main document tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    content_hash TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    embedding_model TEXT NOT NULL,
                    metadata_version INTEGER NOT NULL DEFAULT 1,
                    first_indexed_at TEXT NOT NULL,
                    last_indexed_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata TEXT
                )
            """)

            # Index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_file_path
                ON documents(file_path)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_status
                ON documents(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_source_type
                ON documents(source_type)
            """)

            # Schema version tracking for migrations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    description TEXT,
                    applied_at TEXT NOT NULL
                )
            """)

            # Embedding model tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL UNIQUE,
                    dimension INTEGER NOT NULL,
                    first_used_at TEXT NOT NULL,
                    is_current INTEGER NOT NULL DEFAULT 0
                )
            """)

    @staticmethod
    def compute_content_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA256 hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @staticmethod
    def generate_document_id() -> str:
        """Generate a unique document ID.

        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    def register_document(
        self,
        file_path: Path,
        source_type: str,
        chunk_count: int = 0,
        metadata: dict | None = None,
    ) -> TrackedDocument:
        """Register a new document or update existing.

        Args:
            file_path: Path to source file
            source_type: Type of document (text, email, whatsapp, etc.)
            chunk_count: Number of chunks created
            metadata: Additional metadata to store

        Returns:
            TrackedDocument with assigned ID
        """
        file_path = Path(file_path).absolute()
        content_hash = self.compute_content_hash(file_path)
        now = datetime.now()

        # Check if document already exists
        existing = self.get_by_file_path(str(file_path))

        with self._get_connection() as conn:
            if existing:
                # Update existing document
                conn.execute(
                    """
                    UPDATE documents
                    SET content_hash = ?,
                        source_type = ?,
                        chunk_count = ?,
                        embedding_model = ?,
                        last_indexed_at = ?,
                        status = ?,
                        metadata = ?
                    WHERE id = ?
                    """,
                    (
                        content_hash,
                        source_type,
                        chunk_count,
                        settings.embedding_model,
                        now.isoformat(),
                        DocumentStatus.ACTIVE.value,
                        json.dumps(metadata) if metadata else None,
                        existing.id,
                    ),
                )
                return TrackedDocument(
                    id=existing.id,
                    file_path=str(file_path),
                    content_hash=content_hash,
                    source_type=source_type,
                    chunk_count=chunk_count,
                    embedding_model=settings.embedding_model,
                    metadata_version=existing.metadata_version,
                    first_indexed_at=existing.first_indexed_at,
                    last_indexed_at=now,
                    status=DocumentStatus.ACTIVE,
                    metadata=metadata or {},
                )
            else:
                # Create new document
                doc_id = self.generate_document_id()
                conn.execute(
                    """
                    INSERT INTO documents (
                        id, file_path, content_hash, source_type, chunk_count,
                        embedding_model, metadata_version, first_indexed_at,
                        last_indexed_at, status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        str(file_path),
                        content_hash,
                        source_type,
                        chunk_count,
                        settings.embedding_model,
                        1,
                        now.isoformat(),
                        now.isoformat(),
                        DocumentStatus.ACTIVE.value,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                return TrackedDocument(
                    id=doc_id,
                    file_path=str(file_path),
                    content_hash=content_hash,
                    source_type=source_type,
                    chunk_count=chunk_count,
                    embedding_model=settings.embedding_model,
                    metadata_version=1,
                    first_indexed_at=now,
                    last_indexed_at=now,
                    status=DocumentStatus.ACTIVE,
                    metadata=metadata or {},
                )

    def get_by_id(self, document_id: str) -> TrackedDocument | None:
        """Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            TrackedDocument or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()

            if not row:
                return None

            return self._row_to_document(row)

    def get_by_file_path(self, file_path: str) -> TrackedDocument | None:
        """Get document by file path.

        Args:
            file_path: Absolute path to file

        Returns:
            TrackedDocument or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE file_path = ?",
                (file_path,),
            ).fetchone()

            if not row:
                return None

            return self._row_to_document(row)

    def list_documents(
        self,
        status: DocumentStatus | None = None,
        source_type: str | None = None,
        limit: int = 100,
    ) -> list[TrackedDocument]:
        """List tracked documents with optional filters.

        Args:
            status: Filter by status
            source_type: Filter by source type
            limit: Maximum documents to return

        Returns:
            List of TrackedDocument objects
        """
        query = "SELECT * FROM documents WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)

        query += " ORDER BY last_indexed_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_document(row) for row in rows]

    def mark_deleted(self, document_id: str) -> bool:
        """Mark document as deleted (soft delete).

        Args:
            document_id: Document UUID

        Returns:
            True if marked, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE documents
                SET status = ?, last_indexed_at = ?
                WHERE id = ?
                """,
                (DocumentStatus.DELETED.value, datetime.now().isoformat(), document_id),
            )
            return cursor.rowcount > 0

    def mark_archived(self, document_id: str) -> bool:
        """Mark document as archived.

        Args:
            document_id: Document UUID

        Returns:
            True if marked, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE documents
                SET status = ?, last_indexed_at = ?
                WHERE id = ?
                """,
                (
                    DocumentStatus.ARCHIVED.value,
                    datetime.now().isoformat(),
                    document_id,
                ),
            )
            return cursor.rowcount > 0

    def permanently_delete(self, document_id: str) -> bool:
        """Permanently remove document from registry.

        Args:
            document_id: Document UUID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0

    def get_changed_files(self, directory: Path) -> dict[str, str]:
        """Find files that need re-indexing.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping file_path to change_type ('new', 'modified', 'deleted')
        """
        changes: dict[str, str] = {}

        # Get all active documents
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT file_path, content_hash FROM documents WHERE status = ?",
                (DocumentStatus.ACTIVE.value,),
            ).fetchall()
            existing = {row["file_path"]: row["content_hash"] for row in rows}

        # Scan directory for current files
        current_files = set()
        for ext in [".txt", ".md", ".markdown", ".eml", ".mbox", ".json"]:
            current_files.update(str(f.absolute()) for f in directory.rglob(f"*{ext}"))

        # Check for new/modified files
        for file_path in current_files:
            if file_path not in existing:
                changes[file_path] = "new"
            else:
                current_hash = self.compute_content_hash(Path(file_path))
                if current_hash != existing[file_path]:
                    changes[file_path] = "modified"

        # Check for deleted files
        for file_path in existing:
            if file_path not in current_files:
                changes[file_path] = "deleted"

        return changes

    def get_stats(self) -> dict:
        """Get registry statistics.

        Returns:
            Dict with counts by status and source type
        """
        with self._get_connection() as conn:
            # Count by status
            status_counts = {}
            for status in DocumentStatus:
                count = conn.execute(
                    "SELECT COUNT(*) FROM documents WHERE status = ?",
                    (status.value,),
                ).fetchone()[0]
                status_counts[status.value] = count

            # Count by source type (active only)
            source_rows = conn.execute(
                """
                SELECT source_type, COUNT(*) as count, SUM(chunk_count) as chunks
                FROM documents
                WHERE status = ?
                GROUP BY source_type
                """,
                (DocumentStatus.ACTIVE.value,),
            ).fetchall()
            source_counts = {
                row["source_type"]: {
                    "documents": row["count"],
                    "chunks": row["chunks"] or 0,
                }
                for row in source_rows
            }

            return {
                "by_status": status_counts,
                "by_source_type": source_counts,
                "total_active": status_counts.get("active", 0),
                "total_deleted": status_counts.get("deleted", 0),
            }

    def check_embedding_compatibility(self) -> dict:
        """Check if current embedding model matches indexed data.

        Returns:
            Dict with compatibility info
        """
        with self._get_connection() as conn:
            # Get models used in active documents
            rows = conn.execute(
                """
                SELECT DISTINCT embedding_model, COUNT(*) as count
                FROM documents
                WHERE status = ?
                GROUP BY embedding_model
                """,
                (DocumentStatus.ACTIVE.value,),
            ).fetchall()

            models_used = {row["embedding_model"]: row["count"] for row in rows}

            current_model = settings.embedding_model
            compatible = len(models_used) <= 1 and current_model in models_used

            return {
                "compatible": compatible,
                "current_model": current_model,
                "models_in_index": models_used,
                "requires_reindex": not compatible and len(models_used) > 0,
            }

    def _row_to_document(self, row: sqlite3.Row) -> TrackedDocument:
        """Convert database row to TrackedDocument."""
        return TrackedDocument(
            id=row["id"],
            file_path=row["file_path"],
            content_hash=row["content_hash"],
            source_type=row["source_type"],
            chunk_count=row["chunk_count"],
            embedding_model=row["embedding_model"],
            metadata_version=row["metadata_version"],
            first_indexed_at=datetime.fromisoformat(row["first_indexed_at"]),
            last_indexed_at=datetime.fromisoformat(row["last_indexed_at"]),
            status=DocumentStatus(row["status"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
