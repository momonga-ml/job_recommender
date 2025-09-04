"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('email', sa.String(), nullable=False, index=True, unique=True),
        sa.Column('username', sa.String(), nullable=False, index=True, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('current_title', sa.String(), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('desired_salary_min', sa.Integer(), nullable=True),
        sa.Column('desired_salary_max', sa.Integer(), nullable=True),
        sa.Column('preferred_locations', sa.Text(), nullable=True),
        sa.Column('work_authorization', sa.String(), nullable=True),
        sa.Column('willing_to_relocate', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(), nullable=False, index=True),
        sa.Column('company', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('location', sa.String(), nullable=True, index=True),
        sa.Column('remote_type', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True, default='US'),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('salary_currency', sa.String(), default='USD'),
        sa.Column('salary_period', sa.String(), default='yearly'),
        sa.Column('job_type', sa.String(), nullable=True),
        sa.Column('experience_level', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('department', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_platform', sa.String(), nullable=True),
        sa.Column('external_job_id', sa.String(), nullable=True),
        sa.Column('apply_url', sa.String(), nullable=True),
        sa.Column('company_website', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_remote_friendly', sa.Boolean(), default=False),
        sa.Column('requires_visa_sponsorship', sa.Boolean(), default=False),
        sa.Column('data_completeness_score', sa.Float(), default=0.0),
        sa.Column('last_scraped', sa.DateTime(), default=sa.func.now()),
        sa.Column('required_skills', sa.Text(), nullable=True),
        sa.Column('preferred_skills', sa.Text(), nullable=True),
        sa.Column('technologies', sa.Text(), nullable=True),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('application_deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
    )

    # Create resumes table
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_content', sa.Text(), nullable=True),
        sa.Column('candidate_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('work_experience', sa.Text(), nullable=True),
        sa.Column('education', sa.Text(), nullable=True),
        sa.Column('skills', sa.Text(), nullable=True),
        sa.Column('certifications', sa.Text(), nullable=True),
        sa.Column('projects', sa.Text(), nullable=True),
        sa.Column('languages', sa.Text(), nullable=True),
        sa.Column('total_experience_years', sa.Float(), nullable=True),
        sa.Column('highest_education', sa.String(), nullable=True),
        sa.Column('current_title', sa.String(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), default=False),
        sa.Column('processing_status', sa.String(), default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('ats_score', sa.Float(), nullable=True),
        sa.Column('completeness_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
    )

    # Create skills table
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('normalized_name', sa.String(), nullable=False, index=True),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True, index=True),
        sa.Column('subcategory', sa.String(), nullable=True),
        sa.Column('skill_type', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('aliases', sa.Text(), nullable=True),
        sa.Column('related_skills', sa.Text(), nullable=True),
        sa.Column('demand_score', sa.Float(), nullable=True),
        sa.Column('average_salary_impact', sa.Float(), nullable=True),
        sa.Column('growth_trend', sa.String(), nullable=True),
        sa.Column('job_mentions_count', sa.Integer(), default=0),
        sa.Column('resume_mentions_count', sa.Integer(), default=0),
        sa.Column('last_job_mention', sa.DateTime(), nullable=True),
        sa.Column('last_resume_mention', sa.DateTime(), nullable=True),
        sa.Column('experience_levels', sa.Text(), nullable=True),
        sa.Column('certifications_available', sa.Text(), nullable=True),
        sa.Column('learning_resources', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('is_deprecated', sa.Boolean(), default=False),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_updated_stats', sa.DateTime(), nullable=True),
    )

    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id'), nullable=False),
        sa.Column('overall_match_score', sa.Float(), nullable=False, index=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('skills_match_score', sa.Float(), nullable=True),
        sa.Column('experience_match_score', sa.Float(), nullable=True),
        sa.Column('education_match_score', sa.Float(), nullable=True),
        sa.Column('location_match_score', sa.Float(), nullable=True),
        sa.Column('salary_match_score', sa.Float(), nullable=True),
        sa.Column('matching_skills', sa.Text(), nullable=True),
        sa.Column('missing_skills', sa.Text(), nullable=True),
        sa.Column('additional_skills', sa.Text(), nullable=True),
        sa.Column('experience_gap_years', sa.Float(), nullable=True),
        sa.Column('experience_level_match', sa.String(), nullable=True),
        sa.Column('relevant_experience_years', sa.Float(), nullable=True),
        sa.Column('education_requirement_met', sa.Boolean(), default=False),
        sa.Column('education_level_match', sa.String(), nullable=True),
        sa.Column('relevant_education', sa.Text(), nullable=True),
        sa.Column('location_compatible', sa.Boolean(), default=True),
        sa.Column('relocation_required', sa.Boolean(), default=False),
        sa.Column('remote_work_compatible', sa.Boolean(), default=True),
        sa.Column('visa_sponsorship_needed', sa.Boolean(), default=False),
        sa.Column('salary_expectation_met', sa.Boolean(), nullable=True),
        sa.Column('salary_gap_percentage', sa.Float(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('weaknesses', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('cover_letter_suggestions', sa.Text(), nullable=True),
        sa.Column('detailed_feedback', sa.Text(), nullable=True),
        sa.Column('improvement_suggestions', sa.Text(), nullable=True),
        sa.Column('analysis_version', sa.String(), default='1.0'),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('is_bookmarked', sa.Boolean(), default=False),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
    )

    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id'), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='interested', index=True),
        sa.Column('application_method', sa.String(), nullable=True),
        sa.Column('application_url', sa.String(), nullable=True),
        sa.Column('external_application_id', sa.String(), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('custom_resume_version', sa.Text(), nullable=True),
        sa.Column('additional_documents', sa.Text(), nullable=True),
        sa.Column('contact_person', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('referral_person', sa.String(), nullable=True),
        sa.Column('referral_notes', sa.Text(), nullable=True),
        sa.Column('applied_date', sa.DateTime(), nullable=True),
        sa.Column('response_deadline', sa.DateTime(), nullable=True),
        sa.Column('first_response_date', sa.DateTime(), nullable=True),
        sa.Column('interview_scheduled', sa.Boolean(), default=False),
        sa.Column('interview_dates', sa.Text(), nullable=True),
        sa.Column('interview_types', sa.Text(), nullable=True),
        sa.Column('interview_feedback', sa.Text(), nullable=True),
        sa.Column('offer_received', sa.Boolean(), default=False),
        sa.Column('offer_amount', sa.Integer(), nullable=True),
        sa.Column('offer_currency', sa.String(), default='USD'),
        sa.Column('offer_details', sa.Text(), nullable=True),
        sa.Column('offer_deadline', sa.DateTime(), nullable=True),
        sa.Column('rejection_date', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(), nullable=True),
        sa.Column('rejection_feedback', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(), default='medium'),
        sa.Column('follow_up_date', sa.DateTime(), nullable=True),
        sa.Column('last_contact_date', sa.DateTime(), nullable=True),
        sa.Column('match_analysis_id', sa.Integer(), sa.ForeignKey('analyses.id'), nullable=True),
        sa.Column('application_strength_score', sa.Float(), nullable=True),
        sa.Column('success_probability', sa.Float(), nullable=True),
        sa.Column('auto_applied', sa.Boolean(), default=False),
        sa.Column('auto_follow_up', sa.Boolean(), default=False),
        sa.Column('email_notifications', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_status_change', sa.DateTime(), default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_analyses_user_job', 'analyses', ['user_id', 'job_id'])
    op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])
    op.create_index('ix_applications_user_id', 'applications', ['user_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_user_id', table_name='applications')
    op.drop_index('ix_resumes_user_id', table_name='resumes')
    op.drop_index('ix_analyses_user_job', table_name='analyses')
    
    # Drop tables in reverse order
    op.drop_table('applications')
    op.drop_table('analyses')
    op.drop_table('skills')
    op.drop_table('resumes')
    op.drop_table('jobs')
    op.drop_table('users')