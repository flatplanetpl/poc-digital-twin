"""SQLite-based contact registry for tracking relationships."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.config import settings


@dataclass
class Contact:
    """Represents a contact in the registry."""

    id: int | None = None
    name: str = ""
    normalized_name: str = ""
    source: str = ""  # messenger, whatsapp, email, facebook_friends
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    message_count: int = 0
    call_count: int = 0
    relationship_type: str | None = None  # family, friend, coworker
    is_hidden: bool = False
    metadata: dict | None = None


@dataclass
class ContactInteraction:
    """Monthly aggregation of contact interactions."""

    contact_id: int
    year_month: str  # "2024-01"
    message_count: int = 0
    call_count: int = 0


class ContactRegistry:
    """Manages contact tracking and relationship statistics using SQLite."""

    def __init__(self, db_path: Path | None = None):
        """Initialize contact registry.

        Args:
            db_path: Path to SQLite database file. If None, uses settings.
        """
        self.db_path = db_path or settings.db_path
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
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    first_seen TEXT,
                    last_seen TEXT,
                    message_count INTEGER DEFAULT 0,
                    call_count INTEGER DEFAULT 0,
                    relationship_type TEXT,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_normalized_source
                ON contacts(normalized_name, source)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_contacts_name
                ON contacts(name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_contacts_relationship
                ON contacts(relationship_type)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS contact_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL,
                    year_month TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    call_count INTEGER DEFAULT 0,
                    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
                    UNIQUE(contact_id, year_month)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_contact
                ON contact_interactions(contact_id)
            """)

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize contact name for matching.

        Args:
            name: Original name

        Returns:
            Lowercase, stripped name
        """
        return name.lower().strip()

    def register_contact(
        self,
        name: str,
        source: str,
        timestamp: datetime | None = None,
        relationship_type: str | None = None,
        metadata: dict | None = None,
    ) -> Contact:
        """Register or update a contact.

        Args:
            name: Contact name
            source: Data source (messenger, whatsapp, email, facebook_friends)
            timestamp: Interaction timestamp
            relationship_type: Type of relationship (family, friend, coworker)
            metadata: Additional metadata

        Returns:
            Created or updated Contact object
        """
        normalized = self.normalize_name(name)
        now = datetime.now().isoformat()
        ts = timestamp.isoformat() if timestamp else now

        with self._get_connection() as conn:
            # Try to find existing contact
            cursor = conn.execute(
                """
                SELECT id, first_seen, message_count, call_count, metadata
                FROM contacts
                WHERE normalized_name = ? AND source = ?
                """,
                (normalized, source),
            )
            row = cursor.fetchone()

            if row:
                # Update existing contact
                existing_metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                if metadata:
                    existing_metadata.update(metadata)

                conn.execute(
                    """
                    UPDATE contacts
                    SET last_seen = ?,
                        relationship_type = COALESCE(?, relationship_type),
                        metadata = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        ts,
                        relationship_type,
                        json.dumps(existing_metadata) if existing_metadata else None,
                        now,
                        row["id"],
                    ),
                )

                return Contact(
                    id=row["id"],
                    name=name,
                    normalized_name=normalized,
                    source=source,
                    first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
                    last_seen=datetime.fromisoformat(ts),
                    message_count=row["message_count"],
                    call_count=row["call_count"],
                    relationship_type=relationship_type,
                    metadata=existing_metadata,
                )
            else:
                # Insert new contact
                cursor = conn.execute(
                    """
                    INSERT INTO contacts
                    (name, normalized_name, source, first_seen, last_seen,
                     relationship_type, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        normalized,
                        source,
                        ts,
                        ts,
                        relationship_type,
                        json.dumps(metadata) if metadata else None,
                        now,
                        now,
                    ),
                )

                return Contact(
                    id=cursor.lastrowid,
                    name=name,
                    normalized_name=normalized,
                    source=source,
                    first_seen=datetime.fromisoformat(ts),
                    last_seen=datetime.fromisoformat(ts),
                    relationship_type=relationship_type,
                    metadata=metadata,
                )

    def update_stats(
        self,
        name: str,
        source: str,
        message_count: int = 0,
        call_count: int = 0,
        timestamp: datetime | None = None,
    ) -> None:
        """Update contact statistics.

        Args:
            name: Contact name
            source: Data source
            message_count: Number of messages to add
            call_count: Number of calls to add
            timestamp: Interaction timestamp for monthly aggregation
        """
        normalized = self.normalize_name(name)
        now = datetime.now()
        ts = timestamp or now
        year_month = ts.strftime("%Y-%m")

        with self._get_connection() as conn:
            # Update total counts
            conn.execute(
                """
                UPDATE contacts
                SET message_count = message_count + ?,
                    call_count = call_count + ?,
                    last_seen = ?,
                    updated_at = ?
                WHERE normalized_name = ? AND source = ?
                """,
                (
                    message_count,
                    call_count,
                    ts.isoformat(),
                    now.isoformat(),
                    normalized,
                    source,
                ),
            )

            # Get contact ID for interaction tracking
            cursor = conn.execute(
                "SELECT id FROM contacts WHERE normalized_name = ? AND source = ?",
                (normalized, source),
            )
            row = cursor.fetchone()

            if row and (message_count > 0 or call_count > 0):
                # Update monthly aggregation
                conn.execute(
                    """
                    INSERT INTO contact_interactions (contact_id, year_month, message_count, call_count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(contact_id, year_month) DO UPDATE SET
                        message_count = message_count + excluded.message_count,
                        call_count = call_count + excluded.call_count
                    """,
                    (row["id"], year_month, message_count, call_count),
                )

    def get_contact(self, name: str, source: str | None = None) -> Contact | None:
        """Get contact by name.

        Args:
            name: Contact name (fuzzy matched via normalized_name)
            source: Optional source filter

        Returns:
            Contact object or None if not found
        """
        normalized = self.normalize_name(name)

        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "SELECT * FROM contacts WHERE normalized_name = ? AND source = ?",
                    (normalized, source),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM contacts WHERE normalized_name = ? ORDER BY message_count DESC LIMIT 1",
                    (normalized,),
                )

            row = cursor.fetchone()
            if row:
                return self._row_to_contact(row)
            return None

    def get_contact_by_id(self, contact_id: int) -> Contact | None:
        """Get contact by ID.

        Args:
            contact_id: Contact ID

        Returns:
            Contact object or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_contact(row)
            return None

    def get_top_contacts(
        self,
        limit: int = 20,
        source: str | None = None,
        exclude_hidden: bool = True,
    ) -> list[Contact]:
        """Get most frequent contacts.

        Args:
            limit: Maximum number of contacts to return
            source: Optional source filter
            exclude_hidden: Whether to exclude hidden contacts

        Returns:
            List of Contact objects sorted by message count
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM contacts WHERE 1=1"
            params = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if exclude_hidden:
                query += " AND is_hidden = FALSE"

            query += " ORDER BY message_count DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            return [self._row_to_contact(row) for row in cursor.fetchall()]

    def search_contacts(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Contact]:
        """Search contacts by name.

        Args:
            query: Search query (partial name match)
            limit: Maximum number of results

        Returns:
            List of matching contacts
        """
        normalized = self.normalize_name(query)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM contacts
                WHERE normalized_name LIKE ?
                ORDER BY message_count DESC
                LIMIT ?
                """,
                (f"%{normalized}%", limit),
            )
            return [self._row_to_contact(row) for row in cursor.fetchall()]

    def get_contacts_by_relationship(
        self,
        relationship_type: str,
        limit: int | None = None,
    ) -> list[Contact]:
        """Get contacts by relationship type.

        Args:
            relationship_type: Type of relationship (family, friend, coworker)
            limit: Optional maximum number of results

        Returns:
            List of contacts with the specified relationship
        """
        with self._get_connection() as conn:
            query = """
                SELECT * FROM contacts
                WHERE relationship_type = ?
                ORDER BY message_count DESC
            """
            params = [relationship_type]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            return [self._row_to_contact(row) for row in cursor.fetchall()]

    def get_interaction_history(
        self,
        contact_id: int,
        months: int = 12,
    ) -> list[ContactInteraction]:
        """Get monthly interaction history for a contact.

        Args:
            contact_id: Contact ID
            months: Number of months of history to retrieve

        Returns:
            List of monthly interaction records
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM contact_interactions
                WHERE contact_id = ?
                ORDER BY year_month DESC
                LIMIT ?
                """,
                (contact_id, months),
            )

            return [
                ContactInteraction(
                    contact_id=row["contact_id"],
                    year_month=row["year_month"],
                    message_count=row["message_count"],
                    call_count=row["call_count"],
                )
                for row in cursor.fetchall()
            ]

    def hide_contact(self, name: str, source: str | None = None) -> bool:
        """Hide a contact from queries.

        Args:
            name: Contact name
            source: Optional source filter

        Returns:
            True if contact was hidden, False if not found
        """
        normalized = self.normalize_name(name)

        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "UPDATE contacts SET is_hidden = TRUE WHERE normalized_name = ? AND source = ?",
                    (normalized, source),
                )
            else:
                cursor = conn.execute(
                    "UPDATE contacts SET is_hidden = TRUE WHERE normalized_name = ?",
                    (normalized,),
                )
            return cursor.rowcount > 0

    def delete_contact(self, name: str, source: str | None = None) -> int:
        """Delete a contact and all interactions.

        Args:
            name: Contact name
            source: Optional source filter

        Returns:
            Number of contacts deleted
        """
        normalized = self.normalize_name(name)

        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "DELETE FROM contacts WHERE normalized_name = ? AND source = ?",
                    (normalized, source),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM contacts WHERE normalized_name = ?",
                    (normalized,),
                )
            return cursor.rowcount

    def get_all_contacts(
        self,
        source: str | None = None,
        exclude_hidden: bool = True,
    ) -> list[Contact]:
        """Get all contacts.

        Args:
            source: Optional source filter
            exclude_hidden: Whether to exclude hidden contacts

        Returns:
            List of all contacts
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM contacts WHERE 1=1"
            params = []

            if source:
                query += " AND source = ?"
                params.append(source)

            if exclude_hidden:
                query += " AND is_hidden = FALSE"

            query += " ORDER BY name"

            cursor = conn.execute(query, params)
            return [self._row_to_contact(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Get contact registry statistics.

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM contacts")
            total = cursor.fetchone()["total"]

            cursor = conn.execute(
                "SELECT source, COUNT(*) as count FROM contacts GROUP BY source"
            )
            by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

            cursor = conn.execute("SELECT SUM(message_count) as total FROM contacts")
            total_messages = cursor.fetchone()["total"] or 0

            return {
                "total_contacts": total,
                "by_source": by_source,
                "total_messages": total_messages,
            }

    def _row_to_contact(self, row: sqlite3.Row) -> Contact:
        """Convert database row to Contact object.

        Args:
            row: SQLite row

        Returns:
            Contact object
        """
        return Contact(
            id=row["id"],
            name=row["name"],
            normalized_name=row["normalized_name"],
            source=row["source"],
            first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
            message_count=row["message_count"],
            call_count=row["call_count"],
            relationship_type=row["relationship_type"],
            is_hidden=bool(row["is_hidden"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )
