"""Upload routes for Google Takeout files."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import InvalidFileError, TakeoutParseError
from app.models.place import ParsedPlace
from app.models.session import JobType, job_store
from app.services.takeout_parser import takeout_parser

router = APIRouter(prefix="/upload", tags=["upload"])


class UploadResponse(BaseModel):
    """Response for file upload."""

    session_id: str
    places_count: int
    places: list[ParsedPlace]
    lists_found: list[str]


class UploadError(BaseModel):
    """Error response for upload."""

    error: str
    details: str | None = None


@router.post(
    "/file",
    response_model=UploadResponse,
    responses={400: {"model": UploadError}, 413: {"model": UploadError}},
)
async def upload_takeout_file(
    file: UploadFile = File(..., description="Google Takeout ZIP or JSON file"),
) -> UploadResponse:
    """
    Upload a Google Takeout export file.

    Accepts:
    - ZIP file containing Google Maps saved places
    - JSON/GeoJSON file with saved places

    Returns parsed places with identifiers for status checking.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    filename = file.filename.lower()
    if not (filename.endswith(".zip") or filename.endswith(".json") or filename.endswith(".geojson")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a ZIP or JSON file.",
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    # Parse the file
    try:
        places = takeout_parser.parse_file(content, file.filename)
    except (InvalidFileError, TakeoutParseError) as e:
        raise HTTPException(status_code=400, detail=e.message)

    if not places:
        raise HTTPException(
            status_code=400,
            detail="No saved places found in the uploaded file.",
        )

    # Create session and store parsed places
    session = job_store.create_session()
    session.filename = file.filename
    session.parsed_places = [p.model_dump() for p in places]
    job_store.update_session(session)

    # Get unique list names
    lists_found = list(set(p.source_list for p in places if p.source_list))

    return UploadResponse(
        session_id=session.id,
        places_count=len(places),
        places=places,
        lists_found=lists_found,
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get upload session details."""
    session = job_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "filename": session.filename,
        "created_at": session.created_at.isoformat(),
        "places_count": len(session.parsed_places),
        "has_status_results": bool(session.places_with_status),
    }
