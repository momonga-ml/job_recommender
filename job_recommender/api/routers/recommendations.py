"""Recommendations router with enhanced matching algorithm."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import logging
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from ...models.database import get_db
from ...models.job import Job
from ...models.resume import Resume
from ...models.user import User
from ...models.analysis import Analysis
from ...models.skill import Skill
from ..dependencies import get_current_user, get_pagination_params, PaginationParams, api_rate_limit, cache_response

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class JobRecommendation(BaseModel):
    job_id: int
    job_title: str
    company: str
    location: Optional[str]
    salary_range: Optional[str]
    match_score: float
    match_grade: str
    confidence_score: float
    reasons: List[str]
    missing_skills: List[str]
    matching_skills: List[str]
    remote_type: Optional[str]
    posted_date: Optional[datetime]
    apply_url: Optional[str]
    
    class Config:
        from_attributes = True


class RecommendationsResponse(BaseModel):
    recommendations: List[JobRecommendation]
    total: int
    page: int
    size: int
    resume_id: Optional[int]
    filters_applied: Dict[str, Any]
    generated_at: datetime


class RecommendationFeedback(BaseModel):
    job_id: int
    feedback_type: str  # "like", "dislike", "not_interested", "applied"
    reason: Optional[str] = None


class RecommendationFilters(BaseModel):
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    location: Optional[str] = None
    remote_only: Optional[bool] = None
    experience_level: Optional[str] = None
    industry: Optional[str] = None
    job_type: Optional[str] = None
    exclude_applied: bool = True


class SkillGapAnalysis(BaseModel):
    skill_name: str
    importance_score: float
    market_demand: float
    learning_resources: List[str]
    estimated_learning_time: Optional[str]


class RecommendationInsights(BaseModel):
    total_matches: int
    top_skills_in_demand: List[str]
    salary_insights: Dict[str, Any]
    location_insights: Dict[str, Any]
    skill_gaps: List[SkillGapAnalysis]
    market_trends: List[str]


class EnhancedMatchingEngine:
    """Enhanced job matching engine with multiple algorithms."""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        self.scaler = StandardScaler()
    
    def calculate_enhanced_match_score(
        self,
        job: Job,
        resume: Resume,
        user: User,
        user_preferences: Dict = None
    ) -> Dict[str, Any]:
        """Calculate enhanced match score using multiple factors."""
        
        scores = {}
        reasons = []
        
        # 1. Content Similarity (TF-IDF + Cosine Similarity)
        content_score = self._calculate_content_similarity(job, resume)
        scores['content'] = content_score
        
        # 2. Skills Matching (Exact + Semantic)
        skills_analysis = self._analyze_skills_match(job, resume)
        scores['skills'] = skills_analysis['score']
        
        # 3. Experience Level Matching
        experience_score = self._calculate_experience_match(job, resume)
        scores['experience'] = experience_score
        
        # 4. Salary Compatibility
        salary_score = self._calculate_salary_compatibility(job, user)
        scores['salary'] = salary_score
        
        # 5. Location Preference
        location_score = self._calculate_location_preference(job, user)
        scores['location'] = location_score
        
        # 6. Company Preference (based on history)
        company_score = self._calculate_company_preference(job, user)
        scores['company'] = company_score
        
        # 7. Recency and Relevance
        recency_score = self._calculate_job_recency_score(job)
        scores['recency'] = recency_score
        
        # Calculate weighted overall score
        weights = {
            'content': 0.25,
            'skills': 0.30,
            'experience': 0.20,
            'salary': 0.10,
            'location': 0.05,
            'company': 0.05,
            'recency': 0.05
        }
        
        overall_score = sum(scores[key] * weights[key] for key in weights.keys())
        
        # Generate reasons for the match
        if scores['skills'] > 0.8:
            reasons.append("Strong skills alignment")
        if scores['experience'] > 0.8:
            reasons.append("Experience level matches")
        if scores['content'] > 0.7:
            reasons.append("Job description matches your background")
        if scores['salary'] > 0.8:
            reasons.append("Salary meets expectations")
        if scores['location'] > 0.9:
            reasons.append("Great location match")
        
        # Calculate confidence based on data availability
        confidence = self._calculate_confidence_score(job, resume, scores)
        
        return {
            'overall_score': min(max(overall_score * 100, 0), 100),
            'component_scores': {k: v * 100 for k, v in scores.items()},
            'reasons': reasons,
            'confidence': confidence,
            'skills_analysis': skills_analysis
        }
    
    def _calculate_content_similarity(self, job: Job, resume: Resume) -> float:
        """Calculate content similarity using TF-IDF."""
        job_text = f"{job.title} {job.description} {job.requirements or ''}"
        resume_text = resume.raw_text or ""
        
        if not job_text.strip() or not resume_text.strip():
            return 0.0
        
        try:
            documents = [job_text, resume_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating content similarity: {e}")
            return 0.0
    
    def _analyze_skills_match(self, job: Job, resume: Resume) -> Dict[str, Any]:
        """Analyze skills matching with semantic understanding."""
        
        job_skills = self._extract_skills_from_job(job)
        resume_skills = self._extract_skills_from_resume(resume)
        
        # Normalize skills
        job_skills_norm = {skill.lower().strip() for skill in job_skills}
        resume_skills_norm = {skill.lower().strip() for skill in resume_skills}
        
        # Direct matches
        matching_skills = list(job_skills_norm.intersection(resume_skills_norm))
        missing_skills = list(job_skills_norm - resume_skills_norm)
        additional_skills = list(resume_skills_norm - job_skills_norm)
        
        # Calculate score
        if len(job_skills) > 0:
            score = len(matching_skills) / len(job_skills)
        else:
            score = 1.0  # No specific requirements
        
        return {
            'score': score,
            'matching_skills': [skill.title() for skill in matching_skills],
            'missing_skills': [skill.title() for skill in missing_skills],
            'additional_skills': [skill.title() for skill in additional_skills]
        }
    
    def _extract_skills_from_job(self, job: Job) -> List[str]:
        """Extract skills from job posting."""
        skills = []
        
        for field in [job.required_skills, job.preferred_skills, job.technologies]:
            if field:
                try:
                    parsed_skills = json.loads(field)
                    if isinstance(parsed_skills, list):
                        skills.extend(parsed_skills)
                except json.JSONDecodeError:
                    # Treat as comma-separated string
                    skills.extend([s.strip() for s in field.split(',')])
        
        return list(set(skills))
    
    def _extract_skills_from_resume(self, resume: Resume) -> List[str]:
        """Extract skills from resume."""
        skills = []
        
        if resume.skills:
            try:
                parsed_skills = json.loads(resume.skills)
                if isinstance(parsed_skills, list):
                    skills.extend(parsed_skills)
            except json.JSONDecodeError:
                skills.extend([s.strip() for s in resume.skills.split(',')])
        
        return list(set(skills))
    
    def _calculate_experience_match(self, job: Job, resume: Resume) -> float:
        """Calculate experience level match."""
        
        # Extract required experience from job
        required_years = self._extract_required_experience(job)
        candidate_years = resume.total_experience_years or 0
        
        if required_years == 0:
            return 1.0  # No requirement specified
        
        if candidate_years >= required_years:
            return 1.0
        elif candidate_years >= required_years * 0.8:
            return 0.9
        elif candidate_years >= required_years * 0.6:
            return 0.7
        else:
            return 0.5
    
    def _extract_required_experience(self, job: Job) -> int:
        """Extract required experience years from job description."""
        import re
        
        text = f"{job.description} {job.requirements or ''}"
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
    
    def _calculate_salary_compatibility(self, job: Job, user: User) -> float:
        """Calculate salary compatibility."""
        
        if not job.salary_min or not user.desired_salary_min:
            return 0.8  # Neutral score if no data
        
        if job.salary_min >= user.desired_salary_min:
            return 1.0
        else:
            # Calculate how close it is
            ratio = job.salary_min / user.desired_salary_min
            return max(0.3, ratio)
    
    def _calculate_location_preference(self, job: Job, user: User) -> float:
        """Calculate location preference score."""
        
        # Remote work preference
        if job.remote_type in ['remote', 'hybrid']:
            return 1.0
        
        # Location matching (simplified)
        if not job.location or not user.location:
            return 0.7  # Neutral if no data
        
        job_location = job.location.lower()
        user_location = user.location.lower()
        
        if user_location in job_location or job_location in user_location:
            return 1.0
        elif user.willing_to_relocate:
            return 0.8
        else:
            return 0.3
    
    def _calculate_company_preference(self, job: Job, user: User) -> float:
        """Calculate company preference based on user history."""
        # This would be based on user's application history, ratings, etc.
        # For now, return neutral score
        return 0.8
    
    def _calculate_job_recency_score(self, job: Job) -> float:
        """Calculate job recency score."""
        if not job.posted_date:
            return 0.7  # Neutral if no date
        
        days_old = (datetime.utcnow() - job.posted_date).days
        
        if days_old <= 7:
            return 1.0
        elif days_old <= 30:
            return 0.9
        elif days_old <= 90:
            return 0.7
        else:
            return 0.5
    
    def _calculate_confidence_score(self, job: Job, resume: Resume, scores: Dict) -> float:
        """Calculate confidence in the match score."""
        confidence = 100.0
        
        # Reduce confidence for missing data
        if not resume.raw_text:
            confidence -= 20
        if not job.description:
            confidence -= 15
        if not resume.skills:
            confidence -= 10
        if not job.required_skills:
            confidence -= 10
        
        return max(confidence, 50.0)


# Initialize matching engine
matching_engine = EnhancedMatchingEngine()


@router.get("/", response_model=RecommendationsResponse, dependencies=[Depends(api_rate_limit)])
async def get_job_recommendations(
    pagination: PaginationParams = Depends(get_pagination_params),
    resume_id: Optional[int] = Query(None, description="Resume ID to use for matching"),
    min_score: float = Query(60.0, description="Minimum match score"),
    min_salary: Optional[int] = Query(None, description="Minimum salary"),
    max_salary: Optional[int] = Query(None, description="Maximum salary"),
    location: Optional[str] = Query(None, description="Location filter"),
    remote_only: Optional[bool] = Query(False, description="Remote jobs only"),
    experience_level: Optional[str] = Query(None, description="Experience level"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    job_type: Optional[str] = Query(None, description="Job type filter"),
    exclude_applied: bool = Query(True, description="Exclude already applied jobs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized job recommendations."""
    
    # Get user's primary resume if not specified
    if not resume_id:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_primary == True,
            Resume.is_active == True
        ).first()
        
        if not resume:
            # Get most recent resume
            resume = db.query(Resume).filter(
                Resume.user_id == current_user.id,
                Resume.is_active == True
            ).order_by(Resume.created_at.desc()).first()
    else:
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
            Resume.is_active == True
        ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume found. Please upload a resume first."
        )
    
    # Build job query with filters
    job_query = db.query(Job).filter(Job.is_active == True)
    
    # Apply filters
    filters_applied = {}
    
    if min_salary:
        job_query = job_query.filter(Job.salary_min >= min_salary)
        filters_applied['min_salary'] = min_salary
    
    if max_salary:
        job_query = job_query.filter(Job.salary_max <= max_salary)
        filters_applied['max_salary'] = max_salary
    
    if location:
        job_query = job_query.filter(Job.location.ilike(f"%{location}%"))
        filters_applied['location'] = location
    
    if remote_only:
        job_query = job_query.filter(Job.remote_type.in_(['remote', 'hybrid']))
        filters_applied['remote_only'] = remote_only
    
    if experience_level:
        job_query = job_query.filter(Job.experience_level == experience_level)
        filters_applied['experience_level'] = experience_level
    
    if industry:
        job_query = job_query.filter(Job.industry == industry)
        filters_applied['industry'] = industry
    
    if job_type:
        job_query = job_query.filter(Job.job_type == job_type)
        filters_applied['job_type'] = job_type
    
    # Exclude jobs user has already applied to
    if exclude_applied:
        from ...models.application import Application
        applied_job_ids = db.query(Application.job_id).filter(
            Application.user_id == current_user.id
        ).subquery()
        job_query = job_query.filter(~Job.id.in_(applied_job_ids))
        filters_applied['exclude_applied'] = exclude_applied
    
    # Get jobs for matching (limit to reasonable number for performance)
    jobs = job_query.order_by(Job.created_at.desc()).limit(1000).all()
    
    # Calculate match scores for all jobs
    recommendations = []
    
    for job in jobs:
        try:
            match_result = matching_engine.calculate_enhanced_match_score(
                job, resume, current_user
            )
            
            if match_result['overall_score'] >= min_score:
                
                # Convert to match grade
                score = match_result['overall_score']
                if score >= 90:
                    grade = "A+"
                elif score >= 85:
                    grade = "A"
                elif score >= 80:
                    grade = "A-"
                elif score >= 75:
                    grade = "B+"
                elif score >= 70:
                    grade = "B"
                else:
                    grade = "C"
                
                recommendation = JobRecommendation(
                    job_id=job.id,
                    job_title=job.title,
                    company=job.company,
                    location=job.location,
                    salary_range=job.salary_range,
                    match_score=score,
                    match_grade=grade,
                    confidence_score=match_result['confidence'],
                    reasons=match_result['reasons'],
                    missing_skills=match_result['skills_analysis']['missing_skills'],
                    matching_skills=match_result['skills_analysis']['matching_skills'],
                    remote_type=job.remote_type,
                    posted_date=job.posted_date,
                    apply_url=job.apply_url
                )
                
                recommendations.append((recommendation, score))
        
        except Exception as e:
            logger.error(f"Error calculating match for job {job.id}: {e}")
            continue
    
    # Sort by match score
    recommendations.sort(key=lambda x: x[1], reverse=True)
    
    # Apply pagination
    total = len(recommendations)
    start_idx = pagination.offset
    end_idx = start_idx + pagination.limit
    paginated_recommendations = [rec[0] for rec in recommendations[start_idx:end_idx]]
    
    return RecommendationsResponse(
        recommendations=paginated_recommendations,
        total=total,
        page=pagination.page,
        size=pagination.size,
        resume_id=resume.id,
        filters_applied=filters_applied,
        generated_at=datetime.utcnow()
    )


