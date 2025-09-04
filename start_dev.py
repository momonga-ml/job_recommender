#!/usr/bin/env python3
"""Development startup script for Job Recommender API."""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required services are running."""
    logger.info("Checking dependencies...")
    
    # Check database connection (SQLite or PostgreSQL based on DATABASE_URL)
    try:
        from job_recommender.models.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.info("Database connection issue - will try to create tables anyway")
        # Don't return False - we can still try to setup the database
    
    # Check Redis (optional)
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.warning(f"⚠ Redis connection failed: {e}")
        logger.info("Redis is optional - caching will be disabled but the app will still work")
    
    return True


def setup_database():
    """Set up database tables."""
    logger.info("Setting up database...")
    
    try:
        from job_recommender.models.database import create_tables
        create_tables()
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Database setup failed: {e}")
        return False


def start_celery_worker():
    """Start Celery worker in background."""
    logger.info("Starting Celery worker...")
    
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "job_recommender.celery_app",
        "worker",
        "--loglevel=info",
        "--queues=scraping,processing,analysis,email"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=project_root)
        logger.info(f"✓ Celery worker started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"✗ Failed to start Celery worker: {e}")
        return None


def start_celery_beat():
    """Start Celery beat scheduler in background."""
    logger.info("Starting Celery beat scheduler...")
    
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "job_recommender.celery_app",
        "beat",
        "--loglevel=info"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=project_root)
        logger.info(f"✓ Celery beat started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"✗ Failed to start Celery beat: {e}")
        return None


def start_api_server():
    """Start the FastAPI server."""
    logger.info("Starting FastAPI server...")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "job_recommender.api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--reload-dir", str(project_root / "job_recommender")
    ]
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"✗ Failed to start API server: {e}")


def main():
    """Main startup function."""
    logger.info("Starting Job Recommender API Development Server")
    logger.info("=" * 50)
    
    # Check .env file
    env_file = project_root / ".env"
    if not env_file.exists():
        logger.warning("No .env file found. Copy .env.example to .env and update the values.")
        
        # Create .env from example
        example_env = project_root / ".env.example"
        if example_env.exists():
            import shutil
            shutil.copy(example_env, env_file)
            logger.info("Created .env file from .env.example")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency checks failed. Please fix the issues and try again.")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        logger.error("Database setup failed. Please check your database connection.")
        sys.exit(1)
    
    # Create uploads directory
    uploads_dir = project_root / "uploads" / "resumes"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    logger.info("✓ Uploads directory created")
    
    # Start background services
    celery_worker = start_celery_worker()
    time.sleep(2)  # Give worker time to start
    
    celery_beat = start_celery_beat()
    time.sleep(2)  # Give beat time to start
    
    logger.info("=" * 50)
    logger.info("🚀 Job Recommender API is starting!")
    logger.info("📖 API Documentation: http://localhost:8000/docs")
    logger.info("🔍 ReDoc Documentation: http://localhost:8000/redoc")
    logger.info("💾 API Stats: http://localhost:8000/api/stats")
    logger.info("❤️  Health Check: http://localhost:8000/health")
    logger.info("=" * 50)
    
    try:
        # Start the API server (this will block)
        start_api_server()
    finally:
        # Cleanup background processes
        logger.info("Cleaning up background processes...")
        
        if celery_worker:
            try:
                celery_worker.terminate()
                celery_worker.wait(timeout=5)
                logger.info("✓ Celery worker stopped")
            except:
                celery_worker.kill()
                logger.info("✓ Celery worker killed")
        
        if celery_beat:
            try:
                celery_beat.terminate()
                celery_beat.wait(timeout=5)
                logger.info("✓ Celery beat stopped")
            except:
                celery_beat.kill()
                logger.info("✓ Celery beat killed")
        
        logger.info("👋 Job Recommender API stopped")


if __name__ == "__main__":
    main()