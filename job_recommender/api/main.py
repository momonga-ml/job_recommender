"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import redis
from sqlalchemy.exc import SQLAlchemyError

from ..models.database import create_tables
from .routers import auth, jobs, resumes, analysis, recommendations


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting up Job Recommender API...")
    try:
        # Create database tables
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Test Redis connection
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Job Recommender API...")


# Create FastAPI application
app = FastAPI(
    title="Job Recommender API",
    description="A comprehensive job recommendation system with AI-powered matching",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:8080",  # Alternative frontend port
        "https://yourdomain.com",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def catch_exceptions(request: Request, call_next):
    """Global exception handler middleware."""
    try:
        response = await call_next(request)
        return response
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Database error occurred"}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Include routers
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    jobs.router,
    prefix="/api/jobs",
    tags=["Jobs"]
)

app.include_router(
    resumes.router,
    prefix="/api/resumes",
    tags=["Resumes"]
)

app.include_router(
    analysis.router,
    prefix="/api/analysis",
    tags=["Analysis"]
)

app.include_router(
    recommendations.router,
    prefix="/api/recommendations", 
    tags=["Recommendations"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Job Recommender API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        from ..models.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        # Test Redis connection
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/api/stats")
async def get_api_stats():
    """Get API statistics."""
    from ..models.database import SessionLocal
    from ..models import Job, User, Resume, Analysis
    
    db = SessionLocal()
    try:
        stats = {
            "total_jobs": db.query(Job).count(),
            "active_jobs": db.query(Job).filter(Job.is_active == True).count(),
            "total_users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "total_resumes": db.query(Resume).count(),
            "total_analyses": db.query(Analysis).count(),
        }
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "job_recommender.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )