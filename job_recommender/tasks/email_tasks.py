"""Email notification background tasks."""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from sqlalchemy.orm import Session
from celery import Task
from dotenv import load_dotenv

from ..celery_app import celery_app
from ..models.database import SessionLocal
from ..models.user import User
from ..models.job import Job
from ..models.analysis import Analysis

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
FROM_NAME = os.getenv("FROM_NAME", "Job Recommender")


class DatabaseTask(Task):
    """Base task class that provides database session."""
    
    def __call__(self, *args, **kwargs):
        db = SessionLocal()
        try:
            return super().__call__(*args, db=db, **kwargs)
        finally:
            db.close()


class EmailSender:
    """Email sending utility class."""
    
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.username = SMTP_USERNAME
        self.password = SMTP_PASSWORD
        self.from_email = FROM_EMAIL
        self.from_name = FROM_NAME
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send an email."""
        
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured. Email not sent.")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False


email_sender = EmailSender()


@celery_app.task(bind=True, name="job_recommender.tasks.email_tasks.send_welcome_email")
def send_welcome_email(self, user_email: str, user_name: str = None) -> Dict[str, Any]:
    """Send welcome email to new user."""
    
    subject = "Welcome to Job Recommender!"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Welcome to Job Recommender!</h2>
                
                <p>Hi {user_name or 'there'},</p>
                
                <p>Thank you for joining Job Recommender! We're excited to help you find your next great opportunity.</p>
                
                <h3>Getting Started:</h3>
                <ol>
                    <li><strong>Upload your resume</strong> - This helps us understand your skills and experience</li>
                    <li><strong>Complete your profile</strong> - Add your preferences and career goals</li>
                    <li><strong>Get personalized recommendations</strong> - We'll match you with relevant job opportunities</li>
                    <li><strong>Apply with confidence</strong> - Use our analysis tools to optimize your applications</li>
                </ol>
                
                <p>Our AI-powered platform analyzes thousands of job postings to find the best matches for your profile. You'll receive detailed insights about how well you match each position and what skills to highlight.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Pro Tip:</strong> The more complete your profile, the better our recommendations will be!</p>
                </div>
                
                <p>If you have any questions, feel free to reach out to our support team.</p>
                
                <p>Happy job hunting!</p>
                <p>The Job Recommender Team</p>
            </div>
        </body>
    </html>
    """
    
    text_content = f"""
    Welcome to Job Recommender!
    
    Hi {user_name or 'there'},
    
    Thank you for joining Job Recommender! We're excited to help you find your next great opportunity.
    
    Getting Started:
    1. Upload your resume - This helps us understand your skills and experience
    2. Complete your profile - Add your preferences and career goals  
    3. Get personalized recommendations - We'll match you with relevant job opportunities
    4. Apply with confidence - Use our analysis tools to optimize your applications
    
    Our AI-powered platform analyzes thousands of job postings to find the best matches for your profile.
    
    If you have any questions, feel free to reach out to our support team.
    
    Happy job hunting!
    The Job Recommender Team
    """
    
    success = email_sender.send_email(user_email, subject, html_content, text_content)
    
    return {
        "email": user_email,
        "subject": subject,
        "sent": success,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, name="job_recommender.tasks.email_tasks.send_verification_email")
