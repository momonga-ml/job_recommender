"""Skill model for tracking skills and technologies."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship

from .database import Base


class Skill(Base):
    """Skill model for tracking skills and technologies."""
    
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Skill information
    name = Column(String, nullable=False, unique=True, index=True)
    normalized_name = Column(String, nullable=False, index=True)  # lowercase, standardized
    display_name = Column(String, nullable=False)  # Proper formatting for display
    
    # Categorization
    category = Column(String, nullable=True, index=True)  # programming, framework, database, etc.
    subcategory = Column(String, nullable=True)
    skill_type = Column(String, nullable=True)  # technical, soft, language, certification
    
    # Skill details
    description = Column(Text, nullable=True)
    aliases = Column(Text, nullable=True)  # JSON array of alternative names
    related_skills = Column(Text, nullable=True)  # JSON array of related skill IDs
    
    # Market data
    demand_score = Column(Float, nullable=True)  # 0-100 based on job postings
    average_salary_impact = Column(Float, nullable=True)  # Salary premium percentage
    growth_trend = Column(String, nullable=True)  # growing, stable, declining
    
    # Usage statistics
    job_mentions_count = Column(Integer, default=0)
    resume_mentions_count = Column(Integer, default=0)
    last_job_mention = Column(DateTime, nullable=True)
    last_resume_mention = Column(DateTime, nullable=True)
    
    # Skill metadata
    experience_levels = Column(Text, nullable=True)  # JSON array: [beginner, intermediate, advanced, expert]
    certifications_available = Column(Text, nullable=True)  # JSON array of certification names
    learning_resources = Column(Text, nullable=True)  # JSON array of learning links/resources
    
    # Status and quality
    is_verified = Column(Boolean, default=False)  # Manually verified by admin
    is_deprecated = Column(Boolean, default=False)  # Technology is outdated
    confidence_score = Column(Float, default=1.0)  # 0-1 confidence in skill extraction
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_stats = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name}, category={self.category})>"
    
    @property
    def popularity_rank(self) -> str:
        """Get popularity rank based on mentions."""
        total_mentions = self.job_mentions_count + self.resume_mentions_count
        if total_mentions >= 1000:
            return "Very High"
        elif total_mentions >= 500:
            return "High"
        elif total_mentions >= 100:
            return "Medium"
        elif total_mentions >= 10:
            return "Low"
        else:
            return "Very Low"
    
    @property
    def is_trending(self) -> bool:
        """Check if skill is currently trending."""
        return self.growth_trend == "growing" and self.demand_score and self.demand_score > 70
    
    @classmethod
    def normalize_skill_name(cls, name: str) -> str:
        """Normalize skill name for consistent matching."""
        return name.lower().strip().replace("-", "").replace(" ", "").replace(".", "")