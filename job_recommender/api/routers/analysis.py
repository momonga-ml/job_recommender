"""Analysis router for job-resume matching."""

from datetime import datetime
from typing import List, Optional
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ...models.database import get_db
from ...models.analysis import Analysis
from ...models.job import Job
from ...models.resume import Resume
from ...models.user import User
from ..dependencies import get_current_user, get_pagination_params, PaginationParams, api_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class AnalysisRequest(BaseModel):
    job_id: int
    resume_id: int


class SkillAnalysis(BaseModel):
    matching_skills: List[str]
    missing_skills: List[str]
    additional_skills: List[str]


class AnalysisResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    resume_id: int
    overall_match_score: float
    confidence_score: Optional[float]
    skills_match_score: Optional[float]
    experience_match_score: Optional[float]
    education_match_score: Optional[float]
    location_match_score: Optional[float]
    salary_match_score: Optional[float]
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    additional_skills: List[str] = []
    experience_gap_years: Optional[float]
    experience_level_match: Optional[str]
    education_requirement_met: bool
    location_compatible: bool
    salary_expectation_met: Optional[bool]
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    detailed_feedback: Optional[str]
    match_grade: str
    is_good_match: bool
    is_bookmarked: bool
    user_rating: Optional[int]
    created_at: datetime
    
    # Related job and resume data
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    resume_filename: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total: int
    page: int
    size: int
    total_pages: int


class AnalysisFeedback(BaseModel):
    user_rating: Optional[int] = None  # 1-5 stars
    user_feedback: Optional[str] = None
    is_bookmarked: Optional[bool] = None


def perform_job_resume_analysis(job: Job, resume: Resume, user: User, db: Session) -> Analysis:
    """Perform comprehensive job-resume matching analysis."""
    
    # Initialize analysis record
    analysis = Analysis(
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        overall_match_score=0.0
    )
    
    try:
        # 1. Skills Analysis
        skills_analysis = analyze_skills_match(job, resume)
        analysis.skills_match_score = skills_analysis["score"]
        analysis.matching_skills = json.dumps(skills_analysis["matching"])
        analysis.missing_skills = json.dumps(skills_analysis["missing"])
        analysis.additional_skills = json.dumps(skills_analysis["additional"])
        
        # 2. Experience Analysis
        experience_analysis = analyze_experience_match(job, resume)
        analysis.experience_match_score = experience_analysis["score"]
        analysis.experience_gap_years = experience_analysis["gap_years"]
        analysis.experience_level_match = experience_analysis["level_match"]
        analysis.relevant_experience_years = experience_analysis["relevant_years"]
        
        # 3. Education Analysis
        education_analysis = analyze_education_match(job, resume)
        analysis.education_match_score = education_analysis["score"]
        analysis.education_requirement_met = education_analysis["requirement_met"]
        analysis.education_level_match = education_analysis["level_match"]
        
        # 4. Location Analysis
        location_analysis = analyze_location_compatibility(job, resume, user)
        analysis.location_match_score = location_analysis["score"]
        analysis.location_compatible = location_analysis["compatible"]
        analysis.relocation_required = location_analysis["relocation_required"]
        analysis.remote_work_compatible = location_analysis["remote_compatible"]
        
        # 5. Salary Analysis
        salary_analysis = analyze_salary_match(job, user)
        analysis.salary_match_score = salary_analysis["score"]
        analysis.salary_expectation_met = salary_analysis["expectation_met"]
        analysis.salary_gap_percentage = salary_analysis["gap_percentage"]
        
        # 6. Content Similarity (TF-IDF)
        content_similarity = calculate_content_similarity(job, resume)
        
        # 7. Calculate Overall Match Score
        scores = {
            "skills": analysis.skills_match_score or 0,
            "experience": analysis.experience_match_score or 0,
            "education": analysis.education_match_score or 0,
            "location": analysis.location_match_score or 0,
            "salary": analysis.salary_match_score or 0,
            "content": content_similarity * 100
        }
        
        # Weighted average
        weights = {
            "skills": 0.30,
            "experience": 0.25,
            "education": 0.15,
            "location": 0.10,
            "salary": 0.10,
            "content": 0.10
        }
        
        overall_score = sum(scores[key] * weights[key] for key in scores.keys())
        analysis.overall_match_score = min(max(overall_score, 0), 100)
        
        # 8. Generate Insights
        insights = generate_analysis_insights(analysis, job, resume)
        analysis.strengths = json.dumps(insights["strengths"])
        analysis.weaknesses = json.dumps(insights["weaknesses"])
        analysis.recommendations = json.dumps(insights["recommendations"])
        analysis.detailed_feedback = insights["detailed_feedback"]
        analysis.cover_letter_suggestions = insights["cover_letter_suggestions"]
        
        # 9. Set confidence score
        analysis.confidence_score = calculate_confidence_score(analysis, job, resume)
        
        # 10. Processing metadata
        analysis.analysis_version = "1.0"
        analysis.model_used = "custom_tfidf"
        
        logger.info(f"Analysis completed for job {job.id} and resume {resume.id}: {analysis.overall_match_score:.1f}%")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        analysis.overall_match_score = 0.0
        analysis.detailed_feedback = f"Analysis failed: {str(e)}"
    
    return analysis


