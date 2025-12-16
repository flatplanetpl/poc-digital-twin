"""Privacy-safe audit logging for Digital Twin.

Provides operation logging for compliance and debugging while
maintaining strict privacy guarantees:
- Logs document IDs and operation types
- NEVER logs content or sensitive data
- Supports GDPR/RTBF audit requirements

FR-P3-3: Audit Log (privacy-safe)
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from src.config import settings


class OperationType(str, Enum):
    """Types of auditable operations."""

    # Document operations
    INDEX = "index"
    DELETE = "delete"
    ARCHIVE = "archive"
    UPDATE = "update"

    # Query operations
    QUERY = "query"
    SEARCH = "search"

    # System operations
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"

    # Policy operations
    POLICY_CREATE = "policy_create"
    POLICY_APPLY = "policy_apply"
    POLICY_DELETE = "policy_delete"


class EntityType(str, Enum):
    """Types of entities being audited."""

    DOCUMENT = "document"
    COLLECTION = "collection"
    CONVERSATION = "conversation"
    POLICY = "policy"
    BACKUP = "backup"
    PROFILE = "profile"


class AuditEntry(BaseModel):
    """A single audit log entry."""

    id: int | None = None
    timestamp: datetime
    operation: OperationType
    entity_type: EntityType
    entity_id: str | None = None
    details: dict = Field(default_factory=dict)
    session_id: str | None = None


class AuditLogger:
    """Privacy-safe audit logging system.

    IMPORTANT: This logger NEVER stores content. Only metadata
    like document IDs, operation types, and counts are logged.

    Example usage:
        audit = AuditLogger()
        audit.log(
            operation=OperationType.INDEX,
            entity_type=EntityType.DOCUMENT,
            entity_id="doc-uuid-123",
            details={"source_type": "email", "chunk_count": 5}
        )
    """

    def __init__(self, db_path: Path | None = None, enabled: bool | None = None):
        """Initialize audit logger.

        Args:
            db_path: Path to SQLite database. If None, uses default.
            enabled: Whether logging is enabled. If None, uses settings.
        """
        self.db_path = db_path or settings.storage_dir / "audit.db"
        self.enabled = enabled if enabled is not None else getattr(
            settings, "audit_enabled", True
        )
        if self.enabled:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details TEXT,
                    session_id TEXT
                )
            """)

            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_operation
                ON audit_log(operation)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_entity
                ON audit_log(entity_type, entity_id)
            """)

    def log(
        self,
        operation: OperationType,
        entity_type: EntityType,
        entity_id: str | None = None,
        details: dict | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """Log an operation.

        IMPORTANT: `details` must NEVER contain document content.
        Only metadata like counts, timestamps, source types are allowed.

        Args:
            operation: Type of operation performed
            entity_type: Type of entity affected
            entity_id: ID of the entity (document_id, conversation_id, etc.)
            details: Additional metadata (NO CONTENT!)
            session_id: Optional session identifier

        Returns:
            Audit entry ID, or None if logging is disabled

        Raises:
            ValueError: If details appears to contain content
        """
        if not self.enabled:
            return None

        # Safety check: prevent accidental content logging
        if details:
            self._validate_no_content(details)

        now = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log (
                    timestamp, operation, entity_type, entity_id, details, session_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    now.isoformat(),
                    operation.value,
                    entity_type.value,
                    entity_id,
                    json.dumps(details) if details else None,
                    session_id,
                ),
            )
            return cursor.lastrowid

    def _validate_no_content(self, details: dict) -> None:
        """Validate that details don't contain content.

        Args:
            details: Dict to validate

        Raises:
            ValueError: If content-like fields are detected
        """
        forbidden_keys = {"content", "text", "body", "message", "query_text", "answer"}
        found = forbidden_keys.intersection(details.keys())
        if found:
            raise ValueError(
                f"Audit details must not contain content. "
                f"Found forbidden keys: {found}. "
                f"Remove these fields or use safe alternatives like 'content_length'."
            )

        # Check for suspiciously long strings (likely content)
        for key, value in details.items():
            if isinstance(value, str) and len(value) > 500:
                raise ValueError(
                    f"Audit detail '{key}' is suspiciously long ({len(value)} chars). "
                    f"This might be content. Use a hash or length instead."
                )

    def log_index(
        self,
        document_id: str,
        source_type: str,
        chunk_count: int,
        file_path: str | None = None,
    ) -> int | None:
        """Log document indexing operation.

        Args:
            document_id: UUID of indexed document
            source_type: Type of document (email, text, etc.)
            chunk_count: Number of chunks created
            file_path: Path to source file (stored for reference)

        Returns:
            Audit entry ID
        """
        return self.log(
            operation=OperationType.INDEX,
            entity_type=EntityType.DOCUMENT,
            entity_id=document_id,
            details={
                "source_type": source_type,
                "chunk_count": chunk_count,
                "file_name": Path(file_path).name if file_path else None,
            },
        )

    def log_delete(
        self,
        document_id: str,
        reason: str,
        chunks_deleted: int = 0,
    ) -> int | None:
        """Log document deletion operation.

        Args:
            document_id: UUID of deleted document
            reason: Reason for deletion (user_request, retention_policy, etc.)
            chunks_deleted: Number of vector chunks removed

        Returns:
            Audit entry ID
        """
        return self.log(
            operation=OperationType.DELETE,
            entity_type=EntityType.DOCUMENT,
            entity_id=document_id,
            details={
                "reason": reason,
                "chunks_deleted": chunks_deleted,
            },
        )

    def log_query(
        self,
        result_count: int,
        mode: str = "search",
        filters_used: list[str] | None = None,
    ) -> int | None:
        """Log query operation (without query text!).

        Args:
            result_count: Number of results returned
            mode: Query mode (search, recall, decision, etc.)
            filters_used: Names of filters applied

        Returns:
            Audit entry ID
        """
        # Check if query logging is enabled
        if not getattr(settings, "audit_queries", False):
            return None

        return self.log(
            operation=OperationType.QUERY,
            entity_type=EntityType.COLLECTION,
            details={
                "result_count": result_count,
                "mode": mode,
                "filters_used": filters_used or [],
            },
        )

    def log_backup(
        self,
        backup_id: str,
        operation: OperationType,
        document_count: int,
        backup_path: str | None = None,
    ) -> int | None:
        """Log backup/restore operation.

        Args:
            backup_id: Identifier for the backup
            operation: BACKUP or RESTORE
            document_count: Number of documents in backup
            backup_path: Path to backup (filename only for privacy)

        Returns:
            Audit entry ID
        """
        return self.log(
            operation=operation,
            entity_type=EntityType.BACKUP,
            entity_id=backup_id,
            details={
                "document_count": document_count,
                "backup_name": Path(backup_path).name if backup_path else None,
            },
        )

    def query_log(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        operation: OperationType | None = None,
        entity_type: EntityType | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit log with filters.

        Args:
            start_date: Filter entries after this date
            end_date: Filter entries before this date
            operation: Filter by operation type
            entity_type: Filter by entity type
            entity_id: Filter by specific entity
            limit: Maximum entries to return

        Returns:
            List of AuditEntry objects
        """
        if not self.enabled:
            return []

        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        if operation:
            query += " AND operation = ?"
            params.append(operation.value)

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type.value)

        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def get_document_history(self, document_id: str) -> list[AuditEntry]:
        """Get all audit entries for a specific document.

        Args:
            document_id: Document UUID

        Returns:
            List of AuditEntry objects for this document
        """
        return self.query_log(
            entity_type=EntityType.DOCUMENT,
            entity_id=document_id,
            limit=1000,
        )

    def get_deletion_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Generate deletion audit report.

        Args:
            start_date: Report start date (default: 30 days ago)
            end_date: Report end date (default: now)

        Returns:
            Dict with deletion statistics
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        deletions = self.query_log(
            start_date=start_date,
            end_date=end_date,
            operation=OperationType.DELETE,
            limit=10000,
        )

        by_reason: dict[str, int] = {}
        total_chunks = 0

        for entry in deletions:
            reason = entry.details.get("reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1
            total_chunks += entry.details.get("chunks_deleted", 0)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_deletions": len(deletions),
            "total_chunks_deleted": total_chunks,
            "by_reason": by_reason,
        }

    def export_log(
        self,
        output_path: Path,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Export audit log to JSON file.

        Args:
            output_path: Path for output file
            start_date: Export entries after this date
            end_date: Export entries before this date

        Returns:
            Number of entries exported
        """
        entries = self.query_log(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "entry_count": len(entries),
            "entries": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "operation": e.operation.value,
                    "entity_type": e.entity_type.value,
                    "entity_id": e.entity_id,
                    "details": e.details,
                    "session_id": e.session_id,
                }
                for e in entries
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        return len(entries)

    def cleanup_old_entries(self, days_to_keep: int = 365) -> int:
        """Remove audit entries older than specified days.

        Args:
            days_to_keep: Keep entries from last N days

        Returns:
            Number of entries deleted
        """
        if not self.enabled:
            return 0

        cutoff = datetime.now() - timedelta(days=days_to_keep)

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM audit_log WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            return cursor.rowcount

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        """Convert database row to AuditEntry."""
        return AuditEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            operation=OperationType(row["operation"]),
            entity_type=EntityType(row["entity_type"]),
            entity_id=row["entity_id"],
            details=json.loads(row["details"]) if row["details"] else {},
            session_id=row["session_id"],
        )
