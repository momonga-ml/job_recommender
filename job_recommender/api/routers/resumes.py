"""Resumes router for resume management."""

import os
import uuid
from datetime import datetime
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import aiofiles
from PyPDF2 import PdfReader

from ...models.database import get_db
from ...models.resume import Resume
from ...models.user import User
from ..dependencies import get_current_user, api_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
UPLOAD_DIRECTORY = "uploads/resumes"
ALLOWED_FILE_TYPES = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


# Pydantic models
class ResumeBase(BaseModel):
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    objective: Optional[str] = None
    work_experience: Optional[str] = None  # JSON string
    education: Optional[str] = None  # JSON string
    skills: Optional[str] = None  # JSON string
    certifications: Optional[str] = None  # JSON string
    projects: Optional[str] = None  # JSON string
    languages: Optional[str] = None  # JSON string
    total_experience_years: Optional[float] = None
    highest_education: Optional[str] = None
    current_title: Optional[str] = None


class ResumeUpdate(ResumeBase):
    is_primary: Optional[bool] = None


class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    is_processed: bool
    processing_status: str
    processing_error: Optional[str]
    ats_score: Optional[float]
    completeness_score: Optional[float]
    is_active: bool
    is_primary: bool
    created_at: datetime
    updated_at: datetime
    last_analyzed: Optional[datetime]
    file_size_mb: Optional[float]
    is_processing: bool

    class Config:
        from_attributes = True


class ResumeListResponse(BaseModel):
    resumes: List[ResumeResponse]
    total: int


class ResumeProcessingStatus(BaseModel):
    id: int
    processing_status: str
    is_processed: bool
    processing_error: Optional[str]
    ats_score: Optional[float]
    completeness_score: Optional[float]


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    try:
        # This would require python-docx library
        # For now, return placeholder
        return "DOCX text extraction not implemented"
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {e}")
        return ""


def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text from uploaded file based on type."""
    if file_type == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_type in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    elif file_type == ".txt":
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            return ""
    else:
        return ""


def process_resume_content(resume: Resume, db: Session):
    """Process resume content and extract structured data."""
    try:
        resume.processing_status = "processing"
        db.commit()
        
        # Extract raw text
        raw_text = extract_text_from_file(resume.file_path, resume.file_type)
        resume.raw_text = raw_text
        
        # Basic parsing (in real implementation, use NLP/AI)
        parsed_content = parse_resume_content(raw_text)
        resume.parsed_content = json.dumps(parsed_content)
        
        # Extract basic information
        resume.candidate_name = parsed_content.get("name")
        resume.email = parsed_content.get("email")
        resume.phone = parsed_content.get("phone")
        resume.location = parsed_content.get("location")
        resume.summary = parsed_content.get("summary")
        resume.total_experience_years = parsed_content.get("experience_years", 0)
        resume.current_title = parsed_content.get("current_title")
        
        # Convert lists to JSON strings
        if parsed_content.get("work_experience"):
            resume.work_experience = json.dumps(parsed_content["work_experience"])
        if parsed_content.get("education"):
            resume.education = json.dumps(parsed_content["education"])
        if parsed_content.get("skills"):
            resume.skills = json.dumps(parsed_content["skills"])
        
        # Calculate scores
        resume.ats_score = calculate_ats_score(parsed_content)
        resume.completeness_score = calculate_completeness_score(parsed_content)
        
        resume.is_processed = True
        resume.processing_status = "completed"
        resume.last_analyzed = datetime.utcnow()
        
        logger.info(f"Resume {resume.id} processed successfully")
        
    except Exception as e:
        resume.processing_status = "failed"
        resume.processing_error = str(e)
        logger.error(f"Error processing resume {resume.id}: {e}")
    
    finally:
        db.commit()


def parse_resume_content(text: str) -> dict:
    """Parse resume text and extract structured information."""
    # This is a placeholder implementation
    # In a real system, you'd use NLP/AI services like spaCy, OpenAI, etc.
    
    parsed = {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "summary": None,
        "experience_years": 0,
        "current_title": None,
        "work_experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": [],
        "languages": []
    }
    
    # Basic email extraction
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        parsed["email"] = emails[0]
    
    # Basic phone extraction
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    if phones:
        parsed["phone"] = phones[0]
    
    # Extract skills (simple keyword matching)
    skill_keywords = [
        "Python", "JavaScript", "Java", "C++", "SQL", "React", "Node.js",
        "AWS", "Docker", "Kubernetes", "Git", "Machine Learning", "AI"
    ]
    
    found_skills = []
    for skill in skill_keywords:
        if skill.lower() in text.lower():
            found_skills.append(skill)
    
    parsed["skills"] = found_skills
    
    return parsed


def calculate_ats_score(parsed_content: dict) -> float:
    """Calculate ATS compatibility score."""
    score = 0.0
    
    # Check for key sections
    if parsed_content.get("name"):
        score += 15
    if parsed_content.get("email"):
        score += 15
    if parsed_content.get("phone"):
        score += 10
    if parsed_content.get("work_experience"):
        score += 25
    if parsed_content.get("education"):
        score += 15
    if parsed_content.get("skills"):
        score += 20
    
    return min(score, 100.0)


def calculate_completeness_score(parsed_content: dict) -> float:
    """Calculate resume completeness score."""
    total_sections = 8
    filled_sections = 0
    
    sections = [
        "name", "email", "phone", "summary", "work_experience",
        "education", "skills", "location"
    ]
    
    for section in sections:
        if parsed_content.get(section):
            filled_sections += 1
    
    return (filled_sections / total_sections) * 100


@router.get("/", response_model=ResumeListResponse, dependencies=[Depends(api_rate_limit)])
async def list_user_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's resumes."""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).order_by(Resume.created_at.desc()).all()
    
    return ResumeListResponse(
        resumes=resumes,
        total=len(resumes)
    )


