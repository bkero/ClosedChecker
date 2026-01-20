"""Data models for places and business status."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
    address: Optional[str] = None
    google_maps_url: str
    place_id: Optional[str] = None
    cid: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    source_list: Optional[str] = None


class PlaceWithStatus(BaseModel):
    """A place with its business status from Google Places API."""

    name: str
    address: Optional[str] = None
    google_maps_url: str
    place_id: Optional[str] = None
    cid: Optional[str] = None
    business_status: BusinessStatus = BusinessStatus.UNKNOWN
    coordinates: Optional[Coordinates] = None
    source_list: Optional[str] = None
    api_error: Optional[str] = None

    @classmethod
    def from_parsed_place(
        cls,
        place: ParsedPlace,
        business_status: BusinessStatus = BusinessStatus.UNKNOWN,
        api_error: Optional[str] = None,
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
    error: Optional[str] = None


class StatusCheckRequest(BaseModel):
    """Request to check status of places."""

    api_key: str = Field(..., min_length=1)
    place_urls: list[str] = Field(..., min_length=1)


class RemovalRequest(BaseModel):
    """Request to remove places from saved lists."""

    place_urls: list[str] = Field(..., min_length=1)
