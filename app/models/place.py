"""Data models for places and business status."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BusinessStatus(str, Enum):
    """Business status from Google Places API."""

    OPERATIONAL = "OPERATIONAL"
    CLOSED_TEMPORARILY = "CLOSED_TEMPORARILY"
    CLOSED_PERMANENTLY = "CLOSED_PERMANENTLY"
    UNKNOWN = "UNKNOWN"


class Coordinates(BaseModel):
    """Geographic coordinates."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ParsedPlace(BaseModel):
    """A place parsed from Google Takeout data."""

    model_config = ConfigDict(frozen=True)

    name: str
    address: str | None = None
    google_maps_url: str
    place_id: str | None = None
    cid: str | None = None
    coordinates: Coordinates | None = None
    source_list: str | None = None


class PlaceWithStatus(BaseModel):
    """A place with its business status from Google Places API."""

    name: str
    address: str | None = None
    google_maps_url: str
    place_id: str | None = None
    cid: str | None = None
    business_status: BusinessStatus = BusinessStatus.UNKNOWN
    coordinates: Coordinates | None = None
    source_list: str | None = None
    api_error: str | None = None

    @classmethod
    def from_parsed_place(
        cls,
        place: ParsedPlace,
        business_status: BusinessStatus = BusinessStatus.UNKNOWN,
        api_error: str | None = None,
    ) -> "PlaceWithStatus":
        """Create from a parsed place with status information."""
        return cls(
            name=place.name,
            address=place.address,
            google_maps_url=place.google_maps_url,
            place_id=place.place_id,
            cid=place.cid,
            business_status=business_status,
            coordinates=place.coordinates,
            source_list=place.source_list,
            api_error=api_error,
        )


class PlaceRemovalResult(BaseModel):
    """Result of attempting to remove a place from saved lists."""

    google_maps_url: str
    name: str
    success: bool
    error: str | None = None


class StatusCheckRequest(BaseModel):
    """Request to check status of places."""

    api_key: str = Field(..., min_length=1)
    place_urls: list[str] = Field(..., min_length=1)


class RemovalRequest(BaseModel):
    """Request to remove places from saved lists."""

    place_urls: list[str] = Field(..., min_length=1)
