"""Routes for exporting places data."""


from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.models.place import BusinessStatus, PlaceWithStatus
from app.models.session import job_store
from app.services.export_service import export_service

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/json/{session_id}")
async def export_json(
    session_id: str,
    status: list[BusinessStatus] | None = Query(None, description="Filter by status"),
    pretty: bool = Query(True, description="Pretty print JSON"),
) -> Response:
    """
    Export places with status as JSON.

    Optionally filter by business status.
    """
    session = job_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.places_with_status:
        raise HTTPException(
            status_code=400,
            detail="Status check not completed for this session",
        )

    places = [PlaceWithStatus(**p) for p in session.places_with_status]
    json_content = export_service.export_json(places, filter_status=status, pretty=pretty)

    filename = f"places_{session_id[:8]}.json"
    if status:
        status_str = "_".join(s.value.lower() for s in status)
        filename = f"places_{status_str}_{session_id[:8]}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/csv/{session_id}")
async def export_csv(
    session_id: str,
    status: list[BusinessStatus] | None = Query(None, description="Filter by status"),
) -> Response:
    """
    Export places with status as CSV.

    Optionally filter by business status.
    """
    session = job_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.places_with_status:
        raise HTTPException(
            status_code=400,
            detail="Status check not completed for this session",
        )

    places = [PlaceWithStatus(**p) for p in session.places_with_status]
    csv_content = export_service.export_csv(places, filter_status=status)

    filename = f"places_{session_id[:8]}.csv"
    if status:
        status_str = "_".join(s.value.lower() for s in status)
        filename = f"places_{status_str}_{session_id[:8]}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/summary/{session_id}")
async def export_summary(session_id: str) -> dict:
    """
    Get a summary of places organized by status.

    Useful for viewing results in the browser.
    """
    session = job_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.places_with_status:
        raise HTTPException(
            status_code=400,
            detail="Status check not completed for this session",
        )

    places = [PlaceWithStatus(**p) for p in session.places_with_status]
    return export_service.export_summary(places)
