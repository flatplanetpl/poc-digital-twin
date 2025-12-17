"""Loader for Facebook location data exports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base import BaseLoader


class LocationLoader(BaseLoader):
    """Loader for Facebook location data exports.

    Parses:
    - logged_information/location/device_location.json
    - logged_information/location/primary_location.json
    - logged_information/location/primary_public_location.json
    - logged_information/other_logged_information/locations_of_interest.json

    Creates documents with location context for temporal/spatial queries.
    """

    def __init__(self):
        """Initialize Location loader."""
        super().__init__(source_type="location")

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
        """Parse Facebook location JSON file.

        Args:
            file_path: Path to the JSON file

        Yields:
            Tuple of (content, metadata) for each location entry
        """
        filename = file_path.name

        # Route to appropriate parser
        if filename == "device_location.json":
            yield from self._parse_device_location(file_path)
        elif filename == "primary_location.json":
            yield from self._parse_primary_location(file_path)
        elif filename == "primary_public_location.json":
            yield from self._parse_primary_location(file_path)
        elif filename == "locations_of_interest.json":
            yield from self._parse_locations_of_interest(file_path)

    def _load_json(self, file_path: Path) -> dict | list | None:
        """Load JSON file with encoding fallback."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    return json.load(f)
            except Exception:
                return None

    def _parse_device_location(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse device location history.

        Args:
            file_path: Path to device_location.json

        Yields:
            Tuple of (content, metadata) for each location record
        """
        data = self._load_json(file_path)
        if not data:
            return

        locations = data.get("location_history_v2", data.get("location_history", []))
        if not locations:
            return

        # Group locations by day for more meaningful documents
        daily_locations: dict[str, list] = {}

        for loc in locations:
            timestamp = loc.get("timestamp", 0)
            if not timestamp:
                continue

            dt = datetime.fromtimestamp(timestamp)
            day_key = dt.strftime("%Y-%m-%d")

            if day_key not in daily_locations:
                daily_locations[day_key] = []

            location_info = {
                "timestamp": dt,
                "latitude": loc.get("coordinate", {}).get("latitude"),
                "longitude": loc.get("coordinate", {}).get("longitude"),
                "city": self._fix_encoding(loc.get("city", "")),
                "region": self._fix_encoding(loc.get("region", "")),
                "country": self._fix_encoding(loc.get("country", "")),
            }
            daily_locations[day_key].append(location_info)

        for day, locs in daily_locations.items():
            # Create summary for the day
            cities = list(set(l["city"] for l in locs if l["city"]))
            regions = list(set(l["region"] for l in locs if l["region"]))

            content_parts = [f"Location history for {day}:"]
            if cities:
                content_parts.append(f"Cities visited: {', '.join(cities)}")
            if regions:
                content_parts.append(f"Regions: {', '.join(regions)}")
            content_parts.append(f"Number of location records: {len(locs)}")

            content = "\n".join(content_parts)

            metadata = {
                "date": f"{day}T00:00:00",
                "location_type": "device_history",
                "document_category": "location",
                "record_count": len(locs),
            }

            if cities:
                metadata["cities"] = ", ".join(cities[:5])  # Limit for metadata size
            if regions:
                metadata["regions"] = ", ".join(regions[:3])

            # Add coordinates from first location
            first_loc = locs[0]
            if first_loc["latitude"] and first_loc["longitude"]:
                metadata["latitude"] = first_loc["latitude"]
                metadata["longitude"] = first_loc["longitude"]

            yield content, metadata

    def _parse_primary_location(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse primary/home location.

        Args:
            file_path: Path to primary_location.json

        Yields:
            Tuple of (content, metadata) for primary location
        """
        data = self._load_json(file_path)
        if not data:
            return

        # Try different possible structures
        location_data = (
            data.get("primary_location_v2", {}) or
            data.get("primary_location", {}) or
            data.get("primary_public_location_v2", {}) or
            data
        )

        city = self._fix_encoding(location_data.get("city", ""))
        region = self._fix_encoding(location_data.get("region", ""))
        country = self._fix_encoding(location_data.get("country", ""))
        zipcode = location_data.get("zipcode", "")

        if not any([city, region, country]):
            return

        content_parts = ["My primary location:"]
        if city:
            content_parts.append(f"City: {city}")
        if region:
            content_parts.append(f"Region: {region}")
        if country:
            content_parts.append(f"Country: {country}")
        if zipcode:
            content_parts.append(f"Zip code: {zipcode}")

        content = "\n".join(content_parts)

        metadata = {
            "location_type": "primary",
            "document_category": "location",
            "date": datetime.now().isoformat(),
        }

        if city:
            metadata["city"] = city
        if region:
            metadata["region"] = region
        if country:
            metadata["country"] = country

        yield content, metadata

    def _parse_locations_of_interest(self, file_path: Path) -> Iterator[tuple[str, dict]]:
        """Parse locations of interest (inferred by Facebook).

        Args:
            file_path: Path to locations_of_interest.json

        Yields:
            Tuple of (content, metadata) for each location of interest
        """
        data = self._load_json(file_path)
        if not data:
            return

        locations = data.get("inferred_city_v2", data.get("inferred_cities", []))
        if not locations:
            return

        for loc in locations:
            city = self._fix_encoding(loc.get("string_map_data", {}).get("City", {}).get("value", ""))
            if not city:
                city = self._fix_encoding(loc.get("city", ""))

            if not city:
                continue

            content = f"Location of interest: {city}"

            # Try to get timestamp
            timestamp_data = loc.get("string_map_data", {}).get("Start Time", {})
            timestamp = timestamp_data.get("timestamp", 0)

            metadata = {
                "location_type": "interest",
                "document_category": "location",
                "city": city,
            }

            if timestamp:
                metadata["date"] = datetime.fromtimestamp(timestamp).isoformat()
            else:
                metadata["date"] = datetime.now().isoformat()

            yield content, metadata
