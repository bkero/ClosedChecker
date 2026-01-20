"""Google Places API (New) client for checking business status."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx

from app.config import settings
from app.core.exceptions import PlacesAPIError, PlacesAPIKeyMissing, PlacesAPIQuotaExceeded
from app.models.place import BusinessStatus, ParsedPlace, PlaceWithStatus


class PlacesAPIClient:
    """Client for Google Places API (New)."""

    # New Places API base URL
    BASE_URL = "https://places.googleapis.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PlacesAPIClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _ensure_api_key(self) -> str:
        """Ensure API key is available."""
        if not self.api_key:
            raise PlacesAPIKeyMissing()
        return self.api_key

    def _get_headers(self, field_mask: str) -> dict[str, str]:
        """Get headers for API request."""
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._ensure_api_key(),
            "X-Goog-FieldMask": field_mask,
        }

    async def _post_request(
        self, endpoint: str, data: dict[str, Any], field_mask: str
    ) -> dict[str, Any]:
        """Make a POST request to the new Places API."""
        if not self._client:
            raise PlacesAPIError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers(field_mask)

        try:
            response = await self._client.post(url, json=data, headers=headers)

            # Handle error responses
            if response.status_code == 403:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Permission denied")
                if "RESOURCE_EXHAUSTED" in str(error_data):
                    raise PlacesAPIQuotaExceeded()
                # Check if API is not enabled
                if "has not been used in project" in error_msg or "is disabled" in error_msg:
                    raise PlacesAPIError(
                        message="Places API (New) is not enabled",
                        details="Please enable the Places API (New) in your Google Cloud Console: "
                        "https://console.cloud.google.com/apis/library/places.googleapis.com",
                    )
                raise PlacesAPIError(
                    message="Places API request denied",
                    details=error_msg,
                )
            elif response.status_code == 429:
                raise PlacesAPIQuotaExceeded()
            elif response.status_code >= 400:
                error_data = response.json()
                raise PlacesAPIError(
                    message=f"API error: {response.status_code}",
                    details=error_data.get("error", {}).get("message", str(error_data)),
                )

            return response.json()

        except httpx.HTTPStatusError as e:
            raise PlacesAPIError(
                message=f"HTTP error: {e.response.status_code}",
                details=str(e),
            )
        except httpx.RequestError as e:
            raise PlacesAPIError(
                message="Network error",
                details=str(e),
            )

    async def _get_request(self, endpoint: str, field_mask: str) -> dict[str, Any]:
        """Make a GET request to the new Places API."""
        if not self._client:
            raise PlacesAPIError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers(field_mask)

        try:
            response = await self._client.get(url, headers=headers)

            if response.status_code == 403:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Permission denied")
                raise PlacesAPIError(
                    message="Places API request denied",
                    details=error_msg,
                )
            elif response.status_code == 429:
                raise PlacesAPIQuotaExceeded()
            elif response.status_code == 404:
                return {"not_found": True}
            elif response.status_code >= 400:
                error_data = response.json()
                raise PlacesAPIError(
                    message=f"API error: {response.status_code}",
                    details=error_data.get("error", {}).get("message", str(error_data)),
                )

            return response.json()

        except httpx.HTTPStatusError as e:
            raise PlacesAPIError(
                message=f"HTTP error: {e.response.status_code}",
                details=str(e),
            )
        except httpx.RequestError as e:
            raise PlacesAPIError(
                message="Network error",
                details=str(e),
            )

    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        """Get details for a place by place_id."""
        # New API format: places/{place_id}
        endpoint = f"places/{place_id}"
        field_mask = "displayName,formattedAddress,businessStatus,id"
        return await self._get_request(endpoint, field_mask)

    async def search_text(
        self,
        query: str,
        location_bias: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """Search for places using text query."""
        data: dict[str, Any] = {
            "textQuery": query,
        }

        if location_bias:
            lat, lng = location_bias
            data["locationBias"] = {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": 5000.0,  # 5km radius
                }
            }

        field_mask = "places.displayName,places.formattedAddress,places.businessStatus,places.id"
        return await self._post_request("places:searchText", data, field_mask)

    async def check_place_status(self, place: ParsedPlace) -> PlaceWithStatus:
        """Check the business status of a place."""
        business_status = BusinessStatus.UNKNOWN
        api_error: str | None = None
        resolved_place_id = place.place_id

        try:
            # Try place_id first if available and in new format
            if place.place_id and place.place_id.startswith("ChIJ"):
                result = await self.get_place_details(place.place_id)
                if not result.get("not_found"):
                    business_status = self._extract_business_status(result)
                    return PlaceWithStatus.from_parsed_place(place, business_status=business_status)

            # Use text search with name and address
            query = place.name
            if place.address:
                query = f"{place.name}, {place.address}"

            location_bias = None
            if place.coordinates:
                location_bias = (
                    place.coordinates.latitude,
                    place.coordinates.longitude,
                )

            result = await self.search_text(query, location_bias)

            places_list = result.get("places", [])
            if places_list:
                # Get the first (best) match
                best_match = places_list[0]
                business_status = self._extract_business_status(best_match)
                resolved_place_id = best_match.get("id", place.place_id)
            else:
                # No results - place may no longer exist
                api_error = "Place not found - may no longer exist"

        except PlacesAPIQuotaExceeded:
            raise  # Re-raise quota errors to stop processing
        except PlacesAPIError as e:
            api_error = f"{e.message}: {e.details}" if e.details else e.message
        except Exception as e:
            api_error = f"Unexpected error: {str(e)}"

        return PlaceWithStatus(
            name=place.name,
            address=place.address,
            google_maps_url=place.google_maps_url,
            place_id=resolved_place_id,
            cid=place.cid,
            business_status=business_status,
            coordinates=place.coordinates,
            source_list=place.source_list,
            api_error=api_error,
        )

    def _extract_business_status(self, place_data: dict[str, Any]) -> BusinessStatus:
        """Extract business status from place data."""
        # New API uses camelCase: businessStatus
        status = place_data.get("businessStatus", "")

        if status == "OPERATIONAL":
            return BusinessStatus.OPERATIONAL
        elif status == "CLOSED_TEMPORARILY":
            return BusinessStatus.CLOSED_TEMPORARILY
        elif status == "CLOSED_PERMANENTLY":
            return BusinessStatus.CLOSED_PERMANENTLY
        else:
            return BusinessStatus.UNKNOWN

    async def check_places_batch(
        self,
        places: list[ParsedPlace],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[PlaceWithStatus]:
        """
        Check business status for a batch of places.

        Args:
            places: List of places to check
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of places with status information
        """
        results: list[PlaceWithStatus] = []
        total = len(places)
        delay_seconds = settings.places_api_delay_ms / 1000.0

        for i, place in enumerate(places):
            if progress_callback:
                progress_callback(i, total, f"Checking: {place.name}")

            try:
                result = await self.check_place_status(place)
                results.append(result)
            except PlacesAPIQuotaExceeded:
                # Mark remaining places as unknown due to quota
                for remaining_place in places[i:]:
                    results.append(
                        PlaceWithStatus.from_parsed_place(
                            remaining_place,
                            api_error="Skipped due to API quota limit",
                        )
                    )
                break
            except PlacesAPIError as e:
                # Log error but continue with other places
                results.append(
                    PlaceWithStatus.from_parsed_place(
                        place,
                        api_error=f"{e.message}: {e.details}" if e.details else e.message,
                    )
                )

            # Rate limiting delay
            if delay_seconds > 0 and i < total - 1:
                await asyncio.sleep(delay_seconds)

        if progress_callback:
            progress_callback(total, total, "Status check complete")

        return results


async def check_places_status(
    api_key: str,
    places: list[ParsedPlace],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[PlaceWithStatus]:
    """
    Convenience function to check status of places.

    Args:
        api_key: Google Places API key
        places: List of places to check
        progress_callback: Optional progress callback

    Returns:
        List of places with status
    """
    async with PlacesAPIClient(api_key) as client:
        return await client.check_places_batch(places, progress_callback)
