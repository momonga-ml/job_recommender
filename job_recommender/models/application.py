"""Application model for job application tracking."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from .database import Base


class Application(Base):
    """Application model for tracking job applications."""
    
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)  # Which resume was used
    
    # Application details
    status = Column(String, nullable=False, default="interested", index=True)
    # Status options: interested, applied, screening, interviewing, offer, rejected, withdrawn, hired
    
    application_method = Column(String, nullable=True)  # direct, linkedin, indeed, referral, etc.
    application_url = Column(String, nullable=True)
    external_application_id = Column(String, nullable=True)
    
    # Application content
    cover_letter = Column(Text, nullable=True)
    custom_resume_version = Column(Text, nullable=True)  # JSON of customizations made
    additional_documents = Column(Text, nullable=True)  # JSON array of document paths
    
    # Contact and referral information
    contact_person = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    referral_person = Column(String, nullable=True)
    referral_notes = Column(Text, nullable=True)
    
    # Application timeline
    applied_date = Column(DateTime, nullable=True)
    response_deadline = Column(DateTime, nullable=True)
    first_response_date = Column(DateTime, nullable=True)
    
    # Interview tracking
    interview_scheduled = Column(Boolean, default=False)
    interview_dates = Column(Text, nullable=True)  # JSON array of interview datetime strings
    interview_types = Column(Text, nullable=True)  # JSON array: phone, video, onsite, technical
    interview_feedback = Column(Text, nullable=True)
    
    # Offer details
    offer_received = Column(Boolean, default=False)
    offer_amount = Column(Integer, nullable=True)
    offer_currency = Column(String, default="USD")
    offer_details = Column(Text, nullable=True)  # JSON of offer breakdown
    offer_deadline = Column(DateTime, nullable=True)
    
    # Rejection information
    rejection_date = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    rejection_feedback = Column(Text, nullable=True)
    
    # User notes and tracking
    notes = Column(Text, nullable=True)
    priority = Column(String, default="medium")  # high, medium, low
    follow_up_date = Column(DateTime, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    
    # Analysis and insights
    match_analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    application_strength_score = Column(Float, nullable=True)  # 0-100
    success_probability = Column(Float, nullable=True)  # 0-100 predicted success rate
    
    # Automation flags
    auto_applied = Column(Boolean, default=False)
    auto_follow_up = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_status_change = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    resume = relationship("Resume")
    
    def __repr__(self):
        return f"<Application(id={self.id}, job_id={self.job_id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def days_since_applied(self) -> Optional[int]:
        """Get number of days since application was submitted."""
        if self.applied_date:
            return (datetime.utcnow() - self.applied_date).days
        return None
    
    @property
    def is_pending_response(self) -> bool:
        """Check if application is waiting for response."""
        return self.status in ["applied", "screening"] and not self.first_response_date
    
    @property
    def days_without_response(self) -> Optional[int]:
        """Get days since application without response."""
        if self.applied_date and not self.first_response_date:
            return (datetime.utcnow() - self.applied_date).days
        return None
    
    @property
    def is_overdue_follow_up(self) -> bool:
        """Check if follow-up is overdue."""
        if self.follow_up_date:
            return datetime.utcnow() > self.follow_up_date
        return False
    
    @property
    def status_color(self) -> str:
        """Get color code for status display."""
        status_colors = {
            "interested": "blue",
            "applied": "yellow", 
            "screening": "orange",
            "interviewing": "purple",
            "offer": "green",
            "hired": "dark_green",
            "rejected": "red",
            "withdrawn": "gray"
        }
        return status_colors.get(self.status, "gray")