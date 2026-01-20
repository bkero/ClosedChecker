"""Routes for removing places from Google Maps saved lists."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.exceptions import AuthenticationExpired, AuthenticationRequired
from app.models.place import PlaceRemovalResult
from app.models.session import AuthStatus, Job, JobStatus, JobType, job_store
from app.services.playwright_automation import (
    PlaywrightAutomation,
    get_auth_status,
    remove_places,
    start_authentication,
)

router = APIRouter(prefix="/removal", tags=["removal"])


class AuthStartResponse(BaseModel):
    """Response when starting auth session."""

    message: str
    instructions: str


class RemovalRequest(BaseModel):
    """Request to remove places."""

    session_id: str
    place_urls: list[str] = Field(
        ..., min_length=1, description="URLs of places to remove"
    )


class RemovalResponse(BaseModel):
    """Response for removal initiation."""

    job_id: str
    status: str
    total_places: int


class RemovalResult(BaseModel):
    """Result of a removal job."""

    job_id: str
    status: str
    progress: dict
    results: list[PlaceRemovalResult] | None = None
    error: str | None = None
    summary: dict | None = None


@router.get("/auth/status", response_model=AuthStatus)
async def check_auth_status() -> AuthStatus:
    """
    Check if Google authentication is available.

    Returns authentication status including expiry information.
    """
    return await get_auth_status()


@router.post("/auth/start", response_model=AuthStartResponse)
async def start_auth_session() -> AuthStartResponse:
    """
    Start a browser session for Google authentication.

    This opens a browser window where the user must manually log in
    to their Google account. The authentication state is saved for
    subsequent removal operations.

    Note: This endpoint blocks until authentication is complete or times out.
    """
    try:
        success = await start_authentication()
        if success:
            return AuthStartResponse(
                message="Authentication completed successfully",
                instructions="You can now use the removal feature to remove saved places.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Authentication was not completed",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}",
        )


async def _run_removal(
    job: Job,
    session_id: str,
    place_urls: list[str],
) -> None:
    """Background task to remove places."""
    session = job_store.get_session(session_id)
    if not session:
        job.fail("Session not found")
        return

    # Build list of places to remove with names
    places_with_status = {
        p["google_maps_url"]: p for p in session.places_with_status
    }

    places_to_remove = []
    for url in place_urls:
        place_data = places_with_status.get(url, {})
        places_to_remove.append({
            "url": url,
            "name": place_data.get("name", "Unknown Place"),
        })

    job.start()
    job.progress.total = len(places_to_remove)

    def progress_callback(current: int, total: int, message: str) -> None:
        job.progress.update(current, total, message)

    try:
        results = await remove_places(places_to_remove, progress_callback)

        # Calculate summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        job.complete({
            "results": [r.model_dump() for r in results],
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
            },
        })

    except AuthenticationRequired as e:
        job.fail(e.message)
    except AuthenticationExpired as e:
        job.fail(e.message)
    except Exception as e:
        job.fail(str(e))


@router.post("/execute", response_model=RemovalResponse)
async def start_removal(
    request: RemovalRequest,
    background_tasks: BackgroundTasks,
) -> RemovalResponse:
    """
    Start removing places from Google Maps saved lists.

    Requires authentication to be completed first (see /auth/start).
    Places are removed one at a time using browser automation.

    Returns a job ID to poll for results.
    """
    # Check authentication status
    auth_status = await get_auth_status()
    if not auth_status.authenticated:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please complete /auth/start first.",
        )

    # Verify session exists
    session = job_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create job
    job = job_store.create_job(JobType.REMOVE_PLACES)
    session.removal_job_id = job.id
    job_store.update_session(session)

    # Start background task
    background_tasks.add_task(
        _run_removal,
        job,
        request.session_id,
        request.place_urls,
    )

    return RemovalResponse(
        job_id=job.id,
        status=job.status.value,
        total_places=len(request.place_urls),
    )


@router.get("/result/{job_id}", response_model=RemovalResult)
async def get_removal_result(job_id: str) -> RemovalResult:
    """
    Get the result of a removal job.

    Poll this endpoint to get progress and final results.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = RemovalResult(
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
        result.results = [
            PlaceRemovalResult(**r) for r in job.result.get("results", [])
        ]
        result.summary = job.result.get("summary")

    return result
