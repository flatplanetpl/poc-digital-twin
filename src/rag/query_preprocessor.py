"""Query preprocessor for extracting filters from natural language queries."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Tuple


@dataclass
class PreprocessedQuery:
    """Result of query preprocessing."""

    clean_query: str
    person_filter: str | None = None
    date_range: Tuple[datetime, datetime] | None = None
    source_filter: str | None = None
    extracted_filters: dict = field(default_factory=dict)


class QueryPreprocessor:
    """Preprocesses queries to extract person/date/source filters.

    Extracts implicit filters from natural language queries like:
    - "messages from Ewa about vacation" -> person_filter="Ewa"
    - "what did John say about the project" -> person_filter="John"
    - "conversations in December 2021" -> date_range=(2021-12-01, 2021-12-31)
    - "emails from last week" -> source_filter="email", date_range=...
    """

    # Person extraction patterns (Polish and English)
    PERSON_PATTERNS = [
        # English patterns
        r"(?:from|by|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:said|wrote|mentioned|told)\s+(?:by\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|wrote|mentioned|told)",
        r"conversation(?:s)?\s+with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"chat(?:s)?\s+with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        # Polish patterns
        r"(?:od|z)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)",
        r"(?:powiedział|napisał|wspomniał|mówił)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)",
        r"([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)\s+(?:powiedział|napisał|wspomniał|mówił)",
        r"rozmow(?:a|y)\s+z\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)",
        r"wiadomości\s+od\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)",
    ]

    # Month names (Polish and English)
    MONTHS = {
        # English
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        # Polish
        "stycznia": 1, "styczeń": 1, "styczen": 1,
        "lutego": 2, "luty": 2,
        "marca": 3, "marzec": 3,
        "kwietnia": 4, "kwiecień": 4, "kwiecien": 4,
        "maja": 5, "maj": 5,
        "czerwca": 6, "czerwiec": 6,
        "lipca": 7, "lipiec": 7,
        "sierpnia": 8, "sierpień": 8, "sierpien": 8,
        "września": 9, "wrzesień": 9, "wrzesien": 9,
        "października": 10, "październik": 10, "pazdziernik": 10,
        "listopada": 11, "listopad": 11,
        "grudnia": 12, "grudzień": 12, "grudzien": 12,
    }

    # Date extraction patterns
    DATE_PATTERNS = [
        # "in December 2021", "w grudniu 2021"
        (r"(?:in|w)\s+(\w+)\s+(\d{4})", "month_year"),
        # "from December 2021", "od grudnia 2021"
        (r"(?:from|od)\s+(\w+)\s+(\d{4})", "month_year"),
        # "during December 2021"
        (r"(?:during|podczas)\s+(\w+)\s+(\d{4})", "month_year"),
        # "last week/month/year"
        (r"(?:last|poprzedni(?:ego|m)?|zeszły|zeszłym)\s+(week|month|year|tydzień|tygodniu|miesiąc|miesiącu|rok|roku)", "relative"),
        # "this week/month/year"
        (r"(?:this|w tym|tym)\s+(week|month|year|tygodniu|miesiącu|roku)", "relative_this"),
        # "2021-12" or "12/2021"
        (r"(\d{4})-(\d{1,2})", "year_month"),
        (r"(\d{1,2})/(\d{4})", "month_year_num"),
    ]

    # Source type patterns
    SOURCE_PATTERNS = [
        (r"\b(?:email|e-mail|mail|maile|emaile)\b", "email"),
        (r"\b(?:messenger|facebook|fb)\b", "messenger"),
        (r"\b(?:whatsapp|wa)\b", "whatsapp"),
        (r"\b(?:notatk[ai]|notes?)\b", "text"),
    ]

    def preprocess(self, query: str) -> PreprocessedQuery:
        """Extract filters and clean query.

        Args:
            query: Original user query

        Returns:
            PreprocessedQuery with extracted filters and cleaned query
        """
        result = PreprocessedQuery(clean_query=query)
        extracted = {}

        # Extract person filter
        person, query_without_person = self._extract_person(query)
        if person:
            result.person_filter = person
            result.clean_query = query_without_person
            extracted["person"] = person

        # Extract date range
        date_range, query_without_date = self._extract_date_range(result.clean_query)
        if date_range:
            result.date_range = date_range
            result.clean_query = query_without_date
            extracted["date_range"] = f"{date_range[0].date()} to {date_range[1].date()}"

        # Extract source filter
        source, query_without_source = self._extract_source(result.clean_query)
        if source:
            result.source_filter = source
            result.clean_query = query_without_source
            extracted["source"] = source

        # Clean up the query
        result.clean_query = self._clean_query(result.clean_query)
        result.extracted_filters = extracted

        return result

    def _extract_person(self, query: str) -> Tuple[str | None, str]:
        """Extract person name from query.

        Args:
            query: Input query

        Returns:
            Tuple of (person_name or None, query with person reference removed)
        """
        for pattern in self.PERSON_PATTERNS:
            match = re.search(pattern, query)
            if match:
                person = match.group(1)
                # Don't extract common words that might match
                if person.lower() not in {"the", "a", "an", "to", "do", "co", "jak", "i"}:
                    # Remove the matched portion from query
                    clean_query = re.sub(pattern, "", query, count=1)
                    return person, clean_query
        return None, query

    def _extract_date_range(
        self,
        query: str,
    ) -> Tuple[Tuple[datetime, datetime] | None, str]:
        """Extract date range from query.

        Args:
            query: Input query

        Returns:
            Tuple of ((start_date, end_date) or None, query with date reference removed)
        """
        query_lower = query.lower()

        for pattern, pattern_type in self.DATE_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                date_range = self._parse_date_match(match, pattern_type)
                if date_range:
                    # Remove the matched portion
                    clean_query = re.sub(pattern, "", query, flags=re.IGNORECASE, count=1)
                    return date_range, clean_query

        return None, query

    def _parse_date_match(
        self,
        match: re.Match,
        pattern_type: str,
    ) -> Tuple[datetime, datetime] | None:
        """Parse date match into date range.

        Args:
            match: Regex match object
            pattern_type: Type of pattern matched

        Returns:
            Tuple of (start_date, end_date) or None
        """
        now = datetime.now()

        if pattern_type == "month_year":
            month_str = match.group(1).lower()
            year = int(match.group(2))
            month = self.MONTHS.get(month_str)
            if month:
                return self._month_range(year, month)

        elif pattern_type == "year_month":
            year = int(match.group(1))
            month = int(match.group(2))
            if 1 <= month <= 12:
                return self._month_range(year, month)

        elif pattern_type == "month_year_num":
            month = int(match.group(1))
            year = int(match.group(2))
            if 1 <= month <= 12:
                return self._month_range(year, month)

        elif pattern_type == "relative":
            period = match.group(1).lower()
            if period in ("week", "tydzień", "tygodniu"):
                start = now - timedelta(days=7)
                return (start, now)
            elif period in ("month", "miesiąc", "miesiącu"):
                start = now - timedelta(days=30)
                return (start, now)
            elif period in ("year", "rok", "roku"):
                start = now - timedelta(days=365)
                return (start, now)

        elif pattern_type == "relative_this":
            period = match.group(1).lower()
            if period in ("week", "tygodniu"):
                # Start of current week (Monday)
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                return (start, now)
            elif period in ("month", "miesiącu"):
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                return (start, now)
            elif period in ("year", "roku"):
                start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                return (start, now)

        return None

    def _month_range(
        self,
        year: int,
        month: int,
    ) -> Tuple[datetime, datetime]:
        """Get date range for a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Tuple of (start_of_month, end_of_month)
        """
        start = datetime(year, month, 1)
        # End of month
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        return (start, end)

    def _extract_source(self, query: str) -> Tuple[str | None, str]:
        """Extract source type from query.

        Args:
            query: Input query

        Returns:
            Tuple of (source_type or None, query with source reference removed)
        """
        query_lower = query.lower()

        for pattern, source_type in self.SOURCE_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                clean_query = re.sub(pattern, "", query, flags=re.IGNORECASE, count=1)
                return source_type, clean_query

        return None, query

    def _clean_query(self, query: str) -> str:
        """Clean up query after filter extraction.

        Args:
            query: Query with filters removed

        Returns:
            Cleaned query string
        """
        # Remove extra whitespace
        query = re.sub(r"\s+", " ", query)
        # Remove leading/trailing whitespace
        query = query.strip()
        # Remove dangling prepositions at start
        query = re.sub(r"^(?:from|by|with|in|od|z|w|o)\s+", "", query, flags=re.IGNORECASE)
        # Remove trailing punctuation that might be left over
        query = re.sub(r"[,;:]+$", "", query)
        return query.strip()
