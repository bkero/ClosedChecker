"""Data models for job and session tracking."""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of background job."""

    PARSE_TAKEOUT = "parse_takeout"
    CHECK_STATUS = "check_status"
    REMOVE_PLACES = "remove_places"


class JobProgress(BaseModel):
    """Progress information for a job."""

    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0

    def update(self, current: int, total: int, message: str = "") -> None:
        """Update progress."""
        self.current = current
        self.total = total
        self.message = message
        self.percentage = (current / total * 100) if total > 0 else 0.0


class Job(BaseModel):
    """A background job."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress = Field(default_factory=JobProgress)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self, result: Any = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.result = result

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error = error

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(UTC)


class UploadSession(BaseModel):
    """Session tracking for an upload and its processing."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    filename: Optional[str] = None
    parse_job_id: Optional[str] = None
    check_job_id: Optional[str] = None
    removal_job_id: Optional[str] = None
    parsed_places: list[Any] = Field(default_factory=list)
    places_with_status: list[Any] = Field(default_factory=list)


class AuthStatus(BaseModel):
    """Status of Playwright authentication."""

    authenticated: bool = False
    last_authenticated: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


# In-memory storage for jobs and sessions
class JobStore:
    """In-memory storage for jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._sessions: dict[str, UploadSession] = {}

    def create_job(self, job_type: JobType) -> Job:
        """Create a new job."""
        job = Job(type=job_type)
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def create_session(self) -> UploadSession:
        """Create a new upload session."""
        session = UploadSession()
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session: UploadSession) -> None:
        """Update a session."""
        self._sessions[session.id] = session


# Global job store instance
job_store = JobStore()
