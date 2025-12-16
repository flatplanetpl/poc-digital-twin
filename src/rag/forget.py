"""Forget / Right to Be Forgotten service.

FR-P0-5: System MUST enable permanent deletion of data from:
- Metadata (document registry)
- Vector index (Qdrant)
- Chat memory (conversation history)

This service orchestrates deletion across all storage systems
to ensure complete data removal for GDPR/RTBF compliance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from src.indexer import VectorStore
from src.storage import ChatHistory
from src.storage.document_registry import DocumentRegistry
from src.storage.audit import AuditLogger, OperationType, EntityType


@dataclass
class ForgetResult:
    """Result of a forget operation."""

    success: bool = False
    error: str | None = None

    # What was deleted
    document_id: str | None = None
    entity_type: str | None = None
    entity_value: str | None = None

    # Deletion counts
    vectors_deleted: int = 0
    chat_references_removed: int = 0
    registry_updated: bool = False

    # Audit
    audit_id: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "error": self.error,
            "document_id": self.document_id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "vectors_deleted": self.vectors_deleted,
            "chat_references_removed": self.chat_references_removed,
            "registry_updated": self.registry_updated,
            "audit_id": self.audit_id,
        }


class ForgetService:
    """Orchestrates data deletion across all storage systems.

    Ensures complete removal of data for RTBF compliance by:
    1. Deleting from vector store (Qdrant)
    2. Purging references from chat history
    3. Updating document registry
    4. Logging deletion in audit trail
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        chat_history: ChatHistory | None = None,
        document_registry: DocumentRegistry | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        """Initialize forget service.

        Args:
            vector_store: Vector store instance
            chat_history: Chat history instance
            document_registry: Document registry instance
            audit_logger: Audit logger instance
        """
        self.vector_store = vector_store or VectorStore()
        self.chat_history = chat_history or ChatHistory()
        self.document_registry = document_registry or DocumentRegistry()
        self.audit_logger = audit_logger or AuditLogger()

    def forget_document(self, document_id: str, reason: str = "user_request") -> ForgetResult:
        """Completely remove a document from all systems.

        This is the primary method for RTBF compliance. It:
        1. Deletes all vector chunks for this document
        2. Removes references from chat history
        3. Marks document as deleted in registry
        4. Logs the deletion in audit trail

        Args:
            document_id: UUID of document to delete
            reason: Reason for deletion (for audit)

        Returns:
            ForgetResult with deletion counts
        """
        result = ForgetResult(document_id=document_id)

        try:
            # 1. Delete from vector store
            if self.vector_store.delete_document(document_id):
                # Count is approximate since delete_document returns bool
                result.vectors_deleted = 1  # At least 1 chunk deleted

            # 2. Purge from chat history
            result.chat_references_removed = self.chat_history.purge_by_document(
                document_id
            )

            # 3. Mark as deleted in registry
            if self.document_registry.mark_deleted(document_id):
                result.registry_updated = True

            # 4. Log deletion in audit trail
            result.audit_id = self.audit_logger.log_delete(
                document_id=document_id,
                reason=reason,
                chunks_deleted=result.vectors_deleted,
            )

            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False

        return result

    def forget_by_file_path(self, file_path: str, reason: str = "user_request") -> ForgetResult:
        """Remove all data from a specific source file.

        Args:
            file_path: Absolute path to source file
            reason: Reason for deletion

        Returns:
            ForgetResult with deletion counts
        """
        result = ForgetResult(entity_type="file_path", entity_value=file_path)

        try:
            # Find document by file path
            doc = self.document_registry.get_by_file_path(file_path)
            if doc:
                return self.forget_document(doc.id, reason=reason)

            # If not in registry, try direct deletion from vector store
            result.vectors_deleted = self.vector_store.delete_by_file_path(file_path)

            # Log deletion
            result.audit_id = self.audit_logger.log(
                operation=OperationType.DELETE,
                entity_type=EntityType.DOCUMENT,
                details={
                    "file_path": file_path,
                    "reason": reason,
                    "chunks_deleted": result.vectors_deleted,
                },
            )

            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False

        return result

    def forget_sender(self, sender: str, reason: str = "user_request") -> ForgetResult:
        """Remove all content from a specific sender.

        Useful for removing all emails/messages from a specific person.

        Args:
            sender: Sender name or email
            reason: Reason for deletion

        Returns:
            ForgetResult with deletion counts
        """
        result = ForgetResult(entity_type="sender", entity_value=sender)

        try:
            # 1. Delete from vector store
            result.vectors_deleted = self.vector_store.delete_by_sender(sender)

            # 2. Purge from chat history
            result.chat_references_removed = self.chat_history.purge_by_entity(
                "sender", sender
            )

            # 3. Log deletion
            result.audit_id = self.audit_logger.log(
                operation=OperationType.DELETE,
                entity_type=EntityType.DOCUMENT,
                details={
                    "entity_type": "sender",
                    "entity_value": sender,
                    "reason": reason,
                    "chunks_deleted": result.vectors_deleted,
                },
            )

            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False

        return result

    def forget_by_source_type(
        self, source_type: str, reason: str = "user_request"
    ) -> ForgetResult:
        """Remove all content of a specific source type.

        Args:
            source_type: Type to delete (email, whatsapp, etc.)
            reason: Reason for deletion

        Returns:
            ForgetResult with deletion counts
        """
        result = ForgetResult(entity_type="source_type", entity_value=source_type)

        try:
            # Delete from vector store
            result.vectors_deleted = self.vector_store.delete_by_filter(
                {"source_type": source_type}
            )

            # Log deletion
            result.audit_id = self.audit_logger.log(
                operation=OperationType.DELETE,
                entity_type=EntityType.DOCUMENT,
                details={
                    "entity_type": "source_type",
                    "entity_value": source_type,
                    "reason": reason,
                    "chunks_deleted": result.vectors_deleted,
                },
            )

            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False

        return result

    def get_deletion_report(self, days: int = 30) -> dict:
        """Get report of recent deletions.

        Args:
            days: Number of days to include in report

        Returns:
            Dict with deletion statistics
        """
        return self.audit_logger.get_deletion_report()

    def list_deletable_documents(
        self, source_type: str | None = None, limit: int = 100
    ) -> list[dict]:
        """List documents that can be deleted.

        Args:
            source_type: Filter by source type
            limit: Maximum documents to return

        Returns:
            List of document info dicts
        """
        from src.storage.document_registry import DocumentStatus

        docs = self.document_registry.list_documents(
            status=DocumentStatus.ACTIVE,
            source_type=source_type,
            limit=limit,
        )

        return [
            {
                "id": doc.id,
                "filename": doc.file_path.split("/")[-1],
                "file_path": doc.file_path,
                "source_type": doc.source_type,
                "indexed_at": doc.last_indexed_at.isoformat(),
            }
            for doc in docs
        ]