def analyze_skills_match(job: Job, resume: Resume) -> dict:
    """Analyze skills matching between job and resume."""
    
    # Parse skills from job and resume
    job_skills = parse_skills_from_job(job)
    resume_skills = parse_skills_from_resume(resume)
    
    # Normalize skills for comparison
    job_skills_normalized = [skill.lower().strip() for skill in job_skills]
    resume_skills_normalized = [skill.lower().strip() for skill in resume_skills]
    
    # Find matches
    matching_skills = []
    for job_skill in job_skills:
        for resume_skill in resume_skills:
            if job_skill.lower().strip() == resume_skill.lower().strip():
                matching_skills.append(job_skill)
                break
    
    # Find missing skills
    missing_skills = []
    for job_skill in job_skills:
        if job_skill.lower().strip() not in resume_skills_normalized:
            missing_skills.append(job_skill)
    
    # Find additional skills
    additional_skills = []
    for resume_skill in resume_skills:
        if resume_skill.lower().strip() not in job_skills_normalized:
            additional_skills.append(resume_skill)
    
    # Calculate score
    if len(job_skills) > 0:
        score = (len(matching_skills) / len(job_skills)) * 100
    else:
        score = 100  # No specific skills required
    
    return {
        "score": score,
        "matching": matching_skills,
        "missing": missing_skills,
        "additional": additional_skills
    }


def parse_skills_from_job(job: Job) -> List[str]:
    """Extract skills from job posting."""
    skills = []
    
    # Parse required_skills JSON
    if job.required_skills:
        try:
            required_skills = json.loads(job.required_skills)
            skills.extend(required_skills)
        except:
            # If not JSON, treat as comma-separated string
            skills.extend([s.strip() for s in job.required_skills.split(",")])
    
    # Parse preferred_skills JSON
    if job.preferred_skills:
        try:
            preferred_skills = json.loads(job.preferred_skills)
            skills.extend(preferred_skills)
        except:
            skills.extend([s.strip() for s in job.preferred_skills.split(",")])
    
    # Parse technologies JSON
    if job.technologies:
        try:
            technologies = json.loads(job.technologies)
            skills.extend(technologies)
        except:
            skills.extend([s.strip() for s in job.technologies.split(",")])
    
    return list(set(skills))  # Remove duplicates


def parse_skills_from_resume(resume: Resume) -> List[str]:
    """Extract skills from resume."""
    skills = []
    
    if resume.skills:
        try:
            resume_skills = json.loads(resume.skills)
            skills.extend(resume_skills)
        except:
            skills.extend([s.strip() for s in resume.skills.split(",")])
    
    return list(set(skills))


