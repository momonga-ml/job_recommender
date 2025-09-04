"""Job scraping background tasks."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from sqlalchemy.orm import Session
from celery import Task

from ..celery_app import celery_app
from ..models.database import SessionLocal
from ..models.job import Job
from ..models.skill import Skill
from ..job_scraper import JobScraper
from ..parallel_scraper import ParallelJobScraper

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class that provides database session."""
    
    def __call__(self, *args, **kwargs):
        db = SessionLocal()
        try:
            return super().__call__(*args, db=db, **kwargs)
        finally:
            db.close()


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.job_scraping.scrape_jobs")
def scrape_jobs(
    self,
    platforms: List[str] = None,
    search_terms: List[str] = None,
    locations: List[str] = None,
    max_jobs_per_platform: int = 100,
    db: Session = None
) -> Dict[str, Any]:
    """Scrape jobs from specified platforms."""
    
    if platforms is None:
        platforms = ["linkedin", "indeed", "glassdoor"]
    
    if search_terms is None:
        search_terms = ["software engineer", "data scientist", "product manager", "python developer"]
    
    if locations is None:
        locations = ["San Francisco", "New York", "Seattle", "Remote"]
    
    results = {
        "total_scraped": 0,
        "new_jobs": 0,
        "updated_jobs": 0,
        "errors": [],
        "platforms": {}
    }
    
    try:
        # Initialize parallel scraper
        scraper = ParallelJobScraper()
        
        for platform in platforms:
            platform_results = {
                "scraped": 0,
                "new": 0,
                "updated": 0,
                "errors": []
            }
            
            try:
                logger.info(f"Starting scraping for platform: {platform}")
                
                # Scrape jobs for each search term and location combination
                for search_term in search_terms:
                    for location in locations:
                        try:
                            # Update task progress
                            self.update_state(
                                state="PROGRESS",
                                meta={
                                    "current_platform": platform,
                                    "current_search": search_term,
                                    "current_location": location,
                                    "total_scraped": results["total_scraped"]
                                }
                            )
                            
                            # Scrape jobs
                            scraped_jobs = scraper.scrape_platform(
                                platform=platform,
                                search_term=search_term,
                                location=location,
                                max_results=max_jobs_per_platform // (len(search_terms) * len(locations))
                            )
                            
                            # Process and save jobs
                            for job_data in scraped_jobs:
                                try:
                                    job_result = save_scraped_job(job_data, db)
                                    platform_results["scraped"] += 1
                                    results["total_scraped"] += 1
                                    
                                    if job_result["is_new"]:
                                        platform_results["new"] += 1
                                        results["new_jobs"] += 1
                                    else:
                                        platform_results["updated"] += 1
                                        results["updated_jobs"] += 1
                                    
                                except Exception as e:
                                    error_msg = f"Error saving job: {str(e)}"
                                    platform_results["errors"].append(error_msg)
                                    logger.error(error_msg)
                            
                        except Exception as e:
                            error_msg = f"Error scraping {platform} for '{search_term}' in {location}: {str(e)}"
                            platform_results["errors"].append(error_msg)
                            logger.error(error_msg)
                
                results["platforms"][platform] = platform_results
                logger.info(f"Completed scraping for {platform}: {platform_results['scraped']} jobs")
                
            except Exception as e:
                error_msg = f"Critical error with platform {platform}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Update skill statistics after scraping
        update_skill_statistics_from_jobs.delay()
        
        logger.info(f"Job scraping completed: {results['total_scraped']} total jobs")
        
    except Exception as e:
        error_msg = f"Critical error in job scraping: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg)
        raise
    
    return results


