"""Celery application for background tasks."""

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
celery_app = Celery(
    "job_recommender",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "job_recommender.tasks.job_scraping",
        "job_recommender.tasks.resume_processing",
        "job_recommender.tasks.analysis_tasks",
        "job_recommender.tasks.email_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "job_recommender.tasks.job_scraping.*": {"queue": "scraping"},
        "job_recommender.tasks.resume_processing.*": {"queue": "processing"},
        "job_recommender.tasks.analysis_tasks.*": {"queue": "analysis"},
        "job_recommender.tasks.email_tasks.*": {"queue": "email"},
    },
    
    # Task serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task results
    result_expires=3600,  # 1 hour
    
    # Task routing
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "scrape-jobs-daily": {
            "task": "job_recommender.tasks.job_scraping.scrape_jobs_periodic",
            "schedule": 86400.0,  # 24 hours
            "options": {"queue": "scraping"}
        },
        "cleanup-old-jobs": {
            "task": "job_recommender.tasks.job_scraping.cleanup_old_jobs",
            "schedule": 604800.0,  # 7 days
            "options": {"queue": "scraping"}
        },
        "update-skill-statistics": {
            "task": "job_recommender.tasks.analysis_tasks.update_skill_statistics",
            "schedule": 86400.0,  # 24 hours
            "options": {"queue": "analysis"}
        },
    },
)

if __name__ == "__main__":
    celery_app.start()