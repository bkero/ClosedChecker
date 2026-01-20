"""Tests for the Google Takeout parser."""

import json
import zipfile
from io import BytesIO

import pytest

from app.core.exceptions import InvalidFileError, TakeoutParseError
from app.services.takeout_parser import TakeoutParser


class TestTakeoutParser:
    """Tests for TakeoutParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TakeoutParser()

    def test_parse_geojson_basic(self, sample_geojson_bytes):
        """Test parsing a basic GeoJSON file."""
        places = self.parser.parse_file(sample_geojson_bytes, "test.json")

        assert len(places) == 2
        assert places[0].name == "Test Coffee Shop"
        assert places[0].address == "123 Main St, Portland, OR 97201"
        assert places[0].cid == "12345678901234567890"

    def test_parse_geojson_extracts_place_id(self, sample_geojson_bytes):
        """Test that place_id is extracted from data URL format."""
        places = self.parser.parse_file(sample_geojson_bytes, "test.json")

        # Second place has data URL format
        assert places[1].name == "Test Restaurant"
        assert places[1].place_id == "0x0:0xabcdef1234567890"

    def test_parse_geojson_extracts_coordinates(self, sample_geojson_bytes):
        """Test that coordinates are extracted correctly."""
        places = self.parser.parse_file(sample_geojson_bytes, "test.json")

        assert places[0].coordinates is not None
        assert places[0].coordinates.longitude == -122.6784
        assert places[0].coordinates.latitude == 45.5152

    def test_parse_zip_file(self, sample_geojson):
        """Test parsing a ZIP file containing saved places."""
        # Create a ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Takeout/Maps (your places)/Saved Places.json", json.dumps(sample_geojson))
        zip_buffer.seek(0)

        places = self.parser.parse_file(zip_buffer.read(), "takeout.zip")

        assert len(places) == 2
        assert places[0].source_list == "Saved Places"

    def test_parse_zip_multiple_lists(self, sample_geojson):
        """Test parsing a ZIP with multiple saved lists."""
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Takeout/Maps (your places)/Saved Places.json", json.dumps(sample_geojson))
            zf.writestr("Takeout/Maps (your places)/Want to go.json", json.dumps(sample_geojson))
        zip_buffer.seek(0)

        places = self.parser.parse_file(zip_buffer.read(), "takeout.zip")

        assert len(places) == 4  # 2 places from each list

    def test_parse_invalid_file_type(self):
        """Test that invalid file types raise an error."""
        with pytest.raises(InvalidFileError):
            self.parser.parse_file(b"some content", "test.txt")

    def test_parse_invalid_json(self):
        """Test that invalid JSON raises an error."""
        with pytest.raises(TakeoutParseError):
            self.parser.parse_file(b"not valid json", "test.json")

    def test_parse_empty_features(self):
        """Test parsing GeoJSON with no features."""
        empty_geojson = json.dumps({"type": "FeatureCollection", "features": []}).encode("utf-8")

        places = self.parser.parse_file(empty_geojson, "test.json")
        assert len(places) == 0

    def test_extract_cid_from_url(self):
        """Test CID extraction from various URL formats."""
        assert self.parser._extract_cid("http://maps.google.com/?cid=12345") == "12345"
        assert self.parser._extract_cid("https://maps.google.com/?cid=67890&other=param") == "67890"
        assert self.parser._extract_cid("https://maps.google.com/place/test") is None

    def test_extract_place_id_from_data_url(self):
        """Test place_id extraction from data URL format."""
        url = "https://www.google.com/maps/place//data=!4m2!3m1!1s0x0:0xabcdef"
        assert self.parser._extract_place_id(url) == "0x0:0xabcdef"

    def test_feature_without_url_is_skipped(self):
        """Test that features without Google Maps URL are skipped."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "geometry": {"coordinates": [0, 0], "type": "Point"},
                    "properties": {"location": {"name": "No URL Place"}},
                    "type": "Feature",
                }
            ],
        }

        places = self.parser.parse_file(json.dumps(geojson).encode("utf-8"), "test.json")
        assert len(places) == 0