def save_scraped_job(job_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Save a scraped job to the database."""
    
    # Check if job already exists
    existing_job = None
    if job_data.get("external_job_id") and job_data.get("source_platform"):
        existing_job = db.query(Job).filter(
            Job.external_job_id == job_data["external_job_id"],
            Job.source_platform == job_data["source_platform"]
        ).first()
    
    is_new = existing_job is None
    
    if is_new:
        # Create new job
        job = Job()
    else:
        # Update existing job
        job = existing_job
    
    # Map scraped data to job model
    field_mapping = {
        "title": "title",
        "company": "company",
        "description": "description",
        "requirements": "requirements",
        "benefits": "benefits",
        "location": "location",
        "remote_type": "remote_type",
        "city": "city",
        "state": "state",
        "country": "country",
        "salary_min": "salary_min",
        "salary_max": "salary_max",
        "salary_currency": "salary_currency",
        "job_type": "job_type",
        "experience_level": "experience_level",
        "industry": "industry",
        "source_url": "source_url",
        "source_platform": "source_platform",
        "external_job_id": "external_job_id",
        "apply_url": "apply_url",
        "company_website": "company_website",
        "contact_email": "contact_email",
        "posted_date": "posted_date",
        "application_deadline": "application_deadline",
        "required_skills": "required_skills",
        "preferred_skills": "preferred_skills",
        "technologies": "technologies"
    }
    
    # Update job fields
    for scraped_field, job_field in field_mapping.items():
        if scraped_field in job_data:
            setattr(job, job_field, job_data[scraped_field])
    
    # Set job status
    job.is_active = True
    job.last_scraped = datetime.utcnow()
    
    # Calculate completeness score
    job.data_completeness_score = calculate_job_completeness(job)
    
    # Set remote-friendly flag
    if job.remote_type in ["remote", "hybrid"] or (job.description and "remote" in job.description.lower()):
        job.is_remote_friendly = True
    
    if is_new:
        job.created_at = datetime.utcnow()
        db.add(job)
    else:
        job.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Extract and update skills
    if is_new:
        extract_and_save_skills_from_job(job, db)
    
    return {"is_new": is_new, "job_id": job.id}


def calculate_job_completeness(job: Job) -> float:
    """Calculate job data completeness score."""
    
    fields_to_check = [
        "title", "company", "description", "location", "salary_min",
        "job_type", "experience_level", "apply_url", "required_skills"
    ]
    
    filled_fields = 0
    for field in fields_to_check:
        value = getattr(job, field, None)
        if value is not None and str(value).strip():
            filled_fields += 1
    
    return filled_fields / len(fields_to_check)


def extract_and_save_skills_from_job(job: Job, db: Session):
    """Extract skills from job and update skill statistics."""
    
    # Extract skills from job description and requirements
    skills = extract_skills_from_text(f"{job.description} {job.requirements or ''}")
    
    # Add explicitly mentioned skills
    if job.required_skills:
        try:
            required_skills = json.loads(job.required_skills)
            if isinstance(required_skills, list):
                skills.extend(required_skills)
        except json.JSONDecodeError:
            skills.extend([s.strip() for s in job.required_skills.split(",")])
    
    if job.preferred_skills:
        try:
            preferred_skills = json.loads(job.preferred_skills)
            if isinstance(preferred_skills, list):
                skills.extend(preferred_skills)
        except json.JSONDecodeError:
            skills.extend([s.strip() for s in job.preferred_skills.split(",")])
    
    # Update skill records
    for skill_name in set(skills):  # Remove duplicates
        if not skill_name.strip():
            continue
        
        normalized_name = Skill.normalize_skill_name(skill_name)
        
        # Find or create skill
        skill = db.query(Skill).filter(Skill.normalized_name == normalized_name).first()
        
        if not skill:
            skill = Skill(
                name=skill_name,
                normalized_name=normalized_name,
                display_name=skill_name.title(),
                category=categorize_skill(skill_name)
            )
            db.add(skill)
        
        # Update statistics
        skill.job_mentions_count += 1
        skill.last_job_mention = datetime.utcnow()
    
    db.commit()


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using keyword matching."""
    
    # Common technical skills (this would be much more comprehensive in production)
    skill_keywords = [
        # Programming languages
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "PHP", "Ruby",
        "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL",
        
        # Frameworks and libraries
        "React", "Angular", "Vue", "Django", "Flask", "Spring", "Express", "Node.js",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        
        # Databases
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
        
        # Cloud and DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "GitLab", "GitHub Actions",
        
        # Other technologies
        "Git", "Linux", "Bash", "API", "REST", "GraphQL", "Microservices", "Machine Learning",
        "Deep Learning", "AI", "Data Science", "Analytics", "Tableau", "Power BI"
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    return found_skills


def categorize_skill(skill_name: str) -> str:
    """Categorize a skill based on its name."""
    
    skill_lower = skill_name.lower()
    
    programming_languages = ["python", "java", "javascript", "c++", "c#", "go", "rust", "php", "ruby"]
    frameworks = ["react", "angular", "vue", "django", "flask", "spring", "express"]
    databases = ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"]
    cloud = ["aws", "azure", "gcp", "docker", "kubernetes"]
    
    if skill_lower in programming_languages:
        return "Programming Language"
    elif skill_lower in frameworks:
        return "Framework"
    elif skill_lower in databases:
        return "Database"
    elif skill_lower in cloud:
        return "Cloud/DevOps"
    else:
        return "Technology"


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.job_scraping.scrape_jobs_periodic")
def scrape_jobs_periodic(self, db: Session = None) -> Dict[str, Any]:
    """Periodic job scraping task."""
    
    logger.info("Starting periodic job scraping")
    
    # Use default parameters for periodic scraping
    result = scrape_jobs.apply_async()
    
    return {"message": "Periodic job scraping started", "task_id": result.id}


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.job_scraping.cleanup_old_jobs")
def cleanup_old_jobs(self, days_old: int = 90, db: Session = None) -> Dict[str, Any]:
    """Clean up old job postings."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Mark old jobs as inactive
    old_jobs = db.query(Job).filter(
        Job.created_at < cutoff_date,
        Job.is_active == True
    ).all()
    
    deactivated_count = 0
    for job in old_jobs:
        job.is_active = False
        job.updated_at = datetime.utcnow()
        deactivated_count += 1
    
    db.commit()
    
    logger.info(f"Deactivated {deactivated_count} old jobs")
    
    return {"deactivated_jobs": deactivated_count}


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.job_scraping.update_skill_statistics_from_jobs")
def update_skill_statistics_from_jobs(self, db: Session = None) -> Dict[str, Any]:
    """Update skill statistics based on current job postings."""
    
    # Get all skills
    skills = db.query(Skill).all()
    
    updated_skills = 0
    for skill in skills:
        # Calculate demand score based on recent mentions
        recent_jobs_with_skill = db.query(Job).filter(
            Job.is_active == True,
            Job.created_at >= datetime.utcnow() - timedelta(days=90)
        ).count()
        
        if recent_jobs_with_skill > 0:
            # Simple demand calculation
            skill.demand_score = min((skill.job_mentions_count / recent_jobs_with_skill) * 100, 100)
            updated_skills += 1
    
    db.commit()
    
    return {"updated_skills": updated_skills}