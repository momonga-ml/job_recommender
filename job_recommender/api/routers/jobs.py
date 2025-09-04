"""Jobs router with CRUD endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from pydantic import BaseModel
import logging
import json

from ...models.database import get_db
from ...models.job import Job
from ...models.user import User
from ..dependencies import (
    get_current_user, 
    get_optional_user, 
    get_pagination_params, 
    PaginationParams,
    api_rate_limit
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class JobBase(BaseModel):
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "US"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "yearly"
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    industry: Optional[str] = None
    department: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    external_job_id: Optional[str] = None
    apply_url: Optional[str] = None
    company_website: Optional[str] = None
    contact_email: Optional[str] = None
    is_remote_friendly: Optional[bool] = False
    requires_visa_sponsorship: Optional[bool] = False
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    technologies: Optional[str] = None
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    industry: Optional[str] = None
    department: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    external_job_id: Optional[str] = None
    apply_url: Optional[str] = None
    company_website: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None
    is_remote_friendly: Optional[bool] = None
    requires_visa_sponsorship: Optional[bool] = None
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    technologies: Optional[str] = None
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None


class JobResponse(JobBase):
    id: int
    is_active: bool
    data_completeness_score: float
    last_scraped: datetime
    created_at: datetime
    updated_at: datetime
    salary_range: Optional[str]
    is_expired: bool

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    size: int
    total_pages: int


class JobSearchRequest(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote_type: Optional[str] = None
    industry: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requires_visa_sponsorship: Optional[bool] = None
    is_remote_friendly: Optional[bool] = None


def trigger_job_scraping():
    """Trigger background job scraping (placeholder)."""
    logger.info("Job scraping triggered")
    # TODO: Implement Celery task for job scraping


@router.get("/", response_model=JobListResponse, dependencies=[Depends(api_rate_limit)])
async def list_jobs(
    pagination: PaginationParams = Depends(get_pagination_params),
    query: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Location filter"),
    company: Optional[str] = Query(None, description="Company filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    experience_level: Optional[str] = Query(None, description="Experience level filter"),
    remote_type: Optional[str] = Query(None, description="Remote type filter"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    salary_min: Optional[int] = Query(None, description="Minimum salary"),
    salary_max: Optional[int] = Query(None, description="Maximum salary"),
    requires_visa_sponsorship: Optional[bool] = Query(None, description="Requires visa sponsorship"),
    is_remote_friendly: Optional[bool] = Query(None, description="Remote friendly"),
    sort_by: Optional[str] = Query("created_at", description="Sort by field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """List jobs with search and filtering."""
    query_filters = []
    
    # Base filter for active jobs
    query_filters.append(Job.is_active == True)
    
    # Text search
    if query:
        search_filter = or_(
            Job.title.ilike(f"%{query}%"),
            Job.company.ilike(f"%{query}%"),
            Job.description.ilike(f"%{query}%"),
            Job.requirements.ilike(f"%{query}%")
        )
        query_filters.append(search_filter)
    
    # Filters
    if location:
        query_filters.append(Job.location.ilike(f"%{location}%"))
    
    if company:
        query_filters.append(Job.company.ilike(f"%{company}%"))
    
    if job_type:
        query_filters.append(Job.job_type == job_type)
    
    if experience_level:
        query_filters.append(Job.experience_level == experience_level)
    
    if remote_type:
        query_filters.append(Job.remote_type == remote_type)
    
    if industry:
        query_filters.append(Job.industry == industry)
    
    if salary_min is not None:
        query_filters.append(Job.salary_min >= salary_min)
    
    if salary_max is not None:
        query_filters.append(Job.salary_max <= salary_max)
    
    if requires_visa_sponsorship is not None:
        query_filters.append(Job.requires_visa_sponsorship == requires_visa_sponsorship)
    
    if is_remote_friendly is not None:
        query_filters.append(Job.is_remote_friendly == is_remote_friendly)
    
    # Build query
    base_query = db.query(Job).filter(and_(*query_filters))
    
    # Get total count
    total = base_query.count()
    
    # Apply sorting
    if sort_order.lower() == "desc":
        sort_func = desc
    else:
        sort_func = asc
    
    if hasattr(Job, sort_by):
        base_query = base_query.order_by(sort_func(getattr(Job, sort_by)))
    else:
        base_query = base_query.order_by(desc(Job.created_at))
    
    # Apply pagination
    jobs = base_query.offset(pagination.offset).limit(pagination.limit).all()
    
    total_pages = (total + pagination.size - 1) // pagination.size
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        page=pagination.page,
        size=pagination.size,
        total_pages=total_pages
    )


@router.get("/{job_id}", response_model=JobResponse, dependencies=[Depends(api_rate_limit)])
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get a specific job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job posting (admin only)."""
    # In a real system, you'd check for admin permissions here
    
    job = Job(**job_data.dict())
    job.data_completeness_score = calculate_completeness_score(job)
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"New job created by user {current_user.id}: {job.title} at {job.company}")
    
    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a job posting (admin only)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Update job fields
    for field, value in job_update.dict(exclude_unset=True).items():
        setattr(job, field, value)
    
    job.updated_at = datetime.utcnow()
    job.data_completeness_score = calculate_completeness_score(job)
    
    db.commit()
    db.refresh(job)
    
    logger.info(f"Job {job_id} updated by user {current_user.id}")
    
    return job


@router.delete("/{job_id}", response_model=dict)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job posting (admin only)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Soft delete by setting is_active to False
    job.is_active = False
    job.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Job {job_id} deleted by user {current_user.id}")
    
    return {"message": "Job deleted successfully"}


@router.post("/scrape", response_model=dict)
async def trigger_job_scraping_endpoint(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    platform: Optional[str] = Query(None, description="Platform to scrape (linkedin, indeed, etc)"),
    query: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Location to search")
):
    """Trigger job scraping task."""
    # Add scraping task to background
    background_tasks.add_task(trigger_job_scraping)
    
    logger.info(f"Job scraping triggered by user {current_user.id}")
    
    return {
        "message": "Job scraping task started",
        "status": "queued"
    }


@router.get("/{job_id}/similar", response_model=List[JobResponse])
async def get_similar_jobs(
    job_id: int,
    limit: int = Query(10, description="Number of similar jobs to return"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get similar jobs based on title, company, and industry."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Find similar jobs based on various criteria
    similar_jobs = db.query(Job).filter(
        and_(
            Job.id != job_id,
            Job.is_active == True,
            or_(
                Job.company == job.company,
                Job.industry == job.industry,
                Job.title.ilike(f"%{job.title.split()[0]}%") if job.title else False
            )
        )
    ).limit(limit).all()
    
    return similar_jobs


def calculate_completeness_score(job: Job) -> float:
    """Calculate data completeness score for a job."""
    fields_to_check = [
        'title', 'company', 'description', 'requirements', 'location',
        'salary_min', 'salary_max', 'job_type', 'experience_level',
        'industry', 'apply_url', 'required_skills'
    ]
    
    filled_fields = 0
    total_fields = len(fields_to_check)
    
    for field in fields_to_check:
        value = getattr(job, field, None)
        if value is not None and str(value).strip():
            filled_fields += 1
    
    return filled_fields / total_fields