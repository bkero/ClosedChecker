"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_geojson():
    """Sample GeoJSON data matching Google Takeout format."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {
                    "coordinates": [-122.6784, 45.5152],
                    "type": "Point"
                },
                "properties": {
                    "google_maps_url": "http://maps.google.com/?cid=12345678901234567890",
                    "location": {
                        "name": "Test Coffee Shop",
                        "address": "123 Main St, Portland, OR 97201"
                    }
                },
                "type": "Feature"
            },
            {
                "geometry": {
                    "coordinates": [-122.6800, 45.5200],
                    "type": "Point"
                },
                "properties": {
                    "google_maps_url": "https://www.google.com/maps/place//data=!4m2!3m1!1s0x0:0xabcdef1234567890",
                    "location": {
                        "name": "Test Restaurant",
                        "address": "456 Oak Ave, Portland, OR 97202"
                    }
                },
                "type": "Feature"
            }
        ]
    }


@pytest.fixture
def sample_geojson_bytes(sample_geojson):
    """Sample GeoJSON as bytes."""
    import json
    return json.dumps(sample_geojson).encode("utf-8")
