"""Parser for Google Takeout saved places data."""

import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.exceptions import InvalidFileError, TakeoutParseError
from app.models.place import Coordinates, ParsedPlace


class TakeoutParser:
    """Parser for Google Takeout saved places exports."""

    # Patterns for extracting place identifiers from URLs
    CID_PATTERN = re.compile(r"[?&]cid=(\d+)")
    PLACE_ID_PATTERN = re.compile(r"/place/[^/]+/data=.*!1s([\w-]+)")
    FTID_PATTERN = re.compile(r"ftid=([\w:]+)")

    # Known saved list file patterns in Takeout
    SAVED_LIST_PATTERNS = [
        "Saved Places.json",
        "Want to go.json",
        "Starred Places.json",
        "Favourites.json",
        "Favorites.json",
        "Labelled.json",
        "Labeled.json",
    ]

    def parse_file(self, file_content: bytes, filename: str) -> list[ParsedPlace]:
        """Parse a file (ZIP or JSON) and return list of places."""
        if filename.lower().endswith(".zip"):
            return self._parse_zip(file_content)
        elif filename.lower().endswith(".json") or filename.lower().endswith(".geojson"):
            return self._parse_json(file_content, filename)
        else:
            raise InvalidFileError(
                message="Unsupported file type",
                details="Please upload a ZIP or JSON file from Google Takeout",
            )

    def _parse_zip(self, zip_content: bytes) -> list[ParsedPlace]:
        """Parse a Google Takeout ZIP file."""
        places: list[ParsedPlace] = []

        try:
            with zipfile.ZipFile(BytesIO(zip_content), "r") as zf:
                json_files = self._find_json_files(zf)

                if not json_files:
                    raise TakeoutParseError(
                        message="No saved places files found in ZIP",
                        details="Expected files like 'Saved Places.json' in the archive",
                    )

                for json_path in json_files:
                    try:
                        content = zf.read(json_path)
                        list_name = Path(json_path).stem
                        file_places = self._parse_json(content, json_path, list_name)
                        places.extend(file_places)
                    except Exception as e:
                        # Log but continue with other files
                        print(f"Warning: Failed to parse {json_path}: {e}")
                        continue

        except zipfile.BadZipFile:
            raise InvalidFileError(
                message="Invalid ZIP file",
                details="The uploaded file is not a valid ZIP archive",
            )

        return places

    def _find_json_files(self, zf: zipfile.ZipFile) -> list[str]:
        """Find JSON files containing saved places in the ZIP."""
        json_files: list[str] = []

        for name in zf.namelist():
            # Skip directories
            if name.endswith("/"):
                continue

            # Check if it's a JSON file
            if not name.lower().endswith(".json"):
                continue

            # Check if it matches known patterns or is in a Maps/Saved directory
            basename = Path(name).name
            if any(pattern.lower() in basename.lower() for pattern in self.SAVED_LIST_PATTERNS):
                json_files.append(name)
            elif "maps" in name.lower() and "saved" in name.lower():
                json_files.append(name)
            elif "your places" in name.lower():
                json_files.append(name)

        return json_files

    def _parse_json(
        self, content: bytes, filename: str, source_list: str | None = None
    ) -> list[ParsedPlace]:
        """Parse a JSON/GeoJSON file."""
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise TakeoutParseError(
                message=f"Invalid JSON in {filename}",
                details=str(e),
            )

        # Determine format and parse accordingly
        if self._is_geojson(data):
            return self._parse_geojson(data, source_list)
        elif isinstance(data, list):
            return self._parse_places_list(data, source_list)
        else:
            raise TakeoutParseError(
                message=f"Unrecognized format in {filename}",
                details="Expected GeoJSON FeatureCollection or array of places",
            )

    def _is_geojson(self, data: Any) -> bool:
        """Check if data is a GeoJSON FeatureCollection."""
        return (
            isinstance(data, dict)
            and data.get("type") == "FeatureCollection"
            and "features" in data
        )

    def _parse_geojson(
        self, data: dict[str, Any], source_list: str | None = None
    ) -> list[ParsedPlace]:
        """Parse GeoJSON FeatureCollection format."""
        places: list[ParsedPlace] = []

        for feature in data.get("features", []):
            try:
                place = self._parse_geojson_feature(feature, source_list)
                if place:
                    places.append(place)
            except Exception as e:
                print(f"Warning: Failed to parse feature: {e}")
                continue

        return places

    def _parse_geojson_feature(
        self, feature: dict[str, Any], source_list: str | None = None
    ) -> ParsedPlace | None:
        """Parse a single GeoJSON feature."""
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        # Extract Google Maps URL (try multiple key variations)
        google_maps_url = (
            properties.get("google_maps_url")
            or properties.get("Google Maps URL")
            or properties.get("url")
            or properties.get("URL")
            or ""
        )

        if not google_maps_url:
            return None

        # Extract location info (try both lowercase and capitalized keys)
        location = properties.get("location") or properties.get("Location") or {}
        name = location.get("name") or location.get("Business Name") or ""
        address = location.get("address") or location.get("Address") or ""

        # Fallback to properties directly
        if not name:
            name = properties.get("name", properties.get("Name", ""))
        if not address:
            address = properties.get("address", properties.get("Address", ""))

        if not name:
            # Last resort: extract from URL
            name = self._extract_name_from_url(google_maps_url) or "Unknown Place"

        # Extract coordinates
        coordinates = None
        if geometry.get("type") == "Point" and geometry.get("coordinates"):
            coords = geometry["coordinates"]
            if len(coords) >= 2:
                coordinates = Coordinates(longitude=coords[0], latitude=coords[1])

        # Extract place identifiers from URL
        place_id = self._extract_place_id(google_maps_url)
        cid = self._extract_cid(google_maps_url)

        return ParsedPlace(
            name=name,
            address=address or None,
            google_maps_url=google_maps_url,
            place_id=place_id,
            cid=cid,
            coordinates=coordinates,
            source_list=source_list,
        )

    def _parse_places_list(
        self, data: list[Any], source_list: str | None = None
    ) -> list[ParsedPlace]:
        """Parse a simple list of place objects."""
        places: list[ParsedPlace] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                google_maps_url = item.get("url", item.get("Google Maps URL", ""))
                if not google_maps_url:
                    continue

                name = item.get("name", item.get("title", ""))
                if not name:
                    name = self._extract_name_from_url(google_maps_url) or "Unknown Place"

                place = ParsedPlace(
                    name=name,
                    address=item.get("address"),
                    google_maps_url=google_maps_url,
                    place_id=self._extract_place_id(google_maps_url),
                    cid=self._extract_cid(google_maps_url),
                    coordinates=None,
                    source_list=source_list,
                )
                places.append(place)
            except Exception as e:
                print(f"Warning: Failed to parse place item: {e}")
                continue

        return places

    # Pattern for extracting hex IDs from data parameter (e.g., !1s0x0:0xfa0b1bc4c1af47da)
    DATA_HEX_PATTERN = re.compile(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)")

    def _extract_place_id(self, url: str) -> str | None:
        """Extract place_id from a Google Maps URL."""
        # Try data parameter format with named place_id
        match = self.PLACE_ID_PATTERN.search(url)
        if match:
            return match.group(1)

        # Try hex format in data parameter (e.g., !1s0x0:0xfa0b1bc4c1af47da)
        match = self.DATA_HEX_PATTERN.search(url)
        if match:
            return match.group(1)

        # Try ftid parameter
        match = self.FTID_PATTERN.search(url)
        if match:
            ftid = match.group(1)
            # ftid format is often "0x...:0x..." - convert to place_id format
            if ":" in ftid:
                return ftid

        # Try query parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "place_id" in params:
            return params["place_id"][0]

        return None

    def _extract_cid(self, url: str) -> str | None:
        """Extract CID (customer ID) from a Google Maps URL."""
        match = self.CID_PATTERN.search(url)
        if match:
            return match.group(1)
        return None

    def _extract_name_from_url(self, url: str) -> str | None:
        """Try to extract a place name from the URL path."""
        parsed = urlparse(url)
        path = parsed.path

        # URLs often have format /maps/place/Place+Name/...
        if "/place/" in path:
            parts = path.split("/place/")
            if len(parts) > 1:
                name_part = parts[1].split("/")[0]
                # Decode URL encoding
                name = name_part.replace("+", " ").replace("%20", " ")
                return name if name else None

        return None


# Global parser instance
takeout_parser = TakeoutParser()
