"""Resume model for uploaded resumes."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from .database import Base


class Resume(Base):
    """Resume model for storing uploaded resumes and extracted data."""
    
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File information
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)  # pdf, docx, txt
    
    # Resume content
    raw_text = Column(Text, nullable=True)
    parsed_content = Column(Text, nullable=True)  # JSON string with structured data
    
    # Extracted information
    candidate_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    # Professional summary
    summary = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    
    # Experience and education (JSON strings)
    work_experience = Column(Text, nullable=True)  # JSON array
    education = Column(Text, nullable=True)  # JSON array
    skills = Column(Text, nullable=True)  # JSON array
    certifications = Column(Text, nullable=True)  # JSON array
    projects = Column(Text, nullable=True)  # JSON array
    languages = Column(Text, nullable=True)  # JSON array
    
    # Derived fields
    total_experience_years = Column(Float, nullable=True)
    highest_education = Column(String, nullable=True)
    current_title = Column(String, nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    
    # Analysis metrics
    ats_score = Column(Float, nullable=True)  # ATS compatibility score 0-100
    completeness_score = Column(Float, nullable=True)  # Resume completeness 0-100
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary resume for the user
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    analyses = relationship("Analysis", back_populates="resume", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Resume(id={self.id}, filename={self.filename}, user_id={self.user_id})>"
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def is_processing(self) -> bool:
        """Check if resume is currently being processed."""
        return self.processing_status in ["pending", "processing"]