"""Tests for export service."""

import json

import pytest

from app.models.place import BusinessStatus, Coordinates, PlaceWithStatus
from app.services.export_service import ExportService


class TestExportService:
    """Tests for ExportService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ExportService()
        self.places = [
            PlaceWithStatus(
                name="Open Coffee Shop",
                address="123 Main St",
                google_maps_url="http://maps.google.com/?cid=111",
                business_status=BusinessStatus.OPERATIONAL,
                coordinates=Coordinates(latitude=45.5, longitude=-122.6),
            ),
            PlaceWithStatus(
                name="Temporarily Closed Restaurant",
                address="456 Oak Ave",
                google_maps_url="http://maps.google.com/?cid=222",
                business_status=BusinessStatus.CLOSED_TEMPORARILY,
            ),
            PlaceWithStatus(
                name="Permanently Closed Bar",
                address="789 Elm St",
                google_maps_url="http://maps.google.com/?cid=333",
                business_status=BusinessStatus.CLOSED_PERMANENTLY,
            ),
            PlaceWithStatus(
                name="Unknown Status Place",
                google_maps_url="http://maps.google.com/?cid=444",
                business_status=BusinessStatus.UNKNOWN,
                api_error="Could not determine status",
            ),
        ]

    def test_export_json_all_places(self):
        """Test exporting all places as JSON."""
        result = self.service.export_json(self.places)
        data = json.loads(result)

        assert data["total_count"] == 4
        assert len(data["places"]) == 4
        assert data["filter_applied"] is None

    def test_export_json_filtered(self):
        """Test exporting filtered places as JSON."""
        result = self.service.export_json(
            self.places, filter_status=[BusinessStatus.CLOSED_PERMANENTLY]
        )
        data = json.loads(result)

        assert data["total_count"] == 1
        assert data["places"][0]["name"] == "Permanently Closed Bar"
        assert data["filter_applied"] == ["CLOSED_PERMANENTLY"]

    def test_export_json_multiple_filters(self):
        """Test exporting with multiple status filters."""
        result = self.service.export_json(
            self.places,
            filter_status=[BusinessStatus.CLOSED_TEMPORARILY, BusinessStatus.CLOSED_PERMANENTLY],
        )
        data = json.loads(result)

        assert data["total_count"] == 2

    def test_export_json_pretty(self):
        """Test that pretty JSON has indentation."""
        pretty = self.service.export_json(self.places, pretty=True)
        compact = self.service.export_json(self.places, pretty=False)

        assert len(pretty) > len(compact)
        assert "\n" in pretty

    def test_export_csv(self):
        """Test exporting as CSV."""
        result = self.service.export_csv(self.places)

        # Check header
        lines = result.strip().split("\n")
        assert "Name" in lines[0]
        assert "Business Status" in lines[0]

        # Check data rows
        assert len(lines) == 5  # header + 4 places
        assert "Open Coffee Shop" in result
        assert "OPERATIONAL" in result

    def test_export_csv_filtered(self):
        """Test exporting filtered CSV."""
        result = self.service.export_csv(self.places, filter_status=[BusinessStatus.OPERATIONAL])

        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + 1 place

    def test_export_csv_includes_coordinates(self):
        """Test that CSV includes coordinates when available."""
        result = self.service.export_csv(self.places)

        assert "45.5" in result  # latitude
        assert "-122.6" in result  # longitude

    def test_export_summary(self):
        """Test generating summary."""
        summary = self.service.export_summary(self.places)

        assert summary["total_places"] == 4
        assert summary["status_counts"]["OPERATIONAL"] == 1
        assert summary["status_counts"]["CLOSED_TEMPORARILY"] == 1
        assert summary["status_counts"]["CLOSED_PERMANENTLY"] == 1
        assert summary["status_counts"]["UNKNOWN"] == 1

    def test_export_summary_places_by_status(self):
        """Test that summary includes places grouped by status."""
        summary = self.service.export_summary(self.places)

        assert len(summary["places_by_status"]["OPERATIONAL"]) == 1
        assert summary["places_by_status"]["OPERATIONAL"][0]["name"] == "Open Coffee Shop"

    def test_export_empty_list(self):
        """Test exporting empty list."""
        result = self.service.export_json([])
        data = json.loads(result)

        assert data["total_count"] == 0
        assert data["places"] == []

    def test_place_dict_includes_optional_fields(self):
        """Test that optional fields are included when present."""
        result = self.service.export_json(self.places)
        data = json.loads(result)

        # Find place with coordinates
        open_place = next(p for p in data["places"] if p["name"] == "Open Coffee Shop")
        assert "coordinates" in open_place
        assert open_place["coordinates"]["latitude"] == 45.5

        # Find place with api_error
        unknown_place = next(p for p in data["places"] if p["name"] == "Unknown Status Place")
        assert "api_error" in unknown_place
