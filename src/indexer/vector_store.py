"""Qdrant vector store integration."""

from llama_index.core import Settings as LlamaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

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