def analyze_experience_match(job: Job, resume: Resume) -> dict:
    """Analyze experience matching."""
    
    # Extract experience requirements from job
    required_years = extract_experience_years_from_job(job)
    candidate_years = resume.total_experience_years or 0
    
    # Calculate gap
    gap_years = max(0, required_years - candidate_years) if required_years else 0
    
    # Determine level match
    level_match = "match"
    if required_years and candidate_years < required_years * 0.8:
        level_match = "under"
    elif required_years and candidate_years > required_years * 1.5:
        level_match = "over"
    
    # Calculate score
    if required_years == 0:
        score = 100  # No specific requirements
    elif candidate_years >= required_years:
        score = 100
    elif candidate_years >= required_years * 0.8:
        score = 80
    elif candidate_years >= required_years * 0.6:
        score = 60
    else:
        score = 40
    
    return {
        "score": score,
        "gap_years": gap_years,
        "level_match": level_match,
        "relevant_years": candidate_years
    }


def extract_experience_years_from_job(job: Job) -> int:
    """Extract required experience years from job description."""
    # This is a simplified implementation
    # In reality, you'd use NLP to parse requirements
    
    text = f"{job.description} {job.requirements or ''}"
    
    # Simple regex patterns for experience requirements
    import re
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s+)?experience',
        r'(\d+)\+?\s*years?\s*experience',
        r'minimum\s+(\d+)\s*years?',
        r'at\s+least\s+(\d+)\s*years?'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            return int(matches[0])
    
    return 0


def analyze_education_match(job: Job, resume: Resume) -> dict:
    """Analyze education matching."""
    
    # Simple implementation - in reality, you'd parse education requirements
    requirement_met = True  # Default to true if no specific requirements
    level_match = "match"
    score = 100
    
    # This would be expanded with actual education parsing logic
    
    return {
        "score": score,
        "requirement_met": requirement_met,
        "level_match": level_match
    }


def analyze_location_compatibility(job: Job, resume: Resume, user: User) -> dict:
    """Analyze location compatibility."""
    
    compatible = True
    relocation_required = False
    remote_compatible = True
    score = 100
    
    # Check if job is remote-friendly
    if job.remote_type in ["remote", "hybrid"]:
        remote_compatible = True
        score = 100
    elif job.location and user.location:
        # Simple location matching - in reality, use geolocation services
        if job.location.lower() in user.location.lower() or user.location.lower() in job.location.lower():
            compatible = True
            score = 100
        else:
            relocation_required = user.willing_to_relocate if user.willing_to_relocate else False
            compatible = relocation_required
            score = 70 if relocation_required else 30
    
    return {
        "score": score,
        "compatible": compatible,
        "relocation_required": relocation_required,
        "remote_compatible": remote_compatible
    }


def analyze_salary_match(job: Job, user: User) -> dict:
    """Analyze salary expectations."""
    
    expectation_met = None
    gap_percentage = None
    score = 100  # Default if no salary information
    
    if job.salary_min and user.desired_salary_min:
        if job.salary_min >= user.desired_salary_min:
            expectation_met = True
            score = 100
        else:
            expectation_met = False
            gap_percentage = ((user.desired_salary_min - job.salary_min) / user.desired_salary_min) * 100
            score = max(50, 100 - gap_percentage)
    
    return {
        "score": score,
        "expectation_met": expectation_met,
        "gap_percentage": gap_percentage
    }


