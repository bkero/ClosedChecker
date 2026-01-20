"""Export service for places data in various formats."""

import csv
import io
import json
from datetime import UTC
from typing import Any

from app.models.place import BusinessStatus, PlaceWithStatus


class ExportService:
    """Service for exporting places data."""

    def export_json(
        self,
        places: list[PlaceWithStatus],
        filter_status: list[BusinessStatus] | None = None,
        pretty: bool = True,
    ) -> str:
        """
        Export places to JSON format.

        Args:
            places: List of places with status
            filter_status: Optional list of statuses to include
            pretty: Whether to format with indentation

        Returns:
            JSON string
        """
        filtered = self._filter_places(places, filter_status)

        data = {
            "exported_at": self._get_timestamp(),
            "total_count": len(filtered),
            "filter_applied": [s.value for s in filter_status] if filter_status else None,
            "places": [self._place_to_dict(p) for p in filtered],
        }

        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def export_csv(
        self,
        places: list[PlaceWithStatus],
        filter_status: list[BusinessStatus] | None = None,
    ) -> str:
        """
        Export places to CSV format.

        Args:
            places: List of places with status
            filter_status: Optional list of statuses to include

        Returns:
            CSV string
        """
        filtered = self._filter_places(places, filter_status)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "Name",
                "Address",
                "Business Status",
                "Google Maps URL",
                "Place ID",
                "Latitude",
                "Longitude",
                "Source List",
                "API Error",
            ]
        )

        # Data rows
        for place in filtered:
            lat = place.coordinates.latitude if place.coordinates else ""
            lng = place.coordinates.longitude if place.coordinates else ""

            writer.writerow(
                [
                    place.name,
                    place.address or "",
                    place.business_status.value,
                    place.google_maps_url,
                    place.place_id or "",
                    lat,
                    lng,
                    place.source_list or "",
                    place.api_error or "",
                ]
            )

        return output.getvalue()

    def export_summary(
        self,
        places: list[PlaceWithStatus],
    ) -> dict[str, Any]:
        """
        Generate a summary of places by status.

        Args:
            places: List of places with status

        Returns:
            Summary dictionary
        """
        status_counts: dict[str, int] = {
            BusinessStatus.OPERATIONAL.value: 0,
            BusinessStatus.CLOSED_TEMPORARILY.value: 0,
            BusinessStatus.CLOSED_PERMANENTLY.value: 0,
            BusinessStatus.UNKNOWN.value: 0,
        }

        places_by_status: dict[str, list[dict[str, Any]]] = {
            BusinessStatus.OPERATIONAL.value: [],
            BusinessStatus.CLOSED_TEMPORARILY.value: [],
            BusinessStatus.CLOSED_PERMANENTLY.value: [],
            BusinessStatus.UNKNOWN.value: [],
        }

        for place in places:
            status_key = place.business_status.value
            status_counts[status_key] += 1
            places_by_status[status_key].append(self._place_to_dict(place))

        return {
            "total_places": len(places),
            "status_counts": status_counts,
            "places_by_status": places_by_status,
        }

    def _filter_places(
        self,
        places: list[PlaceWithStatus],
        filter_status: list[BusinessStatus] | None,
    ) -> list[PlaceWithStatus]:
        """Filter places by status if specified."""
        if not filter_status:
            return places
        return [p for p in places if p.business_status in filter_status]

    def _place_to_dict(self, place: PlaceWithStatus) -> dict[str, Any]:
        """Convert a place to a dictionary."""
        result: dict[str, Any] = {
            "name": place.name,
            "address": place.address,
            "business_status": place.business_status.value,
            "google_maps_url": place.google_maps_url,
        }

        if place.place_id:
            result["place_id"] = place.place_id

        if place.cid:
            result["cid"] = place.cid

        if place.coordinates:
            result["coordinates"] = {
                "latitude": place.coordinates.latitude,
                "longitude": place.coordinates.longitude,
            }

        if place.source_list:
            result["source_list"] = place.source_list

        if place.api_error:
            result["api_error"] = place.api_error

        return result

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now(UTC).isoformat()


# Global export service instance
export_service = ExportService()
