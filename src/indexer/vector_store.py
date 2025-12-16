"""Qdrant vector store integration.

FR-P0-3: Source of Truth & Priority Rules - priority-weighted search
FR-P0-5: Forget / Right to Be Forgotten - per-document deletion
"""

from llama_index.core import Settings as LlamaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.config import settings


class VectorStore:
    """Manages document indexing and retrieval using Qdrant."""

    def __init__(self):
        """Initialize vector store with Qdrant client."""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.collection_name = settings.qdrant_collection

        # Configure embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.embedding_model
        )
        LlamaSettings.embed_model = self.embed_model

        # Configure text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        LlamaSettings.text_splitter = self.text_splitter

        self._vector_store = None
        self._index = None

    @property
    def vector_store(self) -> QdrantVectorStore:
        """Get or create Qdrant vector store."""
        if self._vector_store is None:
            self._vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
            )
        return self._vector_store

    @property
    def index(self) -> VectorStoreIndex:
        """Get or create vector store index."""
        if self._index is None:
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=storage_context,
            )
        return self._index

    def add_documents(self, documents: list[Document]) -> int:
        """Add documents to the vector store.

        Args:
            documents: List of LlamaIndex Document objects

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        # Create index from documents (this also adds them to Qdrant)
        storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        self._index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
        )

        return len(documents)

    def collection_exists(self) -> bool:
        """Check if the collection exists in Qdrant."""
        try:
            self.client.get_collection(self.collection_name)
            return True
        except UnexpectedResponse:
            return False

    def delete_collection(self) -> bool:
        """Delete the entire collection.

        Returns:
            True if deleted, False if didn't exist
        """
        if self.collection_exists():
            self.client.delete_collection(self.collection_name)
            self._vector_store = None
            self._index = None
            return True
        return False

    def get_stats(self) -> dict:
        """Get collection statistics.

        Returns:
            Dictionary with collection stats
        """
        if not self.collection_exists():
            return {"exists": False, "points_count": 0}

        info = self.client.get_collection(self.collection_name)
        return {
            "exists": True,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value,
        }

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search for similar documents.

        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)
            filters: Metadata filters (e.g., {"source_type": "email"})

        Returns:
            List of search results with content and metadata
        """
        top_k = top_k or settings.top_k

        # Build retriever with optional filters
        retriever = self.index.as_retriever(
            similarity_top_k=top_k,
        )

        # Retrieve nodes
        nodes = retriever.retrieve(query)

        results = []
        for node in nodes:
            # Apply metadata filters if provided
            if filters:
                match = all(
                    node.metadata.get(k) == v for k, v in filters.items()
                )
                if not match:
                    continue

            results.append({
                "content": node.text,
                "metadata": node.metadata,
                "score": node.score,
            })

        return results

    def search_with_priority(
        self,
        query: str,
        top_k: int | None = None,
        fetch_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search with priority-weighted re-ranking.

        FR-P0-3: Implements priority-based document weighting.
        Fetches more candidates than needed, then re-ranks by
        combined similarity + priority score.

        Args:
            query: Search query text
            top_k: Number of final results to return
            fetch_k: Number of candidates to fetch before re-ranking
            filters: Metadata filters

        Returns:
            List of search results with priority scores
        """
        # Import here to avoid circular dependency
        from src.rag.priority import rank_documents

        top_k = top_k or settings.top_k
        fetch_k = fetch_k or top_k * 3  # Fetch 3x for better re-ranking

        # Fetch more candidates
        candidates = self.search(query, top_k=fetch_k, filters=filters)

        # Re-rank by priority-weighted score
        ranked = rank_documents(candidates)

        # Convert back to dict format and take top_k
        results = []
        for doc in ranked[:top_k]:
            results.append({
                "content": doc.content,
                "metadata": doc.metadata,
                "score": doc.similarity_score,
                "priority": doc.priority.to_dict(),
                "weighted_score": doc.weighted_score,
            })

        return results

    # =========================================
    # FR-P0-5: Forget / Right to Be Forgotten
    # =========================================

    def delete_document(self, document_id: str) -> bool:
        """Delete a specific document and all its chunks.

        FR-P0-5: Enables per-document deletion for RTBF compliance.

        Args:
            document_id: The unique document ID from metadata

        Returns:
            True if deleted, False if not found or error
        """
        if not self.collection_exists():
            return False

        try:
            # Delete all points with matching document_id
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )
            return True
        except Exception:
            return False

    def delete_by_filter(self, filters: dict) -> int:
        """Delete documents matching metadata filters.

        FR-P0-5: Enables bulk deletion by metadata criteria.

        Args:
            filters: Dict of metadata field -> value to match

        Returns:
            Number of points deleted (approximate)
        """
        if not self.collection_exists():
            return 0

        # Get count before deletion
        before_count = self.get_stats().get("points_count", 0)

        # Build filter conditions
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in filters.items()
        ]

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=conditions),
            )

            # Get count after deletion
            after_count = self.get_stats().get("points_count", 0)
            return before_count - after_count
        except Exception:
            return 0

    def delete_by_file_path(self, file_path: str) -> int:
        """Delete all chunks from a specific source file.

        Args:
            file_path: Absolute path to source file

        Returns:
            Number of points deleted
        """
        return self.delete_by_filter({"file_path": file_path})

    def delete_by_sender(self, sender: str) -> int:
        """Delete all content from a specific sender.

        Args:
            sender: Sender name or email

        Returns:
            Number of points deleted
        """
        return self.delete_by_filter({"sender": sender})

    def update_metadata(self, document_id: str, updates: dict) -> bool:
        """Update metadata for a document.

        Useful for changing is_pinned, is_approved status.

        Args:
            document_id: The unique document ID
            updates: Dict of metadata fields to update

        Returns:
            True if updated, False if error
        """
        if not self.collection_exists():
            return False

        try:
            # Use scroll to find points with this document_id
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
            )

            if not points:
                return False

            # Update each point's payload
            for point in points:
                new_payload = dict(point.payload)
                new_payload.update(updates)
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=new_payload,
                    points=[point.id],
                )

            return True
        except Exception:
            return False
