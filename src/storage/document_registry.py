"""Document registry for tracking indexed documents.

Provides document tracking infrastructure for:
- FR-P0-5: Forget / Right to Be Forgotten (per-document deletion)
- FR-P2-5: Re-index & Migration (embedding model tracking)
- FR-P3-1: Ingestion Monitoring (document counts)

Also provides two-tier metadata storage:
- Light metadata: stored in Qdrant chunks (for filtering/search)
- Heavy metadata: stored in SQLite chunk_details table (for display)
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


# Fields that should stay in Qdrant (essential for filtering/search)
LIGHT_METADATA_FIELDS = {
    "document_id",       # Link to chunk_details
    "source_type",       # Filter by source
    "date",              # Temporal filtering
    "date_end",          # Date range end
    "sender",            # Person filtering
    "document_category", # Priority weighting
    "contact_name",      # Contact filtering
    "normalized_name",   # Fuzzy matching
    "is_group_chat",     # Chat type filtering
    "thread_type",       # Thread type filtering
    "message_count",     # Stats (small int)
    "participant_count", # Stats (small int)
}

# Fields to move to chunk_details (heavy/rarely filtered)
HEAVY_METADATA_FIELDS = {
    "file_path",         # Debug only
    "filename",          # Redundant
    "indexed_at",        # Rarely needed at query time
    "is_pinned",         # User preference (updatable)
    "is_approved",       # User preference (updatable)
    "family_members",    # Heavy JSON from ProfileLoader
    "work_history",      # Heavy JSON from ProfileLoader
    "education",         # Heavy JSON from ProfileLoader
    "shared_links",      # URLs from MessengerLoader
    "media_types",       # Media info
    "has_media",         # Media flag
    "reaction_count",    # Stats
    "chat_name",         # Can be long
    "participants",      # Can be long (truncated list)
    "search_query",      # From SearchHistoryLoader
    # Profile fields
    "full_name", "first_name", "last_name", "email", "phone",
    "birthday", "gender", "city", "hometown",
    "relationship_status", "partner", "username", "registration_date",
    # Location fields
    "latitude", "longitude", "cities", "regions", "location_type", "record_count",
    # Contact fields
    "contact_type", "friendship_date",
}


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

            # Chunk-level heavy metadata storage (two-tier metadata system)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL UNIQUE,
                    source_type TEXT NOT NULL,
                    file_path TEXT,
                    indexed_at TEXT,
                    is_pinned BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_details_document_id
                ON chunk_details(document_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_details_source_type
                ON chunk_details(source_type)
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
                        settings.effective_embedding_model,
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
                    embedding_model=settings.effective_embedding_model,
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
                        settings.effective_embedding_model,
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
                    embedding_model=settings.effective_embedding_model,
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

            current_model = settings.effective_embedding_model
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

    # =========================================================================
    # Two-tier metadata methods (chunk_details table)
    # =========================================================================

    @staticmethod
    def split_metadata(metadata: dict) -> tuple[dict, dict]:
        """Split metadata into light (Qdrant) and heavy (SQLite) parts.

        Args:
            metadata: Full metadata dictionary from loader

        Returns:
            Tuple of (light_metadata, heavy_metadata)

        Example:
            light, heavy = registry.split_metadata(doc.metadata)
            # Store light in Qdrant, heavy in chunk_details
        """
        light = {}
        heavy = {}

        for key, value in metadata.items():
            if key in LIGHT_METADATA_FIELDS:
                light[key] = value
            elif key in HEAVY_METADATA_FIELDS:
                heavy[key] = value
            else:
                # Unknown field - put in light if small, heavy if large
                value_str = str(value)
                if len(value_str) > 100:
                    heavy[key] = value
                else:
                    light[key] = value

        # Ensure document_id is in both (needed for linking)
        if "document_id" in metadata:
            light["document_id"] = metadata["document_id"]
            heavy["document_id"] = metadata["document_id"]

        return light, heavy

    def store_chunk_details(
        self,
        document_id: str,
        source_type: str,
        heavy_metadata: dict,
    ) -> None:
        """Store heavy metadata for a chunk.

        Args:
            document_id: Unique chunk identifier (links to Qdrant)
            source_type: Document source type
            heavy_metadata: Heavy metadata to store
        """
        now = datetime.now().isoformat()

        # Extract known fields
        file_path = heavy_metadata.pop("file_path", None)
        indexed_at = heavy_metadata.pop("indexed_at", None)
        is_pinned = heavy_metadata.pop("is_pinned", False)
        is_approved = heavy_metadata.pop("is_approved", False)
        heavy_metadata.pop("document_id", None)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chunk_details
                (document_id, source_type, file_path, indexed_at, is_pinned, is_approved, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source_type = excluded.source_type,
                    file_path = excluded.file_path,
                    indexed_at = excluded.indexed_at,
                    is_pinned = excluded.is_pinned,
                    is_approved = excluded.is_approved,
                    metadata_json = excluded.metadata_json
                """,
                (
                    document_id,
                    source_type,
                    file_path,
                    indexed_at,
                    is_pinned,
                    is_approved,
                    json.dumps(heavy_metadata, ensure_ascii=False) if heavy_metadata else None,
                    now,
                ),
            )

    def store_chunk_details_batch(
        self,
        chunks: list[tuple[str, str, dict]],
    ) -> int:
        """Store heavy metadata for multiple chunks efficiently.

        Args:
            chunks: List of (document_id, source_type, heavy_metadata) tuples

        Returns:
            Number of chunks stored
        """
        now = datetime.now().isoformat()
        count = 0

        with self._get_connection() as conn:
            for document_id, source_type, heavy_metadata in chunks:
                heavy = dict(heavy_metadata)  # Copy to avoid mutation
                file_path = heavy.pop("file_path", None)
                indexed_at = heavy.pop("indexed_at", None)
                is_pinned = heavy.pop("is_pinned", False)
                is_approved = heavy.pop("is_approved", False)
                heavy.pop("document_id", None)

                conn.execute(
                    """
                    INSERT INTO chunk_details
                    (document_id, source_type, file_path, indexed_at, is_pinned, is_approved, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(document_id) DO UPDATE SET
                        source_type = excluded.source_type,
                        file_path = excluded.file_path,
                        indexed_at = excluded.indexed_at,
                        is_pinned = excluded.is_pinned,
                        is_approved = excluded.is_approved,
                        metadata_json = excluded.metadata_json
                    """,
                    (
                        document_id,
                        source_type,
                        file_path,
                        indexed_at,
                        is_pinned,
                        is_approved,
                        json.dumps(heavy, ensure_ascii=False) if heavy else None,
                        now,
                    ),
                )
                count += 1

        return count

    def get_chunk_details(self, document_id: str) -> dict | None:
        """Get heavy metadata for a chunk.

        Args:
            document_id: Chunk identifier

        Returns:
            Heavy metadata dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM chunk_details WHERE document_id = ?",
                (document_id,),
            )
            row = cursor.fetchone()

            if row:
                result = {
                    "document_id": row["document_id"],
                    "source_type": row["source_type"],
                    "is_pinned": bool(row["is_pinned"]),
                    "is_approved": bool(row["is_approved"]),
                }
                if row["file_path"]:
                    result["file_path"] = row["file_path"]
                if row["indexed_at"]:
                    result["indexed_at"] = row["indexed_at"]
                if row["metadata_json"]:
                    result.update(json.loads(row["metadata_json"]))
                return result
            return None

    def get_chunk_details_batch(self, document_ids: list[str]) -> dict[str, dict]:
        """Get heavy metadata for multiple chunks.

        Args:
            document_ids: List of chunk identifiers

        Returns:
            Dictionary mapping document_id to heavy metadata
        """
        if not document_ids:
            return {}

        placeholders = ",".join("?" * len(document_ids))

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM chunk_details WHERE document_id IN ({placeholders})",
                document_ids,
            )

            result = {}
            for row in cursor.fetchall():
                details = {
                    "document_id": row["document_id"],
                    "source_type": row["source_type"],
                    "is_pinned": bool(row["is_pinned"]),
                    "is_approved": bool(row["is_approved"]),
                }
                if row["file_path"]:
                    details["file_path"] = row["file_path"]
                if row["indexed_at"]:
                    details["indexed_at"] = row["indexed_at"]
                if row["metadata_json"]:
                    details.update(json.loads(row["metadata_json"]))
                result[row["document_id"]] = details

            return result

    def merge_metadata(
        self,
        light_metadata: dict,
        heavy_metadata: dict | None,
    ) -> dict:
        """Merge light and heavy metadata into complete metadata.

        Args:
            light_metadata: Light metadata from Qdrant
            heavy_metadata: Heavy metadata from chunk_details (or None)

        Returns:
            Complete merged metadata dict
        """
        result = dict(light_metadata)
        if heavy_metadata:
            result.update(heavy_metadata)
        return result

    def update_chunk_pinned(self, document_id: str, is_pinned: bool) -> bool:
        """Update pinned status for a chunk.

        Args:
            document_id: Chunk identifier
            is_pinned: New pinned status

        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE chunk_details SET is_pinned = ? WHERE document_id = ?",
                (is_pinned, document_id),
            )
            return cursor.rowcount > 0

    def update_chunk_approved(self, document_id: str, is_approved: bool) -> bool:
        """Update approved status for a chunk.

        Args:
            document_id: Chunk identifier
            is_approved: New approved status

        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE chunk_details SET is_approved = ? WHERE document_id = ?",
                (is_approved, document_id),
            )
            return cursor.rowcount > 0

    def delete_chunk_details(self, document_id: str) -> bool:
        """Delete heavy metadata for a chunk.

        Args:
            document_id: Chunk identifier

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chunk_details WHERE document_id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0

    def clear_chunk_details(self, source_type: str | None = None) -> int:
        """Clear chunk details, optionally by source type.

        Args:
            source_type: If provided, only clear this source type

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            if source_type:
                cursor = conn.execute(
                    "DELETE FROM chunk_details WHERE source_type = ?",
                    (source_type,),
                )
            else:
                cursor = conn.execute("DELETE FROM chunk_details")
            return cursor.rowcount

    def get_chunk_details_stats(self) -> dict:
        """Get chunk details statistics.

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM chunk_details")
            total = cursor.fetchone()["total"]

            cursor = conn.execute(
                "SELECT source_type, COUNT(*) as count FROM chunk_details GROUP BY source_type"
            )
            by_source = {row["source_type"]: row["count"] for row in cursor.fetchall()}

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM chunk_details WHERE is_pinned = TRUE"
            )
            pinned = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM chunk_details WHERE is_approved = TRUE"
            )
            approved = cursor.fetchone()["count"]

            return {
                "total_chunks": total,
                "by_source": by_source,
                "pinned_count": pinned,
                "approved_count": approved,
            }
