"""Document priority and weighting system.

FR-P0-3: Source of Truth & Priority Rules
- System MUST distinguish information weight:
  - decisions > notes > conversations
  - newer > older
  - pinned/approved > automatic
"""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from src.config import settings


class DocumentType(IntEnum):
    """Priority weights for document types.

    Higher values = more authoritative source.
    """

    PROFILE = 120  # User's own profile information (highest priority for self-context)
    DECISION = 100  # Explicit decisions, approved documents
    NOTE = 70  # Personal notes, markdown files
    EMAIL = 50  # Email correspondence
    CONTACT = 40  # Contact/relationship information
    CONVERSATION = 30  # WhatsApp, Messenger chats
    INTERESTS = 25  # User interests from ads data
    LOCATION = 20  # Location history
    SEARCH_HISTORY = 10  # Search history (lowest priority)


class ApprovalStatus(IntEnum):
    """Approval status weights.

    Higher values = more trusted content.
    """

    PINNED = 50  # User-pinned as authoritative
    APPROVED = 30  # User-verified content
    AUTOMATIC = 0  # Auto-indexed, not reviewed


# Mapping from source_type/category to DocumentType
CATEGORY_WEIGHTS: dict[str, DocumentType] = {
    # High priority
    "profile": DocumentType.PROFILE,
    "decision": DocumentType.DECISION,
    # Medium priority
    "note": DocumentType.NOTE,
    "text": DocumentType.NOTE,
    "email": DocumentType.EMAIL,
    "contact": DocumentType.CONTACT,
    "contacts": DocumentType.CONTACT,
    # Lower priority
    "whatsapp": DocumentType.CONVERSATION,
    "messenger": DocumentType.CONVERSATION,
    "conversation": DocumentType.CONVERSATION,
    "interests": DocumentType.INTERESTS,
    "location": DocumentType.LOCATION,
    "search_history": DocumentType.SEARCH_HISTORY,
}


@dataclass
class DocumentPriority:
    """Calculated priority for a document.

    Contains the breakdown of all priority components
    and the final combined score.
    """

    # Component scores
    type_weight: int  # From DocumentType enum
    approval_weight: int  # From ApprovalStatus enum
    recency_weight: float  # 0.0 to 1.0 based on age

    # Component contributions (normalized)
    type_contribution: float
    approval_contribution: float
    recency_contribution: float

    # Final combined score (0.0 to 1.0)
    priority_score: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type_weight": self.type_weight,
            "approval_weight": self.approval_weight,
            "recency_weight": self.recency_weight,
            "type_contribution": self.type_contribution,
            "approval_contribution": self.approval_contribution,
            "recency_contribution": self.recency_contribution,
            "priority_score": self.priority_score,
        }


def calculate_priority(
    source_type: str | None = None,
    document_category: str | None = None,
    date: datetime | str | None = None,
    is_pinned: bool = False,
    is_approved: bool = False,
    max_age_days: int | None = None,
) -> DocumentPriority:
    """Calculate document priority score.

    The priority is calculated from three components:
    1. Type weight (40%): Based on document type/category
    2. Approval weight (30%): Based on user verification status
    3. Recency weight (30%): Linear decay over max_age_days

    Args:
        source_type: Source type (text, email, whatsapp, messenger)
        document_category: Override category (decision, note, email, conversation)
        date: Document date (ISO string or datetime)
        is_pinned: Whether document is user-pinned
        is_approved: Whether document is user-approved
        max_age_days: Max age for recency calculation (default from settings)

    Returns:
        DocumentPriority with all component scores
    """
    max_age_days = max_age_days or settings.priority_recency_max_days

    # Determine type weight
    category = document_category or source_type or "note"
    type_weight = CATEGORY_WEIGHTS.get(category, DocumentType.NOTE)

    # Determine approval weight
    if is_pinned:
        approval_weight = ApprovalStatus.PINNED
    elif is_approved:
        approval_weight = ApprovalStatus.APPROVED
    else:
        approval_weight = ApprovalStatus.AUTOMATIC

    # Calculate recency weight (1.0 for today, 0.0 for max_age_days ago)
    if date:
        if isinstance(date, str):
            try:
                # Handle ISO format with possible timezone
                date_str = date[:19]  # Take just YYYY-MM-DDTHH:MM:SS
                parsed_date = datetime.fromisoformat(date_str)
            except ValueError:
                parsed_date = datetime.now()
        else:
            parsed_date = date

        age_days = (datetime.now() - parsed_date).days
        recency_weight = max(0.0, 1.0 - (age_days / max_age_days))
    else:
        recency_weight = 0.5  # Default to middle if no date

    # Normalize component contributions
    # Type: 0-100 -> 0-1 (scale by max possible)
    max_type = float(DocumentType.DECISION)
    type_contribution = float(type_weight) / max_type

    # Approval: 0-50 -> 0-1 (scale by max possible)
    max_approval = float(ApprovalStatus.PINNED)
    approval_contribution = float(approval_weight) / max_approval if max_approval > 0 else 0

    # Recency is already 0-1
    recency_contribution = recency_weight

    # Calculate final priority score
    # Weighted average: 40% type + 30% approval + 30% recency
    priority_score = (
        0.4 * type_contribution
        + 0.3 * approval_contribution
        + 0.3 * recency_contribution
    )

    return DocumentPriority(
        type_weight=int(type_weight),
        approval_weight=int(approval_weight),
        recency_weight=recency_weight,
        type_contribution=type_contribution,
        approval_contribution=approval_contribution,
        recency_contribution=recency_contribution,
        priority_score=priority_score,
    )


