"""Tests for API endpoints."""

import json
import zipfile
from io import BytesIO

import pytest


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestUploadEndpoints:
    """Tests for file upload endpoints."""

    def test_upload_json_file(self, client, sample_geojson):
        """Test uploading a JSON file."""
        content = json.dumps(sample_geojson).encode("utf-8")

        response = client.post(
            "/api/upload/file", files={"file": ("places.json", content, "application/json")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["places_count"] == 2
        assert "session_id" in data

    def test_upload_zip_file(self, client, sample_geojson):
        """Test uploading a ZIP file."""
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("Takeout/Maps (your places)/Saved Places.json", json.dumps(sample_geojson))
        zip_buffer.seek(0)

        response = client.post(
            "/api/upload/file",
            files={"file": ("takeout.zip", zip_buffer.read(), "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["places_count"] == 2

    def test_upload_invalid_file_type(self, client):
        """Test that uploading invalid file type returns error."""
        response = client.post(
            "/api/upload/file", files={"file": ("test.txt", b"hello", "text/plain")}
        )

        assert response.status_code == 400

    def test_upload_invalid_json(self, client):
        """Test that uploading invalid JSON returns error."""
        response = client.post(
            "/api/upload/file", files={"file": ("places.json", b"not json", "application/json")}
        )

        assert response.status_code == 400

    def test_upload_empty_places(self, client):
        """Test that uploading file with no places returns error."""
        empty_geojson = json.dumps({"type": "FeatureCollection", "features": []}).encode("utf-8")

        response = client.post(
            "/api/upload/file", files={"file": ("places.json", empty_geojson, "application/json")}
        )

        assert response.status_code == 400
        assert "No saved places found" in response.json()["detail"]


class TestSessionEndpoints:
    """Tests for session-related endpoints."""

    def test_get_session(self, client, sample_geojson):
        """Test getting session details after upload."""
        # First upload a file
        content = json.dumps(sample_geojson).encode("utf-8")
        upload_response = client.post(
            "/api/upload/file", files={"file": ("places.json", content, "application/json")}
        )
        session_id = upload_response.json()["session_id"]

        # Then get session details
        response = client.get(f"/api/upload/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["places_count"] == 2

    def test_get_nonexistent_session(self, client):
        """Test that getting nonexistent session returns 404."""
        response = client.get("/api/upload/session/nonexistent-id")
        assert response.status_code == 404


class TestExportEndpoints:
    """Tests for export endpoints."""

    def test_export_requires_status_check(self, client, sample_geojson):
        """Test that export fails if status check not completed."""
        # Upload file
        content = json.dumps(sample_geojson).encode("utf-8")
        upload_response = client.post(
            "/api/upload/file", files={"file": ("places.json", content, "application/json")}
        )
        session_id = upload_response.json()["session_id"]

        # Try to export before status check
        response = client.get(f"/api/export/json/{session_id}")

        assert response.status_code == 400
        assert "Status check not completed" in response.json()["detail"]


class TestRemovalAuthEndpoints:
    """Tests for removal authentication endpoints."""

    def test_auth_status_when_not_authenticated(self, client):
        """Test auth status when not authenticated."""
        response = client.get("/api/removal/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestTemplateRoutes:
    """Tests for HTML template routes."""

    def test_index_page(self, client):
        """Test that index page loads."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Google Maps Closed Places Manager" in response.text

    def test_results_page(self, client):
        """Test that results page loads."""
        response = client.get("/results/test-session-id")
        assert response.status_code == 200

    def test_removal_page(self, client):
        """Test that removal page loads."""
        response = client.get("/removal/test-session-id")
        assert response.status_code == 200
