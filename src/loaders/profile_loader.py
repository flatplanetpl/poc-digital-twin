"""Loader for Facebook profile information JSON exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class ProfileLoader(BaseLoader):
    """Loader for Facebook profile information exports.

    Parses profile_information.json from Facebook "Download Your Information".
    Extracts:
    - Personal info: name, email, phone, birthday, gender
    - Location: current city, hometown
    - Relationships: status, partner, family members
    - Work history: employers with dates
    - Education history

    Creates high-priority documents for self-context in RAG queries.
    """

    def __init__(self):
        """Initialize Profile loader."""
        super().__init__(source_type="profile")

    def supported_extensions(self) -> list[str]:
        return [".json"]

    def _fix_encoding(self, text: str) -> str:
        """Fix Facebook's mojibake encoding (latin-1 stored as UTF-8).

        Args:
            text: Text with potential encoding issues

        Returns:
            Properly decoded UTF-8 text
        """
        if not isinstance(text, str):
            return str(text) if text else ""
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    def _parse_file(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse Facebook profile information JSON file.

        Only processes files named 'profile_information.json'.

        Args:
            file_path: Path to the JSON file

        Yields:
            Tuple of (content, metadata) for profile document
        """
        # Only process profile_information.json
        if file_path.name != "profile_information.json":
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

        profile = data.get("profile_v2", {})
        if not profile:
            return

        # Extract profile components
        content_parts = []
        metadata = {
            "profile_type": "self",
            "document_category": "profile",
        }

        # Name
        name_data = profile.get("name", {})
        full_name = self._fix_encoding(name_data.get("full_name", ""))
        if full_name:
            content_parts.append(f"Name: {full_name}")
            metadata["full_name"] = full_name
            metadata["first_name"] = self._fix_encoding(name_data.get("first_name", ""))
            metadata["last_name"] = self._fix_encoding(name_data.get("last_name", ""))

        # Email
        emails_data = profile.get("emails", {})
        emails = emails_data.get("emails", [])
        if emails:
            primary_email = emails[0] if isinstance(emails[0], str) else emails[0].get("email", "")
            content_parts.append(f"Email: {primary_email}")
            metadata["email"] = primary_email

        # Phone
        phone_numbers = profile.get("phone_numbers", [])
        if phone_numbers:
            primary_phone = phone_numbers[0].get("phone_number", "")
            content_parts.append(f"Phone: {primary_phone}")
            metadata["phone"] = primary_phone

        # Birthday
        birthday = profile.get("birthday", {})
        if birthday.get("year"):
            bday_str = f"{birthday.get('year')}-{birthday.get('month', 1):02d}-{birthday.get('day', 1):02d}"
            content_parts.append(f"Birthday: {bday_str}")
            metadata["birthday"] = bday_str

        # Gender
        gender_data = profile.get("gender", {})
        gender = gender_data.get("gender_option", "")
        if gender:
            content_parts.append(f"Gender: {gender}")
            metadata["gender"] = gender

        # Current city
        current_city = profile.get("current_city", {})
        city_name = self._fix_encoding(current_city.get("name", ""))
        if city_name:
            content_parts.append(f"Current city: {city_name}")
            metadata["city"] = city_name

        # Hometown
        hometown = profile.get("hometown", {})
        hometown_name = self._fix_encoding(hometown.get("name", ""))
        if hometown_name:
            content_parts.append(f"Hometown: {hometown_name}")
            metadata["hometown"] = hometown_name

        # Relationship
        relationship = profile.get("relationship", {})
        rel_status = self._fix_encoding(relationship.get("status", ""))
        rel_partner = self._fix_encoding(relationship.get("partner", ""))
        if rel_status:
            rel_text = f"Relationship: {rel_status}"
            if rel_partner:
                rel_text += f" with {rel_partner}"
            content_parts.append(rel_text)
            metadata["relationship_status"] = rel_status
            if rel_partner:
                metadata["partner"] = rel_partner

        # Family members
        family_members = profile.get("family_members", [])
        if family_members:
            family_list = []
            for member in family_members:
                name = self._fix_encoding(member.get("name", ""))
                relation = self._fix_encoding(member.get("relation", ""))
                if name and relation:
                    family_list.append(f"{name} ({relation})")
            if family_list:
                content_parts.append(f"Family: {', '.join(family_list)}")
                metadata["family_members"] = json.dumps(
                    [{"name": self._fix_encoding(m.get("name", "")),
                      "relation": self._fix_encoding(m.get("relation", ""))}
                     for m in family_members],
                    ensure_ascii=False
                )

        # Work experience
        work_experiences = profile.get("work_experiences", [])
        if work_experiences:
            work_list = []
            for job in work_experiences:
                employer = self._fix_encoding(job.get("employer", ""))
                if employer:
                    work_entry = employer
                    start_ts = job.get("start_timestamp")
                    end_ts = job.get("end_timestamp")
                    if start_ts:
                        start_date = datetime.fromtimestamp(start_ts).strftime("%Y")
                        end_date = datetime.fromtimestamp(end_ts).strftime("%Y") if end_ts else "present"
                        work_entry += f" ({start_date}-{end_date})"
                    work_list.append(work_entry)
            if work_list:
                content_parts.append(f"Work: {', '.join(work_list)}")
                metadata["work_history"] = json.dumps(
                    [{"employer": self._fix_encoding(j.get("employer", "")),
                      "start": j.get("start_timestamp"),
                      "end": j.get("end_timestamp")}
                     for j in work_experiences if j.get("employer")],
                    ensure_ascii=False
                )

        # Education
        education = profile.get("education_experiences", [])
        if education:
            edu_list = []
            for edu in education:
                school = self._fix_encoding(edu.get("name", ""))
                if school:
                    edu_list.append(school)
            if edu_list:
                content_parts.append(f"Education: {', '.join(edu_list)}")
                metadata["education"] = json.dumps(edu_list, ensure_ascii=False)

        # Username
        username = profile.get("username", "")
        if username:
            content_parts.append(f"Username: {username}")
            metadata["username"] = username

        # Favorite quotes
        quotes = self._fix_encoding(profile.get("favorite_quotes", ""))
        if quotes:
            content_parts.append(f"Favorite quotes: {quotes}")

        # Registration date
        reg_timestamp = profile.get("registration_timestamp")
        if reg_timestamp:
            reg_date = datetime.fromtimestamp(reg_timestamp).isoformat()
            metadata["registration_date"] = reg_date
            metadata["date"] = reg_date

        if not content_parts:
            return

        content = "My Profile Information:\n" + "\n".join(content_parts)

        yield content, metadata
