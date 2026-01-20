"""Routes for checking place status via Google Places API."""

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.exceptions import PlacesAPIKeyMissing
from app.models.place import BusinessStatus, ParsedPlace, PlaceWithStatus
from app.models.session import Job, JobStatus, JobType, job_store
from app.services.places_api import check_places_status

router = APIRouter(prefix="/places", tags=["places"])


class StatusCheckRequest(BaseModel):
    """Request to start a status check."""

    session_id: str
    api_key: str = Field(..., min_length=1, description="Google Places API key")


class StatusCheckResponse(BaseModel):
    """Response for status check initiation."""

    job_id: str
    status: str
    total_places: int


class StatusCheckResult(BaseModel):
    """Result of a status check job."""

    job_id: str
    status: str
    progress: dict
    places: list[PlaceWithStatus] | None = None
    error: str | None = None
    summary: dict | None = None


async def _run_status_check(
    job: Job,
    session_id: str,
    api_key: str,
) -> None:
    """Background task to check place statuses."""
    session = job_store.get_session(session_id)
    if not session:
        job.fail("Session not found")
        return

    places = [ParsedPlace(**p) for p in session.parsed_places]
    job.start()
    job.progress.total = len(places)

    def progress_callback(current: int, total: int, message: str) -> None:
        job.progress.update(current, total, message)

    try:
        results = await check_places_status(api_key, places, progress_callback)

        # Store results in session
        session.places_with_status = [r.model_dump() for r in results]
        session.check_job_id = job.id
        job_store.update_session(session)

        # Generate summary
        summary = {
            "total": len(results),
            "operational": sum(
                1 for r in results if r.business_status == BusinessStatus.OPERATIONAL
            ),
            "closed_temporarily": sum(
                1 for r in results if r.business_status == BusinessStatus.CLOSED_TEMPORARILY
            ),
            "closed_permanently": sum(
                1 for r in results if r.business_status == BusinessStatus.CLOSED_PERMANENTLY
            ),
            "unknown": sum(1 for r in results if r.business_status == BusinessStatus.UNKNOWN),
        }

        job.complete({"summary": summary})

    except PlacesAPIKeyMissing as e:
        job.fail(e.message)
    except Exception as e:
        job.fail(str(e))


@router.post("/check", response_model=StatusCheckResponse)
async def start_status_check(
    request: StatusCheckRequest,
    background_tasks: BackgroundTasks,
) -> StatusCheckResponse:
    """
    Start checking business status for all places in a session.

    Uses Google Places API to check if businesses are:
    - OPERATIONAL
    - CLOSED_TEMPORARILY
    - CLOSED_PERMANENTLY
    - UNKNOWN

    Returns a job ID to poll for results.
    """
    session = job_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.parsed_places:
        raise HTTPException(status_code=400, detail="No places in session to check")

    # Create job
    job = job_store.create_job(JobType.CHECK_STATUS)

    # Start background task
    background_tasks.add_task(
        _run_status_check,
        job,
        request.session_id,
        request.api_key,
    )

    return StatusCheckResponse(
        job_id=job.id,
        status=job.status.value,
        total_places=len(session.parsed_places),
    )


@router.get("/check/{job_id}", response_model=StatusCheckResult)
async def get_status_check_result(job_id: str) -> StatusCheckResult:
    """
    Get the result of a status check job.

    Poll this endpoint to get progress and final results.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = StatusCheckResult(
        job_id=job.id,
        status=job.status.value,
        progress={
            "current": job.progress.current,
            "total": job.progress.total,
            "percentage": job.progress.percentage,
            "message": job.progress.message,
        },
    )

    if job.status == JobStatus.FAILED:
        result.error = job.error
    elif job.status == JobStatus.COMPLETED and job.result:
        result.summary = job.result.get("summary")

    return result


@router.get("/results/{session_id}", response_model=list[PlaceWithStatus])
async def get_places_with_status(
    session_id: str,
    status: Optional[list[BusinessStatus]] = Query(None, description="Filter by status"),
) -> list[PlaceWithStatus]:
    """
    Get places with their checked status for a session.

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

    if status:
        places = [p for p in places if p.business_status in status]

    return places


@router.get("/summary/{session_id}")
async def get_status_summary(session_id: str) -> dict:
    """Get a summary of place statuses for a session."""
    session = job_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.places_with_status:
        raise HTTPException(
            status_code=400,
            detail="Status check not completed for this session",
        )

    places = [PlaceWithStatus(**p) for p in session.places_with_status]

    return {
        "session_id": session_id,
        "total": len(places),
        "by_status": {
            "operational": sum(
                1 for p in places if p.business_status == BusinessStatus.OPERATIONAL
            ),
            "closed_temporarily": sum(
                1 for p in places if p.business_status == BusinessStatus.CLOSED_TEMPORARILY
            ),
            "closed_permanently": sum(
                1 for p in places if p.business_status == BusinessStatus.CLOSED_PERMANENTLY
            ),
            "unknown": sum(1 for p in places if p.business_status == BusinessStatus.UNKNOWN),
        },
    }
