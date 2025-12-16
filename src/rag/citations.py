"""Structured citations for grounded answers.

FR-P0-1: Grounded Answers
- System MUST generate responses ONLY from indexed data
- MUST always return sources (document, date, fragment)

This module provides data structures for citations and
helpers for extracting and formatting source references.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Citation:
    """A single source citation.

    Contains all information needed to trace a response
    back to its source document.
    """

    # Core identifiers
    document_id: str
    source_type: str  # email, note, whatsapp, messenger

    # Source location
    filename: str
    file_path: str

    # Content reference
    fragment: str  # Exact text used (first 100-200 chars)
    date: str  # ISO format date from source

    # Relevance
    score: float  # Similarity score (0-1)

    # Full metadata (for UI display)
    metadata: dict = field(default_factory=dict)

    def to_inline_citation(self) -> str:
        """Format as inline citation for LLM response.

        Returns:
            String like [Source: email, 2024-01-15, "Meeting notes..."]
        """
        # Extract just the date portion
        date_str = self.date[:10] if len(self.date) >= 10 else self.date

        # Truncate fragment for inline use
        fragment_preview = self.fragment[:50]
        if len(self.fragment) > 50:
            fragment_preview += "..."

        return f'[Source: {self.source_type}, {date_str}, "{fragment_preview}"]'

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "source_type": self.source_type,
            "filename": self.filename,
            "file_path": self.file_path,
            "fragment": self.fragment,
            "date": self.date,
            "score": self.score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_source_node(cls, node: Any) -> "Citation":
        """Create Citation from LlamaIndex source node.

        Args:
            node: LlamaIndex NodeWithScore object

        Returns:
            Citation instance
        """
        metadata = node.metadata or {}

        # Get date from metadata, fallback to indexed_at
        date = metadata.get("date") or metadata.get("indexed_at") or ""

        # Truncate text for fragment
        text = node.text or ""
        fragment = text[:200] + "..." if len(text) > 200 else text

        return cls(
            document_id=metadata.get("document_id", "unknown"),
            source_type=metadata.get("source_type", "unknown"),
            filename=metadata.get("filename", "unknown"),
            file_path=metadata.get("file_path", ""),
            fragment=fragment,
            date=date,
            score=node.score or 0.0,
            metadata=metadata,
        )


@dataclass
class GroundedResponse:
    """A response with grounding information.

    Tracks whether the response is properly grounded
    in the provided citations.
    """

    # The response content
    answer: str

    # Source citations
    citations: list[Citation] = field(default_factory=list)

    # Grounding status
    is_grounded: bool = True  # True if answer uses only citations
    no_context_found: bool = False  # True if no relevant context

    # Metadata
    conversation_id: int | None = None
    query_time_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "is_grounded": self.is_grounded,
            "no_context_found": self.no_context_found,
            "conversation_id": self.conversation_id,
            "query_time_ms": self.query_time_ms,
        }

    @property
    def sources(self) -> list[dict]:
        """Get sources in legacy format for backward compatibility.

        Returns:
            List of source dicts matching old RAGEngine.query() format
        """
        return [
            {
                "content": c.fragment,
                "metadata": c.metadata,
                "score": c.score,
            }
            for c in self.citations
        ]


def extract_citations(source_nodes: list[Any]) -> list[Citation]:
    """Extract citations from LlamaIndex source nodes.

    Args:
        source_nodes: List of NodeWithScore from query response

    Returns:
        List of Citation objects
    """
    return [Citation.from_source_node(node) for node in source_nodes]


def format_citations_for_context(citations: list[Citation]) -> str:
    """Format citations as context string for LLM prompt.

    Args:
        citations: List of Citation objects

    Returns:
        Formatted string with numbered sources
    """
    if not citations:
        return "No relevant sources found."

    parts = []
    for i, cite in enumerate(citations, 1):
        date_str = cite.date[:10] if len(cite.date) >= 10 else cite.date
        parts.append(
            f"[Source {i}] ({cite.source_type}, {date_str}, {cite.filename}):\n"
            f"{cite.fragment}\n"
        )

    return "\n".join(parts)


def validate_grounding(answer: str, citations: list[Citation]) -> bool:
    """Heuristically check if answer is grounded in citations.

    This is a best-effort check. It looks for:
    1. Presence of citation markers
    2. "Could not find" responses
    3. Short answers that might indicate refusal

    Args:
        answer: The LLM response
        citations: Available citations

    Returns:
        True if answer appears grounded
    """
    answer_lower = answer.lower()

    # Check for "no information found" response
    no_info_phrases = [
        "could not find",
        "no information",
        "not found in",
        "don't have information",
        "no relevant",
    ]
    if any(phrase in answer_lower for phrase in no_info_phrases):
        return True  # Properly refused to make things up

    # Check for citation markers
    has_citations = "[source:" in answer_lower or "[source " in answer_lower

    # If we have citations and the answer references them, it's grounded
    if citations and has_citations:
        return True

    # If no citations available and short answer, likely grounded (refused)
    if not citations and len(answer) < 100:
        return True

    # If we have citations but no markers, might be ungrounded
    # But we can't be certain - LLM might have paraphrased
    return has_citations or not citations


# Grounded system prompt template
GROUNDED_SYSTEM_PROMPT = """You are a personal data assistant. You MUST ONLY answer based on the provided context from the user's indexed data.

CRITICAL RULES:
1. ONLY use information explicitly stated in the context below
2. If the context does not contain relevant information, respond: "I could not find this information in your data."
3. NEVER use knowledge from your training data - only the provided context
4. ALWAYS cite your sources using the format: [Source: {source_type}, {date}, "{brief_quote}"]
5. Be specific about which source each fact comes from

Context from user's data:
{context_str}

User's question: {query_str}

Answer using ONLY the context above. Include inline citations for every fact:"""