@router.get("/{resume_id}", response_model=ResumeResponse, dependencies=[Depends(api_rate_limit)])
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    return resume


@router.post("/", response_model=ResumeResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new resume."""
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file selected"
        )
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not allowed. Allowed types: {ALLOWED_FILE_TYPES}"
        )
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    
    # Save file
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving file"
        )
    
    # Create resume record
    resume = Resume(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file.size,
        file_type=file_extension,
        is_processed=False,
        processing_status="pending"
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    # Process resume in background
    background_tasks.add_task(process_resume_content, resume, db)
    
    logger.info(f"Resume uploaded by user {current_user.id}: {file.filename}")
    
    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    resume_update: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update resume information."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # If setting as primary, unset other primary resumes
    if resume_update.is_primary:
        db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.id != resume_id
        ).update({"is_primary": False})
    
    # Update resume fields
    for field, value in resume_update.dict(exclude_unset=True).items():
        setattr(resume, field, value)
    
    resume.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(resume)
    
    logger.info(f"Resume {resume_id} updated by user {current_user.id}")
    
    return resume


@router.delete("/{resume_id}", response_model=dict)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Soft delete
    resume.is_active = False
    resume.updated_at = datetime.utcnow()
    db.commit()
    
    # Optionally delete file
    try:
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except Exception as e:
        logger.warning(f"Error deleting file {resume.file_path}: {e}")
    
    logger.info(f"Resume {resume_id} deleted by user {current_user.id}")
    
    return {"message": "Resume deleted successfully"}


@router.get("/{resume_id}/status", response_model=ResumeProcessingStatus)
async def get_resume_processing_status(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get resume processing status."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    return ResumeProcessingStatus(
        id=resume.id,
        processing_status=resume.processing_status,
        is_processed=resume.is_processed,
        processing_error=resume.processing_error,
        ats_score=resume.ats_score,
        completeness_score=resume.completeness_score
    )


@router.post("/{resume_id}/reprocess", response_model=dict)
async def reprocess_resume(
    resume_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reprocess a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
        Resume.is_active == True
    ).first()
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Reset processing status
    resume.processing_status = "pending"
    resume.processing_error = None
    resume.is_processed = False
    db.commit()
    
    # Process in background
    background_tasks.add_task(process_resume_content, resume, db)
    
    return {"message": "Resume reprocessing started"}