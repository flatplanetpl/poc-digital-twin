"""Contact graph service for relationship analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.indexer.vector_store import VectorStore

from src.storage.contact_registry import Contact, ContactRegistry


@dataclass
class ContactRelationship:
    """Represents a relationship with a contact."""

    contact_name: str
    normalized_name: str
    message_count: int = 0
    call_count: int = 0
    first_interaction: datetime | None = None
    last_interaction: datetime | None = None
    interaction_score: float = 0.0
    relationship_types: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    is_family: bool = False
    is_friend: bool = False


class ContactGraph:
    """Service for building and querying contact relationships.

    Aggregates contact information from multiple sources (Messenger, WhatsApp,
    Email, Facebook friends) and provides relationship analysis.
    """

    def __init__(
        self,
        contact_registry: ContactRegistry | None = None,
        vector_store: "VectorStore | None" = None,
    ):
        """Initialize contact graph.

        Args:
            contact_registry: Contact registry instance
            vector_store: Vector store for semantic queries (optional)
        """
        self.contact_registry = contact_registry or ContactRegistry()
        self.vector_store = vector_store
        self._relationships: dict[str, ContactRelationship] = {}

    def build_from_registry(self) -> int:
        """Build relationship graph from contact registry.

        Aggregates contacts from all sources by normalized name.

        Returns:
            Number of unique relationships built
        """
        self._relationships.clear()

        contacts = self.contact_registry.get_all_contacts(exclude_hidden=True)

        for contact in contacts:
            normalized = contact.normalized_name

            if normalized not in self._relationships:
                self._relationships[normalized] = ContactRelationship(
                    contact_name=contact.name,
                    normalized_name=normalized,
                )

            rel = self._relationships[normalized]

            # Aggregate stats
            rel.message_count += contact.message_count
            rel.call_count += contact.call_count

            # Track sources
            if contact.source not in rel.sources:
                rel.sources.append(contact.source)

            # Update timestamps
            if contact.first_seen:
                if rel.first_interaction is None or contact.first_seen < rel.first_interaction:
                    rel.first_interaction = contact.first_seen

            if contact.last_seen:
                if rel.last_interaction is None or contact.last_seen > rel.last_interaction:
                    rel.last_interaction = contact.last_seen

            # Track relationship types
            if contact.relationship_type:
                if contact.relationship_type not in rel.relationship_types:
                    rel.relationship_types.append(contact.relationship_type)

                if contact.relationship_type == "family":
                    rel.is_family = True
                elif contact.relationship_type == "friend":
                    rel.is_friend = True

            # Prefer display name from most active source
            if contact.message_count > 0:
                rel.contact_name = contact.name

        # Calculate interaction scores
        for rel in self._relationships.values():
            rel.interaction_score = self.calculate_interaction_score(rel)

        return len(self._relationships)

    def calculate_interaction_score(self, relationship: ContactRelationship) -> float:
        """Calculate relationship strength score (0-1).

        Score components:
        - Frequency (40%): Messages per month, capped at 100/month
        - Recency (40%): Days since last interaction, linear decay over 365 days
        - Diversity (20%): Multiple sources bonus

        Args:
            relationship: ContactRelationship to score

        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0

        # Frequency component (0-0.4)
        if relationship.first_interaction and relationship.message_count > 0:
            days_known = max(
                1,
                (datetime.now() - relationship.first_interaction).days,
            )
            messages_per_month = (relationship.message_count / days_known) * 30
            frequency_score = min(0.4, (messages_per_month / 100) * 0.4)
            score += frequency_score

        # Recency component (0-0.4)
        if relationship.last_interaction:
            days_since = (datetime.now() - relationship.last_interaction).days
            recency_score = max(0.0, 0.4 - (days_since / 365) * 0.4)
            score += recency_score

        # Diversity component (0-0.2)
        # Bonus for appearing in multiple sources
        if len(relationship.sources) >= 2:
            score += 0.15
        if len(relationship.sources) >= 3:
            score += 0.05

        # Small bonus for calls
        if relationship.call_count > 0:
            score += min(0.05, relationship.call_count * 0.01)

        return min(1.0, score)

    def get_relationship(self, name: str) -> ContactRelationship | None:
        """Get relationship information for a contact.

        Args:
            name: Contact name (fuzzy matched via normalized name)

        Returns:
            ContactRelationship or None if not found
        """
        normalized = ContactRegistry.normalize_name(name)

        if normalized in self._relationships:
            return self._relationships[normalized]

        # Try partial match
        for norm_name, rel in self._relationships.items():
            if normalized in norm_name or norm_name in normalized:
                return rel

        return None

    def get_top_contacts(self, limit: int = 20) -> list[ContactRelationship]:
        """Get most important contacts by interaction score.

        Args:
            limit: Maximum number of contacts to return

        Returns:
            List of ContactRelationship sorted by interaction_score
        """
        sorted_rels = sorted(
            self._relationships.values(),
            key=lambda r: r.interaction_score,
            reverse=True,
        )
        return sorted_rels[:limit]

    def get_most_frequent(self, limit: int = 20) -> list[ContactRelationship]:
        """Get contacts with most messages.

        Args:
            limit: Maximum number of contacts to return

        Returns:
            List of ContactRelationship sorted by message_count
        """
        sorted_rels = sorted(
            self._relationships.values(),
            key=lambda r: r.message_count,
            reverse=True,
        )
        return sorted_rels[:limit]

    def get_recent_contacts(self, limit: int = 20) -> list[ContactRelationship]:
        """Get most recently contacted people.

        Args:
            limit: Maximum number of contacts to return

        Returns:
            List of ContactRelationship sorted by last_interaction
        """
        with_interaction = [
            r for r in self._relationships.values()
            if r.last_interaction is not None
        ]
        sorted_rels = sorted(
            with_interaction,
            key=lambda r: r.last_interaction,
            reverse=True,
        )
        return sorted_rels[:limit]

    def get_family(self) -> list[ContactRelationship]:
        """Get all family members.

        Returns:
            List of family ContactRelationships
        """
        return [r for r in self._relationships.values() if r.is_family]

    def get_by_source(self, source: str) -> list[ContactRelationship]:
        """Get contacts from a specific source.

        Args:
            source: Source name (messenger, whatsapp, email, facebook_friends)

        Returns:
            List of ContactRelationships from that source
        """
        return [
            r for r in self._relationships.values()
            if source in r.sources
        ]

    def search(self, query: str, limit: int = 20) -> list[ContactRelationship]:
        """Search contacts by name.

        Args:
            query: Search query (partial match)
            limit: Maximum results

        Returns:
            List of matching ContactRelationships
        """
        normalized_query = ContactRegistry.normalize_name(query)

        matches = [
            rel for norm_name, rel in self._relationships.items()
            if normalized_query in norm_name
        ]

        # Sort by interaction score
        matches.sort(key=lambda r: r.interaction_score, reverse=True)
        return matches[:limit]

    def find_contacts_by_topic(
        self,
        topic: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Find contacts who discussed a specific topic.

        Uses vector store to search for topic mentions and aggregates by sender.

        Args:
            topic: Topic to search for
            top_k: Number of search results to analyze

        Returns:
            List of (contact_name, relevance_score) tuples
        """
        if not self.vector_store:
            return []

        try:
            # Search for topic in indexed content
            results = self.vector_store.search(
                query=topic,
                top_k=top_k * 3,  # Get more results for aggregation
                filters={"source_type": ["messenger", "whatsapp"]},
            )

            # Aggregate by sender
            sender_scores: dict[str, float] = {}
            for result in results:
                sender = result.get("metadata", {}).get("sender", "")
                if sender:
                    score = result.get("score", 0)
                    if sender in sender_scores:
                        sender_scores[sender] = max(sender_scores[sender], score)
                    else:
                        sender_scores[sender] = score

            # Sort by score
            sorted_senders = sorted(
                sender_scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            return sorted_senders[:top_k]

        except Exception:
            return []

    def get_stats(self) -> dict:
        """Get graph statistics.

        Returns:
            Dictionary with statistics
        """
        total = len(self._relationships)
        family_count = sum(1 for r in self._relationships.values() if r.is_family)
        total_messages = sum(r.message_count for r in self._relationships.values())

        source_counts: dict[str, int] = {}
        for rel in self._relationships.values():
            for source in rel.sources:
                source_counts[source] = source_counts.get(source, 0) + 1

        return {
            "total_relationships": total,
            "family_members": family_count,
            "total_messages": total_messages,
            "by_source": source_counts,
        }

    def export_to_dict(self) -> dict:
        """Export graph to dictionary for serialization.

        Returns:
            Dictionary representation of the graph
        """
        return {
            name: {
                "contact_name": rel.contact_name,
                "message_count": rel.message_count,
                "call_count": rel.call_count,
                "first_interaction": rel.first_interaction.isoformat() if rel.first_interaction else None,
                "last_interaction": rel.last_interaction.isoformat() if rel.last_interaction else None,
                "interaction_score": rel.interaction_score,
                "relationship_types": rel.relationship_types,
                "sources": rel.sources,
                "is_family": rel.is_family,
            }
            for name, rel in self._relationships.items()
        }
