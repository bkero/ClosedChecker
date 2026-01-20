"""Tests for data models."""

import pytest
from pydantic import ValidationError

from app.models.place import (
    BusinessStatus,
    Coordinates,
    ParsedPlace,
    PlaceWithStatus,
)
from app.models.session import Job, JobStatus, JobType, UploadSession


class TestCoordinates:
    """Tests for Coordinates model."""

    def test_valid_coordinates(self):
        """Test creating valid coordinates."""
        coords = Coordinates(latitude=45.5152, longitude=-122.6784)
        assert coords.latitude == 45.5152
        assert coords.longitude == -122.6784

    def test_latitude_bounds(self):
        """Test that latitude must be between -90 and 90."""
        with pytest.raises(ValidationError):
            Coordinates(latitude=91, longitude=0)
        with pytest.raises(ValidationError):
            Coordinates(latitude=-91, longitude=0)

    def test_longitude_bounds(self):
        """Test that longitude must be between -180 and 180."""
        with pytest.raises(ValidationError):
            Coordinates(latitude=0, longitude=181)
        with pytest.raises(ValidationError):
            Coordinates(latitude=0, longitude=-181)


class TestParsedPlace:
    """Tests for ParsedPlace model."""

    def test_create_minimal_place(self):
        """Test creating a place with minimal required fields."""
        place = ParsedPlace(
            name="Test Place",
            google_maps_url="http://maps.google.com/?cid=123"
        )
        assert place.name == "Test Place"
        assert place.address is None
        assert place.place_id is None

    def test_create_full_place(self):
        """Test creating a place with all fields."""
        place = ParsedPlace(
            name="Test Place",
            address="123 Main St",
            google_maps_url="http://maps.google.com/?cid=123",
            place_id="ChIJ123",
            cid="123",
            coordinates=Coordinates(latitude=45.5, longitude=-122.6),
            source_list="Saved Places"
        )
        assert place.name == "Test Place"
        assert place.address == "123 Main St"
        assert place.cid == "123"
        assert place.coordinates.latitude == 45.5


class TestPlaceWithStatus:
    """Tests for PlaceWithStatus model."""

    def test_from_parsed_place(self):
        """Test creating PlaceWithStatus from ParsedPlace."""
        parsed = ParsedPlace(
            name="Test Place",
            google_maps_url="http://maps.google.com/?cid=123",
            address="123 Main St"
        )

        with_status = PlaceWithStatus.from_parsed_place(
            parsed,
            business_status=BusinessStatus.OPERATIONAL
        )

        assert with_status.name == "Test Place"
        assert with_status.business_status == BusinessStatus.OPERATIONAL

    def test_default_status_is_unknown(self):
        """Test that default business status is UNKNOWN."""
        place = PlaceWithStatus(
            name="Test",
            google_maps_url="http://example.com"
        )
        assert place.business_status == BusinessStatus.UNKNOWN


class TestBusinessStatus:
    """Tests for BusinessStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        assert BusinessStatus.OPERATIONAL.value == "OPERATIONAL"
        assert BusinessStatus.CLOSED_TEMPORARILY.value == "CLOSED_TEMPORARILY"
        assert BusinessStatus.CLOSED_PERMANENTLY.value == "CLOSED_PERMANENTLY"
        assert BusinessStatus.UNKNOWN.value == "UNKNOWN"


class TestJob:
    """Tests for Job model."""

    def test_job_creation(self):
        """Test creating a new job."""
        job = Job(type=JobType.CHECK_STATUS)
        assert job.status == JobStatus.PENDING
        assert job.id is not None
        assert job.progress.current == 0

    def test_job_start(self):
        """Test starting a job."""
        job = Job(type=JobType.CHECK_STATUS)
        job.start()
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_job_complete(self):
        """Test completing a job."""
        job = Job(type=JobType.CHECK_STATUS)
        job.start()
        job.complete({"result": "success"})
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result == {"result": "success"}

    def test_job_fail(self):
        """Test failing a job."""
        job = Job(type=JobType.CHECK_STATUS)
        job.start()
        job.fail("Something went wrong")
        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"


class TestUploadSession:
    """Tests for UploadSession model."""

    def test_session_creation(self):
        """Test creating a new session."""
        session = UploadSession()
        assert session.id is not None
        assert session.parsed_places == []
        assert session.places_with_status == []
