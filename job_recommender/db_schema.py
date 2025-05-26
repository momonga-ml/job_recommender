from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CachedSearches(Base):
    __tablename__ = 'cached_searches'

    search_hash = Column(String, primary_key=True)
    site_name = Column(String)
    query_string = Column(String)
    location_string = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    job_data = Column(JSONB)

class JobDetails(Base):
    __tablename__ = 'job_details'

    job_id = Column(String, primary_key=True)
    site_name = Column(String)
    title = Column(String)
    company = Column(String, nullable=True)
    description = Column(Text)
    url = Column(String, unique=True)
    location = Column(String, nullable=True)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    raw_search_hash = Column(String, ForeignKey('cached_searches.search_hash'), nullable=True)

class JobAnalysisResults(Base):
    __tablename__ = 'job_analysis_results'

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey('job_details.job_id'), nullable=True)
    resume_hash = Column(String, nullable=True)
    analysis_type = Column(String)
    results = Column(JSONB)
    analyzed_date = Column(DateTime, default=datetime.utcnow)
