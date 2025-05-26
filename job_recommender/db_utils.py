import os
from sqlalchemy import create_engine
from job_recommender.db_schema import Base # For create_tables function

def create_db_engine():
    """
    Creates a SQLAlchemy engine using PostgreSQL connection parameters
    retrieved from environment variables.

    Raises:
        ValueError: If any of the required environment variables
                    (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
                    are not set.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine instance.
    """
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    required_vars = {
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
        "DB_HOST": db_host,
        "DB_PORT": db_port,
        "DB_NAME": db_name,
    }

    missing_vars = [var_name for var_name, var_value in required_vars.items() if var_value is None]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(db_url)
    return engine

def create_tables(engine):
    """
    Creates all tables defined in the SQLAlchemy Base metadata.

    Args:
        engine (sqlalchemy.engine.Engine): The SQLAlchemy engine instance
                                           to bind the metadata to.
    """
    Base.metadata.create_all(engine)
