"""Resume processing background tasks."""

import logging
from datetime import datetime
from typing import Dict, Any
import json

from sqlalchemy.orm import Session
from celery import Task

from ..celery_app import celery_app
from ..models.database import SessionLocal
from ..models.resume import Resume
from ..models.user import User

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class that provides database session."""
    
    def __call__(self, *args, **kwargs):
        db = SessionLocal()
        try:
            return super().__call__(*args, db=db, **kwargs)
        finally:
            db.close()


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.resume_processing.process_resume")
def process_resume(self, resume_id: int, db: Session = None) -> Dict[str, Any]:
    """Process uploaded resume and extract information."""
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    
    if not resume:
        raise ValueError(f"Resume {resume_id} not found")
    
    try:
        # Update status
        resume.processing_status = "processing"
        db.commit()
        
        self.update_state(
            state="PROGRESS",
            meta={"step": "extracting_text", "resume_id": resume_id}
        )
        
        # Extract text from file
        raw_text = extract_text_from_resume_file(resume)
        resume.raw_text = raw_text
        
        self.update_state(
            state="PROGRESS", 
            meta={"step": "parsing_content", "resume_id": resume_id}
        )
        
        # Parse and structure content
        parsed_content = parse_resume_content(raw_text)
        resume.parsed_content = json.dumps(parsed_content)
        
        # Extract structured information
        resume.candidate_name = parsed_content.get("name")
        resume.email = parsed_content.get("email") 
        resume.phone = parsed_content.get("phone")
        resume.location = parsed_content.get("location")
        resume.summary = parsed_content.get("summary")
        resume.objective = parsed_content.get("objective")
        resume.total_experience_years = parsed_content.get("experience_years", 0)
        resume.current_title = parsed_content.get("current_title")
        resume.highest_education = parsed_content.get("highest_education")
        
        # Convert lists to JSON strings
        if parsed_content.get("work_experience"):
            resume.work_experience = json.dumps(parsed_content["work_experience"])
        if parsed_content.get("education"):
            resume.education = json.dumps(parsed_content["education"])
        if parsed_content.get("skills"):
            resume.skills = json.dumps(parsed_content["skills"])
        if parsed_content.get("certifications"):
            resume.certifications = json.dumps(parsed_content["certifications"])
        if parsed_content.get("projects"):
            resume.projects = json.dumps(parsed_content["projects"])
        if parsed_content.get("languages"):
            resume.languages = json.dumps(parsed_content["languages"])
        
        self.update_state(
            state="PROGRESS",
            meta={"step": "calculating_scores", "resume_id": resume_id}
        )
        
        # Calculate quality scores
        resume.ats_score = calculate_ats_score(parsed_content)
        resume.completeness_score = calculate_completeness_score(parsed_content)
        
        # Mark as processed
        resume.is_processed = True
        resume.processing_status = "completed"
        resume.last_analyzed = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Resume {resume_id} processed successfully")
        
        return {
            "resume_id": resume_id,
            "status": "completed",
            "ats_score": resume.ats_score,
            "completeness_score": resume.completeness_score,
            "skills_found": len(parsed_content.get("skills", [])),
            "experience_years": resume.total_experience_years
        }
        
    except Exception as e:
        # Mark as failed
        resume.processing_status = "failed"
        resume.processing_error = str(e)
        db.commit()
        
        logger.error(f"Error processing resume {resume_id}: {e}")
        raise


def extract_text_from_resume_file(resume: Resume) -> str:
    """Extract text from resume file based on file type."""
    
    if resume.file_type == ".pdf":
        return extract_text_from_pdf(resume.file_path)
    elif resume.file_type in [".docx", ".doc"]:
        return extract_text_from_docx(resume.file_path)
    elif resume.file_type == ".txt":
        return extract_text_from_txt(resume.file_path)
    else:
        raise ValueError(f"Unsupported file type: {resume.file_type}")


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    try:
        from PyPDF2 import PdfReader
        
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
        with open(file_path, 'rb') as f:
            # Basic implementation - in production, use python-docx
            return "DOCX text extraction not fully implemented"
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text file: {e}")
        return ""


def parse_resume_content(text: str) -> Dict[str, Any]:
    """Parse resume text and extract structured information."""
    
    # Initialize parsed content structure
    parsed = {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "summary": None,
        "objective": None,
        "experience_years": 0,
        "current_title": None,
        "highest_education": None,
        "work_experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": [],
        "languages": []
    }
    
    # Extract contact information
    parsed.update(extract_contact_information(text))
    
    # Extract sections
    parsed.update(extract_resume_sections(text))
    
    # Calculate experience years
    parsed["experience_years"] = calculate_total_experience(parsed["work_experience"])
    
    # Extract current title
    if parsed["work_experience"]:
        parsed["current_title"] = parsed["work_experience"][0].get("title")
    
    # Determine highest education
    parsed["highest_education"] = determine_highest_education(parsed["education"])
    
    return parsed


def extract_contact_information(text: str) -> Dict[str, str]:
    """Extract contact information from resume text."""
    import re
    
    contact_info = {}
    
    # Email extraction
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        contact_info["email"] = emails[0]
    
    # Phone extraction
    phone_patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
        r'\+\d{1,3}[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}'
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            contact_info["phone"] = phones[0]
            break
    
    # Name extraction (first line heuristic)
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and not any(x in line.lower() for x in ['email', 'phone', '@', 'http']):
            # Simple name validation
            words = line.split()
            if 2 <= len(words) <= 4 and all(word.isalpha() for word in words):
                contact_info["name"] = line
                break
    
    return contact_info


def extract_resume_sections(text: str) -> Dict[str, Any]:
    """Extract main resume sections."""
    
    sections = {
        "summary": None,
        "objective": None,
        "work_experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": [],
        "languages": []
    }
    
    # Split text into lines for processing
    lines = text.split('\n')
    
    # Extract skills using keyword matching
    sections["skills"] = extract_skills_from_text(text)
    
    # Extract work experience (simplified)
    sections["work_experience"] = extract_work_experience(text)
    
    # Extract education (simplified)
    sections["education"] = extract_education(text)
    
    # Extract summary/objective
    summary_text = extract_summary_section(text)
    if summary_text:
        if "objective" in summary_text.lower():
            sections["objective"] = summary_text
        else:
            sections["summary"] = summary_text
    
    return sections


def extract_skills_from_text(text: str) -> list:
    """Extract skills from resume text."""
    
    # Common technical skills
    skill_keywords = [
        # Programming languages
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "PHP", "Ruby",
        "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "HTML", "CSS",
        
        # Frameworks and libraries
        "React", "Angular", "Vue", "Django", "Flask", "Spring", "Express", "Node.js",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Bootstrap", "jQuery",
        
        # Databases
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "Oracle",
        
        # Cloud and DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "GitLab", "GitHub",
        "Terraform", "Ansible", "CI/CD",
        
        # Other technologies
        "Git", "Linux", "Bash", "API", "REST", "GraphQL", "Microservices", "Machine Learning",
        "Deep Learning", "AI", "Data Science", "Analytics", "Tableau", "Power BI",
        
        # Soft skills
        "Leadership", "Communication", "Problem Solving", "Team Work", "Project Management",
        "Agile", "Scrum", "Time Management"
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    return list(set(found_skills))  # Remove duplicates


def extract_work_experience(text: str) -> list:
    """Extract work experience from resume text."""
    
    # This is a simplified implementation
    # In production, you'd use more sophisticated NLP
    
    experience = []
    
    # Look for common job titles
    job_titles = [
        "Software Engineer", "Data Scientist", "Product Manager", "Developer",
        "Analyst", "Consultant", "Manager", "Director", "VP", "CTO", "CEO",
        "Intern", "Associate", "Senior", "Lead", "Principal"
    ]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check if line contains a job title
        for title in job_titles:
            if title.lower() in line.lower():
                # Try to extract company and dates
                exp_item = {
                    "title": title,
                    "company": "Unknown Company",
                    "start_date": None,
                    "end_date": None,
                    "description": ""
                }
                
                # Look for company name in the same or next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not any(t.lower() in next_line.lower() for t in job_titles):
                        exp_item["company"] = next_line
                
                experience.append(exp_item)
                break
    
    return experience[:5]  # Limit to 5 most recent


def extract_education(text: str) -> list:
    """Extract education from resume text."""
    
    education = []
    
    # Look for degree keywords
    degrees = [
        "Bachelor", "Master", "PhD", "Doctorate", "Associate", "Diploma",
        "B.S.", "B.A.", "M.S.", "M.A.", "MBA", "Ph.D."
    ]
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        
        for degree in degrees:
            if degree.lower() in line.lower():
                edu_item = {
                    "degree": degree,
                    "field": "Unknown Field",
                    "school": "Unknown School",
                    "graduation_year": None
                }
                
                # Try to extract more details
                if "in " in line.lower():
                    parts = line.lower().split("in ")
                    if len(parts) > 1:
                        edu_item["field"] = parts[1].strip().title()
                
                education.append(edu_item)
                break
    
    return education[:3]  # Limit to 3 most relevant


def extract_summary_section(text: str) -> str:
    """Extract summary or objective section."""
    
    lines = text.split('\n')
    summary_started = False
    summary_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Check for summary/objective headers
        if any(keyword in line.lower() for keyword in ['summary', 'objective', 'profile']):
            summary_started = True
            continue
        
        if summary_started:
            if line and not line.isupper():  # Not a section header
                summary_lines.append(line)
            elif line.isupper() or (line and len(line.split()) <= 3):  # Next section
                break
    
    return ' '.join(summary_lines) if summary_lines else None


def calculate_total_experience(work_experience: list) -> float:
    """Calculate total years of experience."""
    
    # Simplified calculation - in production, parse actual dates
    return len(work_experience) * 2.5  # Assume 2.5 years per job on average


def determine_highest_education(education: list) -> str:
    """Determine highest level of education."""
    
    if not education:
        return None
    
    # Education hierarchy
    hierarchy = {
        "PhD": 5, "Doctorate": 5, "Ph.D.": 5,
        "Master": 4, "M.S.": 4, "M.A.": 4, "MBA": 4,
        "Bachelor": 3, "B.S.": 3, "B.A.": 3,
        "Associate": 2,
        "Diploma": 1
    }
    
    highest_level = 0
    highest_degree = None
    
    for edu in education:
        degree = edu.get("degree", "")
        level = hierarchy.get(degree, 0)
        if level > highest_level:
            highest_level = level
            highest_degree = degree
    
    return highest_degree


def calculate_ats_score(parsed_content: Dict[str, Any]) -> float:
    """Calculate ATS (Applicant Tracking System) compatibility score."""
    
    score = 0.0
    
    # Contact information (30 points)
    if parsed_content.get("name"):
        score += 10
    if parsed_content.get("email"):
        score += 10
    if parsed_content.get("phone"):
        score += 10
    
    # Work experience (25 points)
    if parsed_content.get("work_experience"):
        score += 25
    
    # Skills (20 points)
    skills_count = len(parsed_content.get("skills", []))
    score += min(skills_count * 2, 20)
    
    # Education (15 points)
    if parsed_content.get("education"):
        score += 15
    
    # Summary/Objective (10 points)
    if parsed_content.get("summary") or parsed_content.get("objective"):
        score += 10
    
    return min(score, 100.0)


def calculate_completeness_score(parsed_content: Dict[str, Any]) -> float:
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