"""Analysis model for job-resume matching results."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from .database import Base


class Analysis(Base):
    """Analysis model for storing job-resume matching results."""
    
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    
    # Overall matching scores
    overall_match_score = Column(Float, nullable=False, index=True)  # 0-100
    confidence_score = Column(Float, nullable=True)  # 0-100
    
    # Detailed scoring breakdown
    skills_match_score = Column(Float, nullable=True)  # 0-100
    experience_match_score = Column(Float, nullable=True)  # 0-100
    education_match_score = Column(Float, nullable=True)  # 0-100
    location_match_score = Column(Float, nullable=True)  # 0-100
    salary_match_score = Column(Float, nullable=True)  # 0-100
    
    # Skills analysis
    matching_skills = Column(Text, nullable=True)  # JSON array of matching skills
    missing_skills = Column(Text, nullable=True)  # JSON array of missing skills
    additional_skills = Column(Text, nullable=True)  # JSON array of extra skills candidate has
    
    # Experience analysis
    experience_gap_years = Column(Float, nullable=True)  # Years short of requirement
    experience_level_match = Column(String, nullable=True)  # under, match, over
    relevant_experience_years = Column(Float, nullable=True)
    
    # Education analysis
    education_requirement_met = Column(Boolean, default=False)
    education_level_match = Column(String, nullable=True)  # under, match, over
    relevant_education = Column(Text, nullable=True)  # JSON array
    
    # Location and logistics
    location_compatible = Column(Boolean, default=True)
    relocation_required = Column(Boolean, default=False)
    remote_work_compatible = Column(Boolean, default=True)
    visa_sponsorship_needed = Column(Boolean, default=False)
    
    # Salary analysis
    salary_expectation_met = Column(Boolean, nullable=True)
    salary_gap_percentage = Column(Float, nullable=True)  # % difference
    
    # AI-generated insights
    strengths = Column(Text, nullable=True)  # JSON array of strength points
    weaknesses = Column(Text, nullable=True)  # JSON array of areas for improvement
    recommendations = Column(Text, nullable=True)  # JSON array of recommendations
    cover_letter_suggestions = Column(Text, nullable=True)
    
    # Detailed analysis
    detailed_feedback = Column(Text, nullable=True)  # Comprehensive analysis text
    improvement_suggestions = Column(Text, nullable=True)  # JSON array
    
    # Processing information
    analysis_version = Column(String, default="1.0")
    processing_time_seconds = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)  # Which AI model was used
    
    # User interaction
    is_bookmarked = Column(Boolean, default=False)
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    job = relationship("Job", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, job_id={self.job_id}, resume_id={self.resume_id}, score={self.overall_match_score})>"
    
    @property
    def match_grade(self) -> str:
        """Get letter grade for match score."""
        if self.overall_match_score >= 90:
            return "A+"
        elif self.overall_match_score >= 85:
            return "A"
        elif self.overall_match_score >= 80:
            return "A-"
        elif self.overall_match_score >= 75:
            return "B+"
        elif self.overall_match_score >= 70:
            return "B"
        elif self.overall_match_score >= 65:
            return "B-"
        elif self.overall_match_score >= 60:
            return "C+"
        elif self.overall_match_score >= 55:
            return "C"
        elif self.overall_match_score >= 50:
            return "C-"
        else:
            return "D"
    
    @property
    def is_good_match(self) -> bool:
        """Check if this is considered a good match."""
        return self.overall_match_score >= 70