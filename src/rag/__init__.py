"""RAG query engine functionality.

FR-P0: Critical requirements implementation:
- FR-P0-1: Grounded answers with citations
- FR-P0-3: Source of Truth & Priority Rules
- FR-P0-4: Explainability
- FR-P0-5: Forget / Right to Be Forgotten
"""

from .query_engine import RAGEngine
from .citations import Citation, GroundedResponse, GROUNDED_SYSTEM_PROMPT
from .priority import (
    DocumentType,
    ApprovalStatus,
    DocumentPriority,
    calculate_priority,
    rank_documents,
)
from .explainability import RAGExplanation, RetrievalExplanation
from .forget import ForgetService, ForgetResult

__all__ = [
    # Query engine
    "RAGEngine",
    # Citations (FR-P0-1)
    "Citation",
    "GroundedResponse",
    "GROUNDED_SYSTEM_PROMPT",
    # Priority (FR-P0-3)
    "DocumentType",
    "ApprovalStatus",
    "DocumentPriority",
    "calculate_priority",
    "rank_documents",
    # Explainability (FR-P0-4)
    "RAGExplanation",
    "RetrievalExplanation",
    # Forget (FR-P0-5)
    "ForgetService",
    "ForgetResult",
]
