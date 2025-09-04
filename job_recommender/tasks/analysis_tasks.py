"""Analysis and recommendation background tasks."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc
from celery import Task

from ..celery_app import celery_app
from ..models.database import SessionLocal
from ..models.analysis import Analysis
from ..models.job import Job
from ..models.resume import Resume
from ..models.user import User
from ..models.skill import Skill

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class that provides database session."""
    
    def __call__(self, *args, **kwargs):
        db = SessionLocal()
        try:
            return super().__call__(*args, db=db, **kwargs)
        finally:
            db.close()


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.analysis_tasks.update_skill_statistics")
def update_skill_statistics(self, db: Session = None) -> Dict[str, Any]:
    """Update skill statistics and market data."""
    
    # Get all active jobs from last 90 days
    recent_jobs = db.query(Job).filter(
        Job.is_active == True,
        Job.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    # Get all skills
    skills = db.query(Skill).all()
    
    updated_skills = 0
    
    for skill in skills:
        # Calculate demand score based on job mentions
        job_mentions = 0
        recent_mentions = 0
        
        for job in recent_jobs:
            job_text = f"{job.description} {job.requirements or ''} {job.required_skills or ''} {job.preferred_skills or ''}"
            
            if skill.name.lower() in job_text.lower():
                job_mentions += 1
                if job.created_at >= datetime.utcnow() - timedelta(days=30):
                    recent_mentions += 1
        
        # Update skill statistics
        skill.job_mentions_count = job_mentions
        if job_mentions > 0:
            skill.last_job_mention = datetime.utcnow()
        
        # Calculate demand score (0-100)
        if len(recent_jobs) > 0:
            skill.demand_score = min((job_mentions / len(recent_jobs)) * 100, 100)
        
        # Determine growth trend
        old_mentions = skill.job_mentions_count - recent_mentions
        if recent_mentions > old_mentions:
            skill.growth_trend = "growing"
        elif recent_mentions < old_mentions:
            skill.growth_trend = "declining"
        else:
            skill.growth_trend = "stable"
        
        skill.last_updated_stats = datetime.utcnow()
        updated_skills += 1
    
    db.commit()
    
    logger.info(f"Updated statistics for {updated_skills} skills")
    
    return {
        "updated_skills": updated_skills,
        "total_jobs_analyzed": len(recent_jobs)
    }


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.analysis_tasks.generate_user_recommendations")
def generate_user_recommendations(self, user_id: int, db: Session = None) -> Dict[str, Any]:
    """Generate job recommendations for a specific user."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Get user's primary resume
    resume = db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.is_primary == True,
        Resume.is_active == True
    ).first()
    
    if not resume:
        # Get most recent resume
        resume = db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_active == True
        ).order_by(Resume.created_at.desc()).first()
    
    if not resume:
        return {"error": "No resume found for user"}
    
    # Get active jobs
    jobs = db.query(Job).filter(
        Job.is_active == True,
        Job.created_at >= datetime.utcnow() - timedelta(days=90)
    ).limit(1000).all()
    
    recommendations = []
    
    # Simple matching algorithm for background task
    for job in jobs:
        try:
            match_score = calculate_simple_match_score(job, resume, user)
            
            if match_score >= 60:  # Minimum threshold
                recommendations.append({
                    "job_id": job.id,
                    "match_score": match_score,
                    "job_title": job.title,
                    "company": job.company,
                    "location": job.location
                })
        except Exception as e:
            logger.error(f"Error calculating match for job {job.id}: {e}")
            continue
    
    # Sort by match score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Store top recommendations (you could cache these in Redis)
    top_recommendations = recommendations[:50]
    
    return {
        "user_id": user_id,
        "total_recommendations": len(top_recommendations),
        "top_score": top_recommendations[0]["match_score"] if top_recommendations else 0,
        "generated_at": datetime.utcnow().isoformat()
    }


def calculate_simple_match_score(job: Job, resume: Resume, user: User) -> float:
    """Calculate a simple match score for background processing."""
    
    score = 0.0
    
    # Skills matching (40% weight)
    skills_score = calculate_skills_overlap(job, resume)
    score += skills_score * 0.4
    
    # Experience level (30% weight)
    experience_score = calculate_experience_match(job, resume)
    score += experience_score * 0.3
    
    # Location preference (20% weight)
    location_score = calculate_location_match(job, user)
    score += location_score * 0.2
    
    # Salary match (10% weight)
    salary_score = calculate_salary_match(job, user)
    score += salary_score * 0.1
    
    return min(score * 100, 100)


def calculate_skills_overlap(job: Job, resume: Resume) -> float:
    """Calculate skills overlap between job and resume."""
    
    # Extract job skills
    job_skills = set()
    
    if job.required_skills:
        try:
            required_skills = json.loads(job.required_skills)
            job_skills.update(skill.lower() for skill in required_skills)
        except:
            job_skills.update(skill.strip().lower() for skill in job.required_skills.split(','))
    
    if job.preferred_skills:
        try:
            preferred_skills = json.loads(job.preferred_skills)
            job_skills.update(skill.lower() for skill in preferred_skills)
        except:
            job_skills.update(skill.strip().lower() for skill in job.preferred_skills.split(','))
    
    # Extract resume skills
    resume_skills = set()
    if resume.skills:
        try:
            skills = json.loads(resume.skills)
            resume_skills.update(skill.lower() for skill in skills)
        except:
            resume_skills.update(skill.strip().lower() for skill in resume.skills.split(','))
    
    # Calculate overlap
    if not job_skills:
        return 1.0  # No specific requirements
    
    overlap = len(job_skills.intersection(resume_skills))
    return overlap / len(job_skills)


def calculate_experience_match(job: Job, resume: Resume) -> float:
    """Calculate experience level match."""
    
    # Extract required experience from job description
    required_years = extract_experience_requirement(job.description or "")
    candidate_years = resume.total_experience_years or 0
    
    if required_years == 0:
        return 1.0  # No specific requirement
    
    if candidate_years >= required_years:
        return 1.0
    elif candidate_years >= required_years * 0.8:
        return 0.8
    elif candidate_years >= required_years * 0.6:
        return 0.6
    else:
        return 0.4


def extract_experience_requirement(text: str) -> int:
    """Extract experience requirement from job description."""
    import re
    
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s+)?experience',
        r'minimum\s+(\d+)\s*years?',
        r'at\s+least\s+(\d+)\s*years?'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            return int(matches[0])
    
    return 0


def calculate_location_match(job: Job, user: User) -> float:
    """Calculate location compatibility."""
    
    # Remote work gets full score
    if job.remote_type in ['remote', 'hybrid']:
        return 1.0
    
    # If no location data, return neutral score
    if not job.location or not user.location:
        return 0.7
    
    # Simple location matching
    job_location = job.location.lower()
    user_location = user.location.lower()
    
    if user_location in job_location or job_location in user_location:
        return 1.0
    elif user.willing_to_relocate:
        return 0.8
    else:
        return 0.3


def calculate_salary_match(job: Job, user: User) -> float:
    """Calculate salary expectation match."""
    
    if not job.salary_min or not user.desired_salary_min:
        return 0.8  # Neutral if no data
    
    if job.salary_min >= user.desired_salary_min:
        return 1.0
    else:
        ratio = job.salary_min / user.desired_salary_min
        return max(0.3, ratio)


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.analysis_tasks.batch_analyze_jobs")
def batch_analyze_jobs(self, user_id: int, job_ids: List[int], db: Session = None) -> Dict[str, Any]:
    """Perform batch analysis of jobs for a user."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Get user's primary resume
    resume = db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.is_primary == True,
        Resume.is_active == True
    ).first()
    
    if not resume:
        return {"error": "No primary resume found for user"}
    
    results = []
    
    for job_id in job_ids:
        job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
        
        if not job:
            continue
        
        try:
            # Check if analysis already exists
            existing_analysis = db.query(Analysis).filter(
                Analysis.user_id == user_id,
                Analysis.job_id == job_id,
                Analysis.resume_id == resume.id,
                Analysis.is_active == True
            ).first()
            
            if existing_analysis:
                results.append({
                    "job_id": job_id,
                    "analysis_id": existing_analysis.id,
                    "match_score": existing_analysis.overall_match_score,
                    "status": "existing"
                })
                continue
            
            # Create new analysis
            match_score = calculate_simple_match_score(job, resume, user)
            
            analysis = Analysis(
                user_id=user_id,
                job_id=job_id,
                resume_id=resume.id,
                overall_match_score=match_score,
                skills_match_score=calculate_skills_overlap(job, resume) * 100,
                experience_match_score=calculate_experience_match(job, resume) * 100,
                location_match_score=calculate_location_match(job, user) * 100,
                salary_match_score=calculate_salary_match(job, user) * 100,
                analysis_version="1.0",
                model_used="simple_batch"
            )
            
            db.add(analysis)
            db.flush()  # Get ID without committing
            
            results.append({
                "job_id": job_id,
                "analysis_id": analysis.id,
                "match_score": match_score,
                "status": "created"
            })
            
        except Exception as e:
            logger.error(f"Error analyzing job {job_id}: {e}")
            results.append({
                "job_id": job_id,
                "error": str(e),
                "status": "failed"
            })
    
    db.commit()
    
    return {
        "user_id": user_id,
        "total_jobs": len(job_ids),
        "successful_analyses": len([r for r in results if r.get("status") != "failed"]),
        "results": results
    }


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.analysis_tasks.cleanup_old_analyses")
def cleanup_old_analyses(self, days_old: int = 180, db: Session = None) -> Dict[str, Any]:
    """Clean up old analysis records."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Mark old analyses as inactive
    old_analyses = db.query(Analysis).filter(
        Analysis.created_at < cutoff_date,
        Analysis.is_active == True
    ).all()
    
    deactivated_count = 0
    for analysis in old_analyses:
        analysis.is_active = False
        analysis.updated_at = datetime.utcnow()
        deactivated_count += 1
    
    db.commit()
    
    logger.info(f"Deactivated {deactivated_count} old analyses")
    
    return {"deactivated_analyses": deactivated_count}