@router.post("/feedback", response_model=dict)
async def provide_recommendation_feedback(
    feedback: RecommendationFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provide feedback on job recommendation."""
    
    # Validate job exists
    job = db.query(Job).filter(Job.id == feedback.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Here you would store the feedback for improving recommendations
    # This could be in a separate feedback table or user preferences
    
    logger.info(f"Recommendation feedback from user {current_user.id}: {feedback.feedback_type} for job {feedback.job_id}")
    
    return {"message": "Feedback recorded successfully"}


@router.get("/insights", response_model=RecommendationInsights)
async def get_recommendation_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get insights about job recommendations and market trends."""
    
    # Get user's primary resume
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_primary == True,
        Resume.is_active == True
    ).first()
    
    if not resume:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True
        ).order_by(Resume.created_at.desc()).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume found"
        )
    
    # Get recent jobs for analysis
    recent_jobs = db.query(Job).filter(
        Job.is_active == True,
        Job.created_at >= datetime.utcnow() - timedelta(days=90)
    ).limit(500).all()
    
    # Analyze top skills in demand
    skill_counts = {}
    for job in recent_jobs:
        job_skills = matching_engine._extract_skills_from_job(job)
        for skill in job_skills:
            skill_counts[skill.lower()] = skill_counts.get(skill.lower(), 0) + 1
    
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_skills_in_demand = [skill[0].title() for skill in top_skills]
    
    # Salary insights
    salaries = [job.salary_min for job in recent_jobs if job.salary_min]
    salary_insights = {}
    if salaries:
        salary_insights = {
            "average": sum(salaries) / len(salaries),
            "median": sorted(salaries)[len(salaries) // 2],
            "min": min(salaries),
            "max": max(salaries)
        }
    
    # Location insights
    location_counts = {}
    for job in recent_jobs:
        if job.location:
            location_counts[job.location] = location_counts.get(job.location, 0) + 1
    
    top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    location_insights = {
        "top_locations": [{"location": loc[0], "count": loc[1]} for loc in top_locations],
        "remote_percentage": len([j for j in recent_jobs if j.remote_type == 'remote']) / len(recent_jobs) * 100 if recent_jobs else 0
    }
    
    # Skill gap analysis
    user_skills = set(skill.lower() for skill in matching_engine._extract_skills_from_resume(resume))
    market_skills = set(skill_counts.keys())
    missing_skills = market_skills - user_skills
    
    skill_gaps = []
    for skill in list(missing_skills)[:5]:  # Top 5 missing skills
        importance = skill_counts.get(skill, 0)
        skill_gaps.append(SkillGapAnalysis(
            skill_name=skill.title(),
            importance_score=min(importance / max(skill_counts.values()) * 100, 100),
            market_demand=importance,
            learning_resources=["Online courses", "Documentation", "Tutorials"],
            estimated_learning_time="2-4 weeks"
        ))
    
    return RecommendationInsights(
        total_matches=len(recent_jobs),
        top_skills_in_demand=top_skills_in_demand,
        salary_insights=salary_insights,
        location_insights=location_insights,
        skill_gaps=skill_gaps,
        market_trends=[
            "Remote work opportunities increasing",
            "AI/ML skills in high demand",
            "Full-stack development popular"
        ]
    )