def send_verification_email(self, user_email: str, verification_token: str, user_name: str = None) -> Dict[str, Any]:
    """Send email verification email."""
    
    subject = "Please verify your email address"
    
    # In production, this would be your frontend URL
    verification_url = f"http://localhost:3000/verify-email?token={verification_token}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Verify Your Email Address</h2>
                
                <p>Hi {user_name or 'there'},</p>
                
                <p>Thank you for signing up for Job Recommender! To complete your registration, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background-color: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Email Address</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #7f8c8d;">{verification_url}</p>
                
                <p>This verification link will expire in 7 days.</p>
                
                <p>If you didn't create an account with Job Recommender, you can safely ignore this email.</p>
                
                <p>Best regards,<br>The Job Recommender Team</p>
            </div>
        </body>
    </html>
    """
    
    text_content = f"""
    Verify Your Email Address
    
    Hi {user_name or 'there'},
    
    Thank you for signing up for Job Recommender! To complete your registration, please verify your email address by visiting this link:
    
    {verification_url}
    
    This verification link will expire in 7 days.
    
    If you didn't create an account with Job Recommender, you can safely ignore this email.
    
    Best regards,
    The Job Recommender Team
    """
    
    success = email_sender.send_email(user_email, subject, html_content, text_content)
    
    return {
        "email": user_email,
        "subject": subject,
        "sent": success,
        "verification_token": verification_token,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, name="job_recommender.tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(self, user_email: str, reset_token: str, user_name: str = None) -> Dict[str, Any]:
    """Send password reset email."""
    
    subject = "Password Reset Request"
    
    # In production, this would be your frontend URL
    reset_url = f"http://localhost:3000/reset-password?token={reset_token}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Password Reset Request</h2>
                
                <p>Hi {user_name or 'there'},</p>
                
                <p>We received a request to reset your password for your Job Recommender account. Click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #7f8c8d;">{reset_url}</p>
                
                <p>This password reset link will expire in 24 hours.</p>
                
                <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                
                <p>For security reasons, we recommend using a strong, unique password.</p>
                
                <p>Best regards,<br>The Job Recommender Team</p>
            </div>
        </body>
    </html>
    """
    
    text_content = f"""
    Password Reset Request
    
    Hi {user_name or 'there'},
    
    We received a request to reset your password for your Job Recommender account. Visit this link to reset your password:
    
    {reset_url}
    
    This password reset link will expire in 24 hours.
    
    If you didn't request a password reset, you can safely ignore this email.
    
    Best regards,
    The Job Recommender Team
    """
    
    success = email_sender.send_email(user_email, subject, html_content, text_content)
    
    return {
        "email": user_email,
        "subject": subject,
        "sent": success,
        "reset_token": reset_token,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.email_tasks.send_job_recommendations_email")
def send_job_recommendations_email(self, user_id: int, db: Session = None) -> Dict[str, Any]:
    """Send weekly job recommendations email."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    
    # Get user's recent high-scoring analyses
    recent_analyses = db.query(Analysis).filter(
        Analysis.user_id == user_id,
        Analysis.is_active == True,
        Analysis.overall_match_score >= 70
    ).order_by(Analysis.overall_match_score.desc()).limit(5).all()
    
    if not recent_analyses:
        return {"message": "No recommendations to send"}
    
    subject = "Your Weekly Job Recommendations"
    
    # Build recommendations HTML
    recommendations_html = ""
    for analysis in recent_analyses:
        job = db.query(Job).filter(Job.id == analysis.job_id).first()
        if job:
            recommendations_html += f"""
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0;">
                <h3 style="color: #2c3e50; margin: 0 0 10px 0;">{job.title}</h3>
                <p style="color: #7f8c8d; margin: 0 0 10px 0;"><strong>{job.company}</strong> • {job.location or 'Location not specified'}</p>
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <p style="margin: 0; color: #27ae60;"><strong>Match Score: {analysis.overall_match_score:.0f}%</strong></p>
                </div>
                <p style="margin: 10px 0;">{job.description[:200]}{'...' if len(job.description) > 200 else ''}</p>
                {f'<a href="{job.apply_url}" style="background-color: #3498db; color: white; padding: 8px 15px; text-decoration: none; border-radius: 3px; display: inline-block;">Apply Now</a>' if job.apply_url else ''}
            </div>
            """
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Your Weekly Job Recommendations</h2>
                
                <p>Hi {user.first_name or user.username},</p>
                
                <p>We've found some great job opportunities that match your profile! Here are your top recommendations this week:</p>
                
                {recommendations_html}
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>💡 Tip:</strong> Log in to see detailed analysis for each position and get personalized application advice!</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/recommendations" style="background-color: #27ae60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">View All Recommendations</a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #7f8c8d;">
                    Don't want to receive these emails? You can <a href="#">update your email preferences</a> or <a href="#">unsubscribe</a>.
                </p>
                
                <p>Best regards,<br>The Job Recommender Team</p>
            </div>
        </body>
    </html>
    """
    
    success = email_sender.send_email(user.email, subject, html_content)
    
    return {
        "user_id": user_id,
        "email": user.email,
        "subject": subject,
        "sent": success,
        "recommendations_count": len(recent_analyses),
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, base=DatabaseTask, name="job_recommender.tasks.email_tasks.send_application_reminder")
def send_application_reminder(self, user_id: int, job_id: int, db: Session = None) -> Dict[str, Any]:
    """Send application follow-up reminder."""
    
    user = db.query(User).filter(User.id == user_id).first()
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not user or not job:
        return {"error": "User or job not found"}
    
    subject = f"Follow up on your {job.title} application"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Application Follow-up Reminder</h2>
                
                <p>Hi {user.first_name or user.username},</p>
                
                <p>It's been a while since you applied for the <strong>{job.title}</strong> position at <strong>{job.company}</strong>. Here are some suggested follow-up actions:</p>
                
                <ul>
                    <li>Send a polite follow-up email to the hiring manager</li>
                    <li>Connect with employees at {job.company} on LinkedIn</li>
                    <li>Check if there are any updates on the company's careers page</li>
                    <li>Consider reaching out to recruiters working with {job.company}</li>
                </ul>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>💡 Follow-up Tip:</strong> Mention specific aspects of the role that excite you and reiterate your key qualifications.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/applications" style="background-color: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">View Application Status</a>
                </div>
                
                <p>Keep up the great work in your job search!</p>
                <p>Best regards,<br>The Job Recommender Team</p>
            </div>
        </body>
    </html>
    """
    
    success = email_sender.send_email(user.email, subject, html_content)
    
    return {
        "user_id": user_id,
        "job_id": job_id,
        "email": user.email,
        "subject": subject,
        "sent": success,
        "timestamp": datetime.utcnow().isoformat()
    }