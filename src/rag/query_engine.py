"""RAG query engine for question answering.

FR-P0-1: Grounded Answers - responses ONLY from indexed data with citations.
"""

import time
from datetime import datetime

from llama_index.core import Settings as LlamaSettings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer

from src.config import settings
from src.indexer import VectorStore
from src.llm import BaseLLM, create_llm
from src.rag.citations import (
    Citation,
    GroundedResponse,
    extract_citations,
    validate_grounding,
    GROUNDED_SYSTEM_PROMPT,
)
from src.rag.explainability import (
    RAGExplanation,
    create_retrieval_explanation,
    create_context_explanation,
)
from src.rag.query_preprocessor import QueryPreprocessor
from src.storage import ChatHistory


class RAGEngine:
    """RAG engine for querying personal data.

    FR-P0-1: All responses are grounded in indexed data with
    mandatory source citations. The LLM is instructed to ONLY
    use provided context and cite sources for every fact.
    """

    # Use grounded prompt that enforces citations
    SYSTEM_PROMPT = GROUNDED_SYSTEM_PROMPT

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
        include_explanation: bool = False,
        person_filter: str | None = None,
        date_range: tuple[datetime, datetime] | None = None,
        source_type: str | None = None,
        use_query_preprocessing: bool = True,
    ) -> dict:
        """Query the RAG system with grounded answers.

        FR-P0-1: Responses are grounded in indexed data with citations.
        FR-P0-4: Optional explainability showing retrieval decisions.

        Supports filtering by person, date range, and source type.
        Filters can be specified explicitly or extracted from the query.

        Args:
            question: User's question
            conversation_id: Optional conversation ID for context
            top_k: Number of documents to retrieve
            include_sources: Whether to include source metadata
            include_explanation: Whether to include RAG explanation
            person_filter: Filter by sender/contact name
            date_range: Filter by date range (start, end)
            source_type: Filter by source type (email, messenger, whatsapp, text)
            use_query_preprocessing: Whether to extract filters from question

        Returns:
            Dict with 'answer', 'sources', 'citations', 'is_grounded',
            and optionally 'explanation', 'conversation_id', 'filters_applied'
        """
        start_time = time.time()
        top_k = top_k or settings.top_k

        # Preprocess query to extract implicit filters
        filters_applied = {}
        clean_question = question

        if use_query_preprocessing:
            preprocessor = QueryPreprocessor()
            preprocessed = preprocessor.preprocess(question)

            # Use preprocessed filters if not explicitly provided
            if not person_filter and preprocessed.person_filter:
                person_filter = preprocessed.person_filter
            if not date_range and preprocessed.date_range:
                date_range = preprocessed.date_range
            if not source_type and preprocessed.source_filter:
                source_type = preprocessed.source_filter

            # Use cleaned query for semantic search
            clean_question = preprocessed.clean_query
            filters_applied = preprocessed.extracted_filters

        # Build metadata filters for retrieval
        metadata_filters = self._build_metadata_filters(
            person_filter=person_filter,
            date_range=date_range,
            source_type=source_type,
        )

        # Build query engine with optional filters
        retriever = self.vector_store.index.as_retriever(
            similarity_top_k=top_k,
            filters=metadata_filters if metadata_filters else None,
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

        # Track retrieval time
        retrieval_start = time.time()

        # Execute query
        response = query_engine.query(full_question)

        retrieval_time_ms = (time.time() - retrieval_start) * 1000

        # Track generation time (approximate - includes response synthesis)
        generation_start = time.time()

        # Calculate total query time
        query_time_ms = (time.time() - start_time) * 1000
        generation_time_ms = query_time_ms - retrieval_time_ms

        # Extract structured citations (FR-P0-1)
        citations: list[Citation] = []
        if include_sources and response.source_nodes:
            citations = extract_citations(response.source_nodes)

        # Check if response is properly grounded
        answer = str(response)
        is_grounded = validate_grounding(answer, citations)
        no_context_found = not citations or "could not find" in answer.lower()

        # Build grounded response
        grounded_response = GroundedResponse(
            answer=answer,
            citations=citations,
            is_grounded=is_grounded,
            no_context_found=no_context_found,
            conversation_id=conversation_id,
            query_time_ms=query_time_ms,
        )

        # Legacy sources format for backward compatibility
        sources = grounded_response.sources

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
                content=answer,
                sources=sources,
            )

        result = {
            "answer": answer,
            "sources": sources,
            "citations": [c.to_dict() for c in citations],
            "is_grounded": is_grounded,
            "no_context_found": no_context_found,
            "conversation_id": conversation_id,
            "query_time_ms": query_time_ms,
            "filters_applied": filters_applied,
        }

        # FR-P0-4: Build explainability data if requested
        if include_explanation and response.source_nodes:
            explanation = self._build_explanation(
                query_text=full_question,
                source_nodes=response.source_nodes,
                top_k=top_k,
                retrieval_time_ms=retrieval_time_ms,
                generation_time_ms=generation_time_ms,
                total_time_ms=query_time_ms,
            )
            result["explanation"] = explanation.to_dict()

        return result

    def _build_explanation(
        self,
        query_text: str,
        source_nodes: list,
        top_k: int,
        retrieval_time_ms: float,
        generation_time_ms: float,
        total_time_ms: float,
    ) -> RAGExplanation:
        """Build RAG explanation from query results.

        FR-P0-4: Creates detailed explanation of retrieval decisions.

        Args:
            query_text: The query that was executed
            source_nodes: Retrieved source nodes
            top_k: Number of documents requested
            retrieval_time_ms: Time spent on retrieval
            generation_time_ms: Time spent on generation
            total_time_ms: Total query time

        Returns:
            RAGExplanation with full breakdown
        """
        # Build retrieval explanations for each document
        doc_explanations = []
        for i, node in enumerate(source_nodes):
            doc_explanations.append(
                create_retrieval_explanation(node, rank=i + 1)
            )

        # Build context window explanation
        context_explanation = create_context_explanation(source_nodes)

        # Get LLM info
        llm_provider = self.llm_provider.name
        llm_model = getattr(settings, f"{settings.llm_provider}_model", "unknown")

        return RAGExplanation(
            query_text=query_text,
            query_embedding_model=settings.embedding_model,
            retrieval_mode="similarity",  # Would be "priority_weighted" if using search_with_priority
            retrieval_top_k=top_k,
            documents_retrieved=doc_explanations,
            context_window=context_explanation,
            response_mode="compact",
            llm_provider=llm_provider,
            llm_model=llm_model,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=total_time_ms,
        )

    def _get_qa_prompt(self):
        """Get the QA prompt template."""
        from llama_index.core import PromptTemplate

        return PromptTemplate(self.SYSTEM_PROMPT)

    def _build_metadata_filters(
        self,
        person_filter: str | None = None,
        date_range: tuple[datetime, datetime] | None = None,
        source_type: str | None = None,
    ) -> dict | None:
        """Build metadata filters for retrieval.

        Args:
            person_filter: Filter by sender name
            date_range: Filter by date range (start, end)
            source_type: Filter by source type

        Returns:
            Metadata filter dict for LlamaIndex, or None if no filters
        """
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator

        filters = []

        if person_filter:
            # Filter by sender field (case-insensitive partial match)
            filters.append(
                MetadataFilter(
                    key="sender",
                    value=person_filter,
                    operator=FilterOperator.CONTAINS,
                )
            )

        if source_type:
            filters.append(
                MetadataFilter(
                    key="source_type",
                    value=source_type,
                    operator=FilterOperator.EQ,
                )
            )

        # Note: Date range filtering is complex with LlamaIndex
        # For now, we'll handle it post-retrieval if needed
        # This is a limitation of the current implementation

        if not filters:
            return None

        return MetadataFilters(filters=filters)

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
