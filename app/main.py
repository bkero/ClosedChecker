"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import export, places, removal, upload
from app.api.websocket import router as websocket_router
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="Google Maps Closed Places Manager",
    description="Identify and remove closed places from your Google Maps saved lists",
    version="1.0.0",
)

# Setup directories
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Ensure directories exist
settings.ensure_directories()
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routers
app.include_router(upload.router, prefix="/api")
app.include_router(places.router, prefix="/api")
app.include_router(removal.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(websocket_router)


# Template routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Home page - file upload."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "Google Maps Closed Places Manager"},
    )


@app.get("/results/{session_id}", response_class=HTMLResponse)
async def results_page(request: Request, session_id: str) -> HTMLResponse:
    """Results page - display places with status."""
    return templates.TemplateResponse(
        request,
        "results.html",
        {"title": "Status Check Results", "session_id": session_id},
    )


@app.get("/removal/{session_id}", response_class=HTMLResponse)
async def removal_page(request: Request, session_id: str) -> HTMLResponse:
    """Removal page - select and remove places."""
    return templates.TemplateResponse(
        request,
        "removal.html",
        {"title": "Remove Places", "session_id": session_id},
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


def main() -> None:
    """Run the application."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
