"""SQLite-based chat history storage."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal

from pydantic import BaseModel

from src.config import settings


class Message(BaseModel):
    """A single chat message."""

    id: int | None = None
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    sources: list[dict] | None = None
    timestamp: datetime


class Conversation(BaseModel):
    """A chat conversation."""

    id: int | None = None
    title: str
    created_at: datetime
    updated_at: datetime


class ChatHistory:
    """Manages chat history persistence using SQLite."""

    def __init__(self, db_path: Path | None = None):
        """Initialize chat history storage.

        Args:
            db_path: Path to SQLite database file. If None, uses settings.
        """
        self.db_path = db_path or settings.db_path
        self._ensure_tables()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        # Ensure directory exists
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
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id)
            """)

    def create_conversation(self, title: str | None = None) -> Conversation:
        """Create a new conversation.

        Args:
            title: Conversation title. If None, uses timestamp.

        Returns:
            Created conversation object
        """
        now = datetime.now()
        title = title or f"Conversation {now.strftime('%Y-%m-%d %H:%M')}"

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (title, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (title, now.isoformat(), now.isoformat()),
            )

            return Conversation(
                id=cursor.lastrowid,
                title=title,
                created_at=now,
                updated_at=now,
            )

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """List recent conversations.

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversations, most recent first
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [
                Conversation(
                    id=row["id"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    def get_conversation(self, conversation_id: int) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: ID of the conversation

        Returns:
            Conversation object or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

            if not row:
                return None

            return Conversation(
                id=row["id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and its messages.

        Args:
            conversation_id: ID of the conversation to delete

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            # Messages are deleted automatically due to ON DELETE CASCADE
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            return cursor.rowcount > 0

    def update_conversation_title(
        self, conversation_id: int, title: str
    ) -> bool:
        """Update conversation title.

        Args:
            conversation_id: ID of the conversation
            title: New title

        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, datetime.now().isoformat(), conversation_id),
            )
            return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id: int,
        role: Literal["user", "assistant"],
        content: str,
        sources: list[dict] | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: ID of the conversation
            role: Message role ("user" or "assistant")
            content: Message content
            sources: Optional list of source metadata

        Returns:
            Created message object
        """
        now = datetime.now()
        sources_json = json.dumps(sources) if sources else None

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, sources, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, sources_json, now.isoformat()),
            )

            # Update conversation timestamp
            conn.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE id = ?
                """,
                (now.isoformat(), conversation_id),
            )

            return Message(
                id=cursor.lastrowid,
                conversation_id=conversation_id,
                role=role,
                content=content,
                sources=sources,
                timestamp=now,
            )

    def get_messages(self, conversation_id: int) -> list[Message]:
        """Get all messages in a conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            List of messages in chronological order
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, sources, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                """,
                (conversation_id,),
            ).fetchall()

            return [
                Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    sources=json.loads(row["sources"]) if row["sources"] else None,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                for row in rows
            ]

    def get_recent_messages(
        self, conversation_id: int, limit: int = 10
    ) -> list[Message]:
        """Get recent messages for context.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages

        Returns:
            List of recent messages
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, sources, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

            messages = [
                Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    sources=json.loads(row["sources"]) if row["sources"] else None,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                for row in rows
            ]

            # Return in chronological order
            return list(reversed(messages))

    # =========================================
    # FR-P0-5: Forget / Right to Be Forgotten
    # =========================================

    def purge_by_document(self, document_id: str) -> int:
        """Remove all references to a deleted document from chat history.

        This removes the document from the 'sources' field of messages
        that cited it, but does NOT delete the messages themselves.

        Args:
            document_id: ID of the deleted document

        Returns:
            Number of messages updated
        """
        with self._get_connection() as conn:
            # Find messages with sources containing this document
            rows = conn.execute(
                "SELECT id, sources FROM messages WHERE sources IS NOT NULL"
            ).fetchall()

            updated = 0
            for row in rows:
                sources = json.loads(row["sources"]) if row["sources"] else []

                # Filter out the deleted document
                new_sources = [
                    s for s in sources
                    if s.get("metadata", {}).get("document_id") != document_id
                ]

                # Update if sources changed
                if len(new_sources) != len(sources):
                    conn.execute(
                        "UPDATE messages SET sources = ? WHERE id = ?",
                        (
                            json.dumps(new_sources) if new_sources else None,
                            row["id"],
                        ),
                    )
                    updated += 1

            return updated

    def purge_by_entity(self, entity_type: str, entity_value: str) -> int:
        """Remove references to an entity from chat history.

        This removes sources that match the entity from message sources.

        Args:
            entity_type: Type of entity (sender, source_type, etc.)
            entity_value: Value to match

        Returns:
            Number of messages updated
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, sources FROM messages WHERE sources IS NOT NULL"
            ).fetchall()

            updated = 0
            for row in rows:
                sources = json.loads(row["sources"]) if row["sources"] else []

                # Filter out matching sources
                new_sources = [
                    s for s in sources
                    if s.get("metadata", {}).get(entity_type) != entity_value
                ]

                if len(new_sources) != len(sources):
                    conn.execute(
                        "UPDATE messages SET sources = ? WHERE id = ?",
                        (
                            json.dumps(new_sources) if new_sources else None,
                            row["id"],
                        ),
                    )
                    updated += 1

            return updated

    def purge_messages_containing(self, text_pattern: str) -> int:
        """Delete messages containing specific text pattern.

        WARNING: This is more aggressive - deletes entire messages.

        Args:
            text_pattern: Text pattern to match

        Returns:
            Number of messages deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE content LIKE ?",
                (f"%{text_pattern}%",),
            )
            return cursor.rowcount
