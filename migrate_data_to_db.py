import os
import json
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Assuming job_recommender package is in PYTHONPATH or this script is run in a way that it can be found
# If not, sys.path manipulations might be needed, or run as `python -m migrate_data_to_db`
try:
    from job_recommender.db_utils import create_db_engine
    from job_recommender.db_schema import Base, CachedSearches, JobDetails
except ImportError:
    # Fallback for running directly from root if job_recommender is not directly in PYTHONPATH
    # This is a common scenario for utility scripts.
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__))) # Add current dir to path
    from job_recommender.db_utils import create_db_engine
    from job_recommender.db_schema import Base, CachedSearches, JobDetails


# 1. Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2. Create DB engine and session factory
try:
    engine = create_db_engine()
    Session = sessionmaker(bind=engine)
    # Optional: Create tables if they don't exist.
    # Base.metadata.create_all(engine) # Usually handled by app startup or a dedicated migration tool
except Exception as e:
    logger.error(f"Failed to initialize database engine or session: {e}")
    exit(1)

DEFAULT_CACHE_DIR = ".cache"
DEFAULT_JOB_DESC_DIR = "job_descriptions"

# Regex to extract job_id from filename (e.g., indeed_JOBID_date.txt)
# It captures the part between the first underscore and the second-to-last underscore.
# Assumes site name does not contain underscores.
JOB_ID_FILENAME_REGEX = re.compile(r"^(?:indeed|linkedin|glassdoor)_([^_]+(?:_[^_]+)*?)_\d{8}\.txt$")


def parse_job_text_file(filepath: str) -> Optional[Dict[str, str]]:
    """
    Parses a job description text file into a dictionary.
    Expected format:
    Site: Indeed
    Title: Software Engineer
    Company: Google (Optional)
    URL: https://...
    Scraped Date: 2023-01-01T12:00:00
    Location: New York, NY (Optional, new field)
    Description:
    The job description text...
    ...
    """
    data = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # First pass for key-value pairs
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("Site:"):
                data['Site'] = line.split(":", 1)[1].strip()
            elif line.startswith("Title:"):
                data['Title'] = line.split(":", 1)[1].strip()
            elif line.startswith("Company:"):
                data['Company'] = line.split(":", 1)[1].strip()
            elif line.startswith("URL:"):
                data['URL'] = line.split(":", 1)[1].strip()
            elif line.startswith("Scraped Date:"):
                data['Scraped Date'] = line.split(":", 1)[1].strip()
            elif line.startswith("Location:"): # Optional field
                data['Location'] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                # Join all subsequent lines as description
                data['Description'] = "".join(lines[i+1:]).strip()
                break # Description is the last part

        # Validate critical fields
        required_fields = ['Site', 'Title', 'URL', 'Scraped Date', 'Description']
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"Missing critical field '{field}' or field is empty in {filepath}. Skipping file.")
                return None
        
        # Company is optional, so provide a default if not found
        if 'Company' not in data:
            data['Company'] = None # Or "Unknown Company" if preferred by schema/application logic

        return data

    except Exception as e:
        logger.error(f"Error parsing file {filepath}: {e}")
        return None