def calculate_weighted_score(
    similarity_score: float,
    priority: DocumentPriority,
    similarity_weight: float | None = None,
    priority_weight: float | None = None,
) -> float:
    """Calculate final weighted score combining similarity and priority.

    Args:
        similarity_score: Semantic similarity score (0-1)
        priority: Document priority object
        similarity_weight: Weight for similarity (default from settings)
        priority_weight: Weight for priority (default from settings)

    Returns:
        Combined weighted score (0-1)
    """
    similarity_weight = similarity_weight or settings.priority_similarity_weight
    priority_weight = priority_weight or settings.priority_document_weight

    # Ensure weights sum to 1
    total = similarity_weight + priority_weight
    if total != 1.0:
        similarity_weight = similarity_weight / total
        priority_weight = priority_weight / total

    return (
        similarity_weight * similarity_score
        + priority_weight * priority.priority_score
    )


def extract_priority_from_metadata(metadata: dict) -> DocumentPriority:
    """Extract priority from document metadata.

    Args:
        metadata: Document metadata dict

    Returns:
        DocumentPriority calculated from metadata fields
    """
    return calculate_priority(
        source_type=metadata.get("source_type"),
        document_category=metadata.get("document_category"),
        date=metadata.get("date") or metadata.get("indexed_at"),
        is_pinned=metadata.get("is_pinned", False),
        is_approved=metadata.get("is_approved", False),
    )


@dataclass
class RankedDocument:
    """A document with priority-weighted ranking."""

    content: str
    metadata: dict
    similarity_score: float
    priority: DocumentPriority
    weighted_score: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score,
            "priority": self.priority.to_dict(),
            "weighted_score": self.weighted_score,
        }


def rank_documents(
    documents: list[dict],
    similarity_weight: float | None = None,
    priority_weight: float | None = None,
) -> list[RankedDocument]:
    """Rank documents by priority-weighted score.

    Takes documents with similarity scores and re-ranks them
    based on combined similarity + priority scoring.

    Args:
        documents: List of dicts with 'content', 'metadata', 'score'
        similarity_weight: Weight for similarity (default from settings)
        priority_weight: Weight for priority (default from settings)

    Returns:
        List of RankedDocument sorted by weighted_score descending
    """
    ranked = []

    for doc in documents:
        priority = extract_priority_from_metadata(doc.get("metadata", {}))
        similarity = doc.get("score", 0.0)

        weighted = calculate_weighted_score(
            similarity_score=similarity,
            priority=priority,
            similarity_weight=similarity_weight,
            priority_weight=priority_weight,
        )

        ranked.append(
            RankedDocument(
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                similarity_score=similarity,
                priority=priority,
                weighted_score=weighted,
            )
        )

    # Sort by weighted score descending
    ranked.sort(key=lambda x: x.weighted_score, reverse=True)

    return ranked
