"""WebSocket endpoints for real-time progress updates."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.session import JobStatus, job_store

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept and track a new connection."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove a connection."""
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def send_progress(self, job_id: str, data: dict[str, Any]) -> None:
        """Send progress update to all connections watching a job."""
        if job_id not in self.active_connections:
            return

        message = json.dumps(data)
        disconnected = []

        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, job_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str) -> None:
    """
    WebSocket endpoint for real-time job progress updates.

    Connect to receive progress updates for a specific job.
    Messages are JSON with structure:
    {
        "status": "running|completed|failed",
        "progress": {
            "current": 5,
            "total": 10,
            "percentage": 50.0,
            "message": "Processing item 5..."
        },
        "result": {...}  // Only present when completed
        "error": "..."   // Only present when failed
    }
    """
    await manager.connect(websocket, job_id)

    try:
        # Initial status check
        job = job_store.get_job(job_id)
        if not job:
            await websocket.send_text(
                json.dumps(
                    {
                        "error": "Job not found",
                        "status": "not_found",
                    }
                )
            )
            return

        # Send initial state
        await websocket.send_text(json.dumps(_job_to_message(job)))

        # Poll for updates until job completes
        poll_interval = 0.5  # seconds

        while True:
            await asyncio.sleep(poll_interval)

            job = job_store.get_job(job_id)
            if not job:
                break

            # Send current state
            message = _job_to_message(job)
            await websocket.send_text(json.dumps(message))

            # Stop polling if job is finished
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, job_id)


def _job_to_message(job: Any) -> dict[str, Any]:
    """Convert job to WebSocket message format."""
    message: dict[str, Any] = {
        "status": job.status.value,
        "progress": {
            "current": job.progress.current,
            "total": job.progress.total,
            "percentage": job.progress.percentage,
            "message": job.progress.message,
        },
    }

    if job.status == JobStatus.COMPLETED and job.result:
        message["result"] = job.result
    elif job.status == JobStatus.FAILED:
        message["error"] = job.error

    return message
