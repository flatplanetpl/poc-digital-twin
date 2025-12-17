"""Loader for Facebook ads interests exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class AdsInterestsLoader(BaseLoader):
    """Loader for Facebook advertising interests exports.

    Parses:
    - logged_information/other_logged_information/ads_interests.json

    Creates a document with user interests for personality context in RAG.
    """

    def __init__(self):
        """Initialize Ads Interests loader."""
        super().__init__(source_type="interests")

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def _fix_encoding(self, text: str) -> str:
        """Fix Facebook's mojibake encoding."""
        if not isinstance(text, str):
            return str(text) if text else ""
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Facebook ads interests JSON file.

        Args:
            file_path: Path to the JSON file

        Yields:
            Tuple of (content, metadata) for interests document
        """
        if file_path.name != "ads_interests.json":
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    data = json.load(f)
            except Exception:
                return

        # Try different possible structures
        topics = data.get("topics_v2", data.get("topics", []))
        if not topics:
            return

        # Clean and fix encoding for all topics
        cleaned_topics = []
        for topic in topics:
            if isinstance(topic, str):
                cleaned = self._fix_encoding(topic)
                # Remove category annotations like "(food and drink)"
                if "(" in cleaned:
                    cleaned = cleaned.split("(")[0].strip()
                cleaned_topics.append(cleaned)

        if not cleaned_topics:
            return

        # Categorize topics for better context
        categories = self._categorize_topics(cleaned_topics)

        content_parts = ["My interests (based on Facebook activity):\n"]

        for category, items in categories.items():
            if items:
                content_parts.append(f"{category}: {', '.join(items[:15])}")

        content_parts.append(f"\nTotal interest topics: {len(cleaned_topics)}")

        content = "\n".join(content_parts)

        metadata = {
            "date": datetime.now().isoformat(),
            "document_category": "interests",
            "topic_count": len(cleaned_topics),
            "categories": ", ".join(categories.keys()),
        }

        yield content, metadata

    def _categorize_topics(self, topics: list[str]) -> dict[str, list[str]]:
        """Categorize topics into groups.

        Args:
            topics: List of interest topics

        Returns:
            Dictionary of category -> topic list
        """
        categories = {
            "Technology": [],
            "Business & Finance": [],
            "Entertainment": [],
            "Food & Drink": [],
            "Sports & Fitness": [],
            "Travel": [],
            "Shopping": [],
            "Science & Education": [],
            "Other": [],
        }

        tech_keywords = [
            "tech", "software", "app", "computer", "digital", "ai", "data",
            "programming", "developer", "android", "ios", "apple", "google",
            "microsoft", "cloud", "startup", "saas", "api", "code", "geforce",
            "nvidia", "intel", "processor", "hardware", "electronics"
        ]

        business_keywords = [
            "business", "finance", "invest", "trading", "forex", "stock",
            "entrepreneur", "marketing", "management", "consulting", "bank",
            "money", "economic", "real estate", "etoro", "fxpro"
        ]

        entertainment_keywords = [
            "game", "gaming", "movie", "film", "music", "video", "stream",
            "netflix", "youtube", "spotify", "entertainment", "tv", "show",
            "cartoon", "anime", "comic"
        ]

        food_keywords = [
            "food", "restaurant", "cooking", "recipe", "cuisine", "beer",
            "wine", "coffee", "tea", "catering", "gastro", "chef", "drink",
            "brewery", "bar"
        ]

        sports_keywords = [
            "sport", "fitness", "gym", "running", "cycling", "football",
            "basketball", "tennis", "swimming", "yoga", "workout", "health"
        ]

        travel_keywords = [
            "travel", "vacation", "hotel", "flight", "tourism", "adventure",
            "destination", "trip", "booking"
        ]

        shopping_keywords = [
            "shop", "retail", "ecommerce", "amazon", "ebay", "fashion",
            "clothes", "buy", "sale", "discount", "black friday"
        ]

        science_keywords = [
            "science", "education", "research", "university", "physics",
            "chemistry", "biology", "math", "engineering", "academic",
            "history", "philosophy"
        ]

        for topic in topics:
            topic_lower = topic.lower()
            categorized = False

            if any(kw in topic_lower for kw in tech_keywords):
                categories["Technology"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in business_keywords):
                categories["Business & Finance"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in entertainment_keywords):
                categories["Entertainment"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in food_keywords):
                categories["Food & Drink"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in sports_keywords):
                categories["Sports & Fitness"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in travel_keywords):
                categories["Travel"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in shopping_keywords):
                categories["Shopping"].append(topic)
                categorized = True
            elif any(kw in topic_lower for kw in science_keywords):
                categories["Science & Education"].append(topic)
                categorized = True

            if not categorized:
                categories["Other"].append(topic)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