def calculate_content_similarity(job: Job, resume: Resume) -> float:
    """Calculate content similarity using TF-IDF."""
    
    job_text = f"{job.title} {job.description} {job.requirements or ''}"
    resume_text = resume.raw_text or ""
    
    if not job_text.strip() or not resume_text.strip():
        return 0.0
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = vectorizer.fit_transform([job_text, resume_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    except Exception as e:
        logger.error(f"Error calculating content similarity: {e}")
        return 0.0


def generate_analysis_insights(analysis: Analysis, job: Job, resume: Resume) -> dict:
    """Generate insights and recommendations."""
    
    strengths = []
    weaknesses = []
    recommendations = []
    
    # Analyze strengths
    if analysis.skills_match_score and analysis.skills_match_score >= 80:
        strengths.append("Strong technical skills alignment")
    
    if analysis.experience_match_score and analysis.experience_match_score >= 80:
        strengths.append("Good experience match")
    
    if analysis.location_match_score and analysis.location_match_score >= 80:
        strengths.append("Location compatibility")
    
    # Analyze weaknesses
    if analysis.skills_match_score and analysis.skills_match_score < 60:
        weaknesses.append("Skills gap exists")
        recommendations.append("Consider gaining skills in missing areas")
    
    if analysis.experience_match_score and analysis.experience_match_score < 60:
        weaknesses.append("Experience level below requirements")
        recommendations.append("Highlight relevant projects and achievements")
    
    # Generate detailed feedback
    detailed_feedback = f"Overall match score: {analysis.overall_match_score:.1f}%. "
    
    if analysis.overall_match_score >= 80:
        detailed_feedback += "This is an excellent match! You meet most requirements."
    elif analysis.overall_match_score >= 60:
        detailed_feedback += "This is a good match with some areas for improvement."
    else:
        detailed_feedback += "This position may be challenging but could be worth considering."
    
    cover_letter_suggestions = "Highlight your matching skills and relevant experience."
    
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "detailed_feedback": detailed_feedback,
        "cover_letter_suggestions": cover_letter_suggestions
    }


def calculate_confidence_score(analysis: Analysis, job: Job, resume: Resume) -> float:
    """Calculate confidence in the analysis."""
    
    confidence = 100.0
    
    # Reduce confidence if data is incomplete
    if not resume.raw_text:
        confidence -= 20
    
    if not job.description:
        confidence -= 15
    
    if not resume.skills:
        confidence -= 10
    
    if not job.required_skills:
        confidence -= 10
    
    return max(confidence, 0)


@router.post("/", response_model=AnalysisResponse)
async def create_analysis(
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job-resume analysis."""
    
    # Validate job exists
    job = db.query(Job).filter(
        Job.id == analysis_request.job_id,
        Job.is_active == True
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Validate resume exists and belongs to user
    resume = db.query(Resume).filter(
        Resume.id == analysis_request.resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Check if analysis already exists
    existing_analysis = db.query(Analysis).filter(
        Analysis.user_id == current_user.id,
        Analysis.job_id == analysis_request.job_id,
        Analysis.resume_id == analysis_request.resume_id,
        Analysis.is_active == True
    ).first()
    
    if existing_analysis:
        # Return existing analysis
        return existing_analysis
    
    # Perform analysis
    start_time = datetime.utcnow()
    analysis = perform_job_resume_analysis(job, resume, current_user, db)
    end_time = datetime.utcnow()
    
    analysis.processing_time_seconds = (end_time - start_time).total_seconds()
    
    # Save analysis
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    logger.info(f"Analysis created: {analysis.id} for user {current_user.id}")
    
    return analysis


@router.get("/", response_model=AnalysisListResponse, dependencies=[Depends(api_rate_limit)])
async def list_user_analyses(
    pagination: PaginationParams = Depends(get_pagination_params),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    resume_id: Optional[int] = Query(None, description="Filter by resume ID"),
    min_score: Optional[float] = Query(None, description="Minimum match score"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's analyses with filtering."""
    
    query = db.query(Analysis).filter(
        Analysis.user_id == current_user.id,
        Analysis.is_active == True
    )
    
    # Apply filters
    if job_id:
        query = query.filter(Analysis.job_id == job_id)
    
    if resume_id:
        query = query.filter(Analysis.resume_id == resume_id)
    
    if min_score:
        query = query.filter(Analysis.overall_match_score >= min_score)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    analyses = query.order_by(Analysis.created_at.desc()).offset(
        pagination.offset
    ).limit(pagination.limit).all()
    
    total_pages = (total + pagination.size - 1) // pagination.size
    
    return AnalysisListResponse(
        analyses=analyses,
        total=total,
        page=pagination.page,
        size=pagination.size,
        total_pages=total_pages
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse, dependencies=[Depends(api_rate_limit)])
async def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific analysis."""
    
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id,
        Analysis.is_active == True
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return analysis


@router.put("/{analysis_id}/feedback", response_model=dict)
async def update_analysis_feedback(
    analysis_id: int,
    feedback: AnalysisFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update analysis feedback."""
    
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id,
        Analysis.is_active == True
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Update feedback fields
    for field, value in feedback.dict(exclude_unset=True).items():
        setattr(analysis, field, value)
    
    analysis.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Feedback updated successfully"}


@router.delete("/{analysis_id}", response_model=dict)
async def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an analysis."""
    
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Soft delete
    analysis.is_active = False
    analysis.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Analysis deleted successfully"}