"""Main FastAPI application."""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from core import setup_logging, get_logger
from config import get_settings
from database import get_db_manager
from .routes import router

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Noctipede API",
    description="Deep Web Analysis System API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="/app/output"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


@app.on_startup
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Noctipede API")
    
    # Test database connection
    db_manager = get_db_manager()
    if not db_manager.test_connection():
        logger.error("Database connection failed")
        raise Exception("Database connection failed")
    
    # Create tables if they don't exist
    db_manager.create_tables()
    logger.info("Database initialized")


@app.on_shutdown
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Noctipede API")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "noctipede-api"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check database connection
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready", "service": "noctipede-api"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def main():
    """Run the API server."""
    settings = get_settings()
    
    uvicorn.run(
        "noctipede.api.main:app",
        host=settings.web_server_host,
        port=settings.web_server_port,
        reload=False,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
