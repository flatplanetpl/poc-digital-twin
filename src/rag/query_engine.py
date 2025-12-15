"""RAG query engine for question answering."""

from llama_index.core import Settings as LlamaSettings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer

from src.config import settings
from src.indexer import VectorStore
from src.llm import BaseLLM, create_llm
from src.storage import ChatHistory


class RAGEngine:
    """RAG engine for querying personal data."""

    SYSTEM_PROMPT = """You are a helpful AI assistant with access to the user's personal data.
Your role is to answer questions based on the provided context from their notes, emails, and chats.

Guidelines:
- Only use information from the provided context
- If you don't find relevant information, say so clearly
- When citing information, mention the source type (email, note, chat)
- Be concise but complete in your answers
- Respect the user's privacy - don't make assumptions about data not in context

Context from user's data:
{context_str}

User's question: {query_str}

Answer based on the context above:"""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        llm_provider: BaseLLM | None = None,
        chat_history: ChatHistory | None = None,
    ):
        """Initialize RAG engine.

        Args:
            vector_store: Vector store instance. If None, creates new one.
            llm_provider: LLM provider. If None, creates from settings.
            chat_history: Chat history storage. If None, creates new one.
        """
        self.vector_store = vector_store or VectorStore()
        self.llm_provider = llm_provider or create_llm()
        self.chat_history = chat_history or ChatHistory()

        # Configure LlamaIndex to use our LLM
        self._configure_llm()

    def _configure_llm(self) -> None:
        """Configure LlamaIndex settings with current LLM."""
        LlamaSettings.llm = self.llm_provider.get_llama_index_llm()

    def set_llm_provider(self, provider: str | BaseLLM) -> None:
        """Change the LLM provider.

        Args:
            provider: Provider name string or BaseLLM instance
        """
        if isinstance(provider, str):
            self.llm_provider = create_llm(provider)
        else:
            self.llm_provider = provider

        self._configure_llm()

    def query(
        self,
        question: str,
        conversation_id: int | None = None,
        top_k: int | None = None,
        include_sources: bool = True,
    ) -> dict:
        """Query the RAG system.

        Args:
            question: User's question
            conversation_id: Optional conversation ID for context
            top_k: Number of documents to retrieve
            include_sources: Whether to include source metadata

        Returns:
            Dict with 'answer', 'sources', and optionally 'conversation_id'
        """
        top_k = top_k or settings.top_k

        # Build query engine
        retriever = self.vector_store.index.as_retriever(
            similarity_top_k=top_k,
        )

        response_synthesizer = get_response_synthesizer(
            response_mode="compact",
            text_qa_template=self._get_qa_prompt(),
        )

        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
        )

        # Add conversation context if available
        full_question = self._build_question_with_context(
            question, conversation_id
        )

        # Execute query
        response = query_engine.query(full_question)

        # Extract sources
        sources = []
        if include_sources and response.source_nodes:
            for node in response.source_nodes:
                sources.append({
                    "content": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                    "metadata": node.metadata,
                    "score": node.score,
                })

        # Save to chat history if conversation exists
        if conversation_id:
            self.chat_history.add_message(
                conversation_id=conversation_id,
                role="user",
                content=question,
            )
            self.chat_history.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=str(response),
                sources=sources,
            )

        return {
            "answer": str(response),
            "sources": sources,
            "conversation_id": conversation_id,
        }

    def _get_qa_prompt(self):
        """Get the QA prompt template."""
        from llama_index.core import PromptTemplate

        return PromptTemplate(self.SYSTEM_PROMPT)

    def _build_question_with_context(
        self, question: str, conversation_id: int | None
    ) -> str:
        """Build question with conversation context.

        Args:
            question: Current question
            conversation_id: Optional conversation ID

        Returns:
            Question potentially augmented with context
        """
        if not conversation_id:
            return question

        # Get recent messages for context
        recent_messages = self.chat_history.get_recent_messages(
            conversation_id, limit=4
        )

        if not recent_messages:
            return question

        # Build context string
        context_parts = ["Previous conversation:"]
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")

        context_parts.append(f"\nCurrent question: {question}")

        return "\n".join(context_parts)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        source_type: str | None = None,
    ) -> list[dict]:
        """Search for relevant documents without generating an answer.

        Args:
            query: Search query
            top_k: Number of results
            source_type: Optional filter by source type

        Returns:
            List of matching documents with metadata
        """
        top_k = top_k or settings.top_k

        filters = {}
        if source_type:
            filters["source_type"] = source_type

        return self.vector_store.search(query, top_k=top_k, filters=filters)

    def get_stats(self) -> dict:
        """Get system statistics.

        Returns:
            Dict with index and provider stats
        """
        return {
            "index": self.vector_store.get_stats(),
            "llm_provider": {
                "name": self.llm_provider.name,
                "is_local": self.llm_provider.is_local,
            },
        }
