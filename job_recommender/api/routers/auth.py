"""Authentication router."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import logging

from ...models.database import get_db
from ...models.user import User
from ..auth import (
    authenticate_user,
    create_user_tokens,
    get_password_hash,
    refresh_access_token,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_verification_token
)
from ..dependencies import get_current_user, auth_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class UserRegistration(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    token: str


class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    bio: Optional[str]
    current_title: Optional[str]
    years_experience: Optional[int]
    is_active: bool
    is_verified: bool
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    current_title: Optional[str] = None
    years_experience: Optional[int] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    preferred_locations: Optional[str] = None
    work_authorization: Optional[str] = None
    willing_to_relocate: Optional[bool] = None


def send_verification_email(email: str, token: str):
    """Send email verification email (placeholder)."""
    logger.info(f"Sending verification email to {email} with token {token}")
    # TODO: Implement actual email sending


def send_password_reset_email(email: str, token: str):
    """Send password reset email (placeholder)."""
    logger.info(f"Sending password reset email to {email} with token {token}")
    # TODO: Implement actual email sending


@router.post("/register", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def register_user(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        email_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate email verification token and send email
    verification_token = generate_email_verification_token(user)
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    
    logger.info(f"New user registered: {user.email}")
    
    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "verification_required": True
    }


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limit)])
async def login_user(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and return tokens."""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    tokens = create_user_tokens(user)
    
    logger.info(f"User logged in: {user.email}")
    
    return Token(**tokens)


@router.post("/login/oauth2", response_model=Token, dependencies=[Depends(auth_rate_limit)])
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible login endpoint."""
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    tokens = create_user_tokens(user)
    return Token(**tokens)


@router.post("/refresh", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    tokens = refresh_access_token(token_request.refresh_token, db)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return tokens


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    # Update user fields
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User profile updated: {current_user.email}")
    
    return current_user


@router.post("/password-reset", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def request_password_reset(
    password_reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    user = db.query(User).filter(User.email == password_reset_request.email).first()
    
    # Always return success to prevent email enumeration
    if user and user.is_active:
        reset_token = generate_password_reset_token(user)
        background_tasks.add_task(send_password_reset_email, user.email, reset_token)
        logger.info(f"Password reset requested for: {user.email}")
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def confirm_password_reset(
    password_reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token."""
    user = verify_password_reset_token(password_reset.token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update password
    user.hashed_password = get_password_hash(password_reset.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Password reset completed for: {user.email}")
    
    return {"message": "Password reset successful"}


@router.post("/verify-email", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def verify_email(
    verification_request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address."""
    user = verify_email_verification_token(verification_request.token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    # Verify email
    user.email_verified = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Email verified for: {user.email}")
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification", response_model=dict, dependencies=[Depends(auth_rate_limit)])
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Resend email verification."""
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification_token = generate_email_verification_token(current_user)
    background_tasks.add_task(send_verification_email, current_user.email, verification_token)
    
    return {"message": "Verification email sent"}


@router.post("/logout", response_model=dict)
async def logout_user():
    """Logout user (client-side token removal)."""
    return {"message": "Logged out successfully"}