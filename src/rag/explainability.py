"""Explainability system for RAG queries.

FR-P0-4: Explainability
- System MUST show which fragments entered context
- System MUST show WHY they were selected (scoring, filters)
- System MUST show which RAG mode was used

This module provides data structures and utilities for
explaining RAG query decisions to users.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RetrievalExplanation:
    """Explains why a document was selected for context.

    Contains the breakdown of all scoring components
    that contributed to the document's selection.
    """

    # Document identification
    document_id: str
    filename: str
    source_type: str

    # Scoring breakdown
    similarity_score: float  # Raw vector similarity (0-1)
    priority_score: float  # Priority weight (0-1)
    final_score: float  # Combined weighted score (0-1)

    # Priority component breakdown
    type_contribution: float  # From document type
    recency_contribution: float  # From document age
    approval_contribution: float  # From pin/approval status

    # Selection info
    rank: int  # Position in final ranking
    passed_filters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "source_type": self.source_type,
            "similarity_score": self.similarity_score,
            "priority_score": self.priority_score,
            "final_score": self.final_score,
            "type_contribution": self.type_contribution,
            "recency_contribution": self.recency_contribution,
            "approval_contribution": self.approval_contribution,
            "rank": self.rank,
            "passed_filters": self.passed_filters,
        }


@dataclass
class ContextFragment:
    """A fragment of text that was included in context."""

    text: str  # The actual text content
    source_id: str  # Document ID
    source_type: str
    token_count: int  # Approximate token count
    truncated: bool = False  # Was text truncated to fit?

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "token_count": self.token_count,
            "truncated": self.truncated,
        }


@dataclass
class ContextWindowExplanation:
    """Explains what was included in the LLM context window.

    Shows what fit in the context, what was truncated,
    and what had to be excluded.
    """

    # Token counts
    total_tokens: int  # Tokens used in context
    max_tokens: int  # Maximum allowed tokens
    utilization: float  # Percentage of context used

    # Fragments included
    fragments: list[ContextFragment] = field(default_factory=list)
    fragment_count: int = 0

    # What didn't fit
    overflow_documents: int = 0  # Documents excluded due to limit
    overflow_tokens: int = 0  # Tokens that didn't fit

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": self.utilization,
            "fragment_count": self.fragment_count,
            "fragments": [f.to_dict() for f in self.fragments],
            "overflow_documents": self.overflow_documents,
            "overflow_tokens": self.overflow_tokens,
        }


@dataclass
class RAGExplanation:
    """Full explanation of a RAG query.

    Provides complete transparency into how a query
    was processed and why specific results were returned.
    """

    # Query info
    query_text: str
    query_embedding_model: str

    # Retrieval explanation
    retrieval_mode: str  # "similarity", "priority_weighted", "hybrid"
    retrieval_top_k: int
    documents_retrieved: list[RetrievalExplanation] = field(default_factory=list)

    # Context explanation
    context_window: ContextWindowExplanation | None = None

    # Response info
    response_mode: str = ""  # "compact", "refine", "tree_summarize"
    llm_provider: str = ""
    llm_model: str = ""

    # Timing breakdown (milliseconds)
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Filters applied
    filters_applied: dict = field(default_factory=dict)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_text": self.query_text[:50] + "..." if len(self.query_text) > 50 else self.query_text,
            "query_embedding_model": self.query_embedding_model,
            "retrieval_mode": self.retrieval_mode,
            "retrieval_top_k": self.retrieval_top_k,
            "documents_retrieved": [d.to_dict() for d in self.documents_retrieved],
            "context_window": self.context_window.to_dict() if self.context_window else None,
            "response_mode": self.response_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "timing": {
                "retrieval_ms": self.retrieval_time_ms,
                "generation_ms": self.generation_time_ms,
                "total_ms": self.total_time_ms,
            },
            "filters_applied": self.filters_applied,
            "timestamp": self.timestamp.isoformat(),
        }


def create_retrieval_explanation(
    node: Any,
    rank: int,
    priority_info: dict | None = None,
) -> RetrievalExplanation:
    """Create retrieval explanation from LlamaIndex node.

    Args:
        node: LlamaIndex NodeWithScore
        rank: Position in ranking
        priority_info: Optional priority breakdown dict

    Returns:
        RetrievalExplanation instance
    """
    metadata = node.metadata or {}
    priority = priority_info or {}

    return RetrievalExplanation(
        document_id=metadata.get("document_id", "unknown"),
        filename=metadata.get("filename", "unknown"),
        source_type=metadata.get("source_type", "unknown"),
        similarity_score=node.score or 0.0,
        priority_score=priority.get("priority_score", 0.0),
        final_score=priority.get("weighted_score", node.score or 0.0),
        type_contribution=priority.get("type_contribution", 0.0),
        recency_contribution=priority.get("recency_contribution", 0.0),
        approval_contribution=priority.get("approval_contribution", 0.0),
        rank=rank,
    )


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Simple approximation: ~4 characters per token.

    Args:
        text: Text to estimate

    Returns:
        Approximate token count
    """
    return len(text) // 4


def create_context_explanation(
    source_nodes: list[Any],
    max_tokens: int = 4000,
) -> ContextWindowExplanation:
    """Create context window explanation from source nodes.

    Args:
        source_nodes: List of LlamaIndex NodeWithScore
        max_tokens: Maximum context tokens

    Returns:
        ContextWindowExplanation instance
    """
    fragments = []
    total_tokens = 0

    for node in source_nodes:
        text = node.text or ""
        tokens = estimate_tokens(text)
        total_tokens += tokens

        fragments.append(
            ContextFragment(
                text=text,
                source_id=node.metadata.get("document_id", "unknown") if node.metadata else "unknown",
                source_type=node.metadata.get("source_type", "unknown") if node.metadata else "unknown",
                token_count=tokens,
                truncated=len(text) > 500,  # Approximation
            )
        )

    utilization = min(1.0, total_tokens / max_tokens) if max_tokens > 0 else 0.0
    overflow = max(0, total_tokens - max_tokens)

    return ContextWindowExplanation(
        total_tokens=total_tokens,
        max_tokens=max_tokens,
        utilization=utilization,
        fragments=fragments,
        fragment_count=len(fragments),
        overflow_documents=0,  # Would need more info to calculate
        overflow_tokens=overflow,
    )


def format_explanation_summary(explanation: RAGExplanation) -> str:
    """Format explanation as human-readable summary.

    Args:
        explanation: RAGExplanation object

    Returns:
        Formatted string summary
    """
    lines = [
        f"Query processed in {explanation.total_time_ms:.0f}ms",
        f"  Retrieval: {explanation.retrieval_time_ms:.0f}ms ({explanation.retrieval_mode})",
        f"  Generation: {explanation.generation_time_ms:.0f}ms ({explanation.llm_provider})",
        f"",
        f"Documents retrieved: {len(explanation.documents_retrieved)}",
    ]

    if explanation.documents_retrieved:
        lines.append("  Top sources:")
        for doc in explanation.documents_retrieved[:3]:
            lines.append(
                f"    {doc.rank}. {doc.filename} "
                f"(sim: {doc.similarity_score:.2f}, pri: {doc.priority_score:.2f})"
            )

    if explanation.context_window:
        ctx = explanation.context_window
        lines.extend([
            f"",
            f"Context: {ctx.total_tokens}/{ctx.max_tokens} tokens "
            f"({ctx.utilization:.0%} used)",
        ])
        if ctx.overflow_documents > 0:
            lines.append(f"  {ctx.overflow_documents} documents excluded (overflow)")

    return "\n".join(lines)