def migrate_cache_data(session, cache_dir_path: str):
    logger.info(f"Starting migration of cache data from {cache_dir_path}...")
    if not os.path.exists(cache_dir_path):
        logger.warning(f"Cache directory {cache_dir_path} not found. Skipping cache migration.")
        return

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for filename in os.listdir(cache_dir_path):
        if filename.endswith(".json"):
            filepath = os.path.join(cache_dir_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                required_keys = ['site', 'query', 'location', 'timestamp', 'jobs']
                if not all(key in data for key in required_keys):
                    logger.warning(f"File {filename} is missing one of the required keys: {required_keys}. Skipping.")
                    error_count +=1
                    continue
                
                site_name = data['site']
                query_string = data['query']
                location_string = data['location']
                
                search_hash = hashlib.md5(f"{site_name}:{query_string}:{location_string}".lower().encode()).hexdigest()

                existing_cache = session.query(CachedSearches).filter_by(search_hash=search_hash).first()
                if existing_cache:
                    logger.info(f"Cache entry for hash {search_hash} (File: {filename}) already exists. Skipping.")
                    skipped_count += 1
                    continue

                timestamp_str = data['timestamp']
                try:
                    timestamp_dt = datetime.fromisoformat(timestamp_str)
                    if timestamp_dt.tzinfo:
                        timestamp_dt = timestamp_dt.astimezone(timezone.utc).replace(tzinfo=None)
                except ValueError:
                    logger.error(f"Invalid timestamp format '{timestamp_str}' in {filename}. Skipping.")
                    error_count += 1
                    continue
                
                job_data = data['jobs'] # This is expected to be a JSONB compatible structure (list of dicts)

                new_cache_entry = CachedSearches(
                    search_hash=search_hash,
                    site_name=site_name,
                    query_string=query_string,
                    location_string=location_string,
                    timestamp=timestamp_dt,
                    job_data=job_data
                )
                session.add(new_cache_entry)
                session.commit()
                migrated_count += 1
                logger.info(f"Migrated cache entry from {filename} (Hash: {search_hash})")

            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {filename}: {e}. Skipping.")
                error_count += 1
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Integrity error migrating cache from {filename}: {e}. Skipping.")
                error_count += 1
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error migrating cache from {filename}: {e}. Skipping.")
                error_count += 1
            except Exception as e:
                session.rollback()
                logger.error(f"Unexpected error migrating cache from {filename}: {e}. Skipping.")
                error_count += 1
                
    logger.info(f"Cache data migration summary: {migrated_count} migrated, {skipped_count} skipped, {error_count} errors.")


def migrate_job_description_files(session, job_desc_dir_path: str):
    logger.info(f"Starting migration of job description files from {job_desc_dir_path}...")
    if not os.path.exists(job_desc_dir_path):
        logger.warning(f"Job description directory {job_desc_dir_path} not found. Skipping job description migration.")
        return

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for filename in os.listdir(job_desc_dir_path):
        if filename.endswith(".txt"):
            filepath = os.path.join(job_desc_dir_path, filename)
            
            parsed_data = parse_job_text_file(filepath)
            if not parsed_data:
                error_count += 1
                continue

            job_url = parsed_data.get('URL')
            if not job_url: # Should have been caught by parse_job_text_file, but double check
                logger.error(f"URL missing in parsed data for {filename}. Skipping.")
                error_count += 1
                continue

            existing_job = session.query(JobDetails).filter_by(url=job_url).first()
            if existing_job:
                logger.info(f"Job description for URL {job_url} (File: {filename}) already exists. Skipping.")
                skipped_count += 1
                continue

            # Extract job_id from filename
            match = JOB_ID_FILENAME_REGEX.match(filename)
            if match:
                extracted_job_id = match.group(1)
            else:
                # Fallback: hash the URL to create a job_id if regex fails
                logger.warning(f"Could not extract job_id from filename {filename} using regex. Using hash of URL as job_id.")
                extracted_job_id = hashlib.md5(job_url.encode()).hexdigest()
            
            scraped_date_str = parsed_data['Scraped Date']
            try:
                scraped_dt = datetime.fromisoformat(scraped_date_str)
                if scraped_dt.tzinfo:
                    scraped_dt = scraped_dt.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                logger.error(f"Invalid Scraped Date format '{scraped_date_str}' in {filename}. Skipping.")
                error_count += 1
                continue

            try:
                new_job_detail = JobDetails(
                    job_id=extracted_job_id, # Site-specific ID from filename or hash of URL
                    site_name=parsed_data['Site'],
                    title=parsed_data['Title'],
                    company=parsed_data.get('Company'), # Company is optional in parser
                    description=parsed_data['Description'],
                    url=job_url,
                    location=parsed_data.get('Location'), # Location is optional
                    scraped_date=scraped_dt,
                    raw_search_hash=None # No direct equivalent in old .txt files
                )
                session.add(new_job_detail)
                session.commit()
                migrated_count += 1
                logger.info(f"Migrated job description from {filename} (URL: {job_url})")

            except IntegrityError as e:
                session.rollback()
                logger.error(f"Integrity error migrating job description from {filename}: {e}. Skipping.")
                error_count += 1
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error migrating job description from {filename}: {e}. Skipping.")
                error_count += 1
            except Exception as e:
                session.rollback()
                logger.error(f"Unexpected error migrating job description from {filename}: {e}. Skipping.")
                error_count += 1

    logger.info(f"Job description files migration summary: {migrated_count} migrated, {skipped_count} skipped, {error_count} errors.")


if __name__ == "__main__":
    logger.info("Starting data migration script...")
    
    # Ensure tables are created (useful for first run)
    # In a more complex setup, this might be handled by Alembic or another migration tool.
    # For this script, it's convenient to ensure tables exist.
    try:
        Base.metadata.create_all(engine)
        logger.info("Checked and ensured all tables are created.")
    except Exception as e:
        logger.error(f"Error during table creation check: {e}")
        # Decide if to proceed or exit. For this script, we might want to proceed if tables already exist.

    with Session() as session:
        try:
            migrate_cache_data(session, DEFAULT_CACHE_DIR)
            migrate_job_description_files(session, DEFAULT_JOB_DESC_DIR)
            # session.commit() # Commits are done within the migration functions
            logger.info("Data migration functions called.")
        except Exception as e:
            logger.error(f"An error occurred during the migration process: {e}")
            # session.rollback() # Rollback is handled within migration functions

    logger.info("Data migration script finished.")
