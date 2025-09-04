"""Job model for scraped job data."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Job(Base):
    """Job model for storing scraped job postings."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic job information
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    
    # Location information
    location = Column(String, nullable=True, index=True)
    remote_type = Column(String, nullable=True)  # remote, hybrid, on-site
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, default="US")
    
    # Salary information
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String, default="USD")
    salary_period = Column(String, default="yearly")  # yearly, hourly
    
    # Job details
    job_type = Column(String, nullable=True)  # full-time, part-time, contract
    experience_level = Column(String, nullable=True)  # entry, mid, senior
    industry = Column(String, nullable=True)
    department = Column(String, nullable=True)
    
    # External source information
    source_url = Column(String, nullable=True)
    source_platform = Column(String, nullable=True)  # linkedin, indeed, etc
    external_job_id = Column(String, nullable=True)
    
    # Application information
    apply_url = Column(String, nullable=True)
    company_website = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    is_remote_friendly = Column(Boolean, default=False)
    requires_visa_sponsorship = Column(Boolean, default=False)
    
    # Scraped data quality
    data_completeness_score = Column(Float, default=0.0)  # 0-1 score
    last_scraped = Column(DateTime, default=datetime.utcnow)
    
    # Skills and technologies (as JSON text for now)
    required_skills = Column(Text, nullable=True)  # JSON string
    preferred_skills = Column(Text, nullable=True)  # JSON string
    technologies = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    posted_date = Column(DateTime, nullable=True)
    application_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, company={self.company})>"
    
    @property
    def salary_range(self) -> Optional[str]:
        """Get formatted salary range."""
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,} - ${self.salary_max:,}"
        elif self.salary_min:
            return f"${self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to ${self.salary_max:,}"
        else:
            return None
    
    @property
    def is_expired(self) -> bool:
        """Check if job posting has expired."""
        if self.application_deadline:
            return datetime.utcnow() > self.application_deadline
        return False