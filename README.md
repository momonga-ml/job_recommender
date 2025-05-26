# Job Recommender

A Python tool for scraping job descriptions from various job boards and analyzing resumes against job requirements.

## Features

- Scrape job descriptions from multiple job boards:
  - Indeed
  - LinkedIn
  - Glassdoor
- Analyze resumes against job requirements
- Extract key skills from job descriptions
- Generate personalized recommendations for skill development
- Support for both PDF and text resume formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/job_recommender.git
cd job_recommender
```

2. Install the package:
```bash
pip install -e ".[dev]"  # Install with development dependencies for testing
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key and database credentials
```

## Database Setup

This project now uses a PostgreSQL database to store cached job search results and detailed job information. You need to have a PostgreSQL instance running.

1.  **Install PostgreSQL:** If you don't have it installed, download it from [postgresql.org](https://www.postgresql.org/download/).

2.  **Create Database and User:**
    Connect to your PostgreSQL server (e.g., using `psql`) and run the following commands. Replace `your_db_user` and `your_db_password` with your desired credentials.

    ```sql
    CREATE DATABASE job_recommender_db;
    CREATE USER your_db_user WITH PASSWORD 'your_db_password';
    GRANT ALL PRIVILEGES ON DATABASE job_recommender_db TO your_db_user;
    ALTER DATABASE job_recommender_db OWNER TO your_db_user;
    ```

3.  **Configure Environment Variables:**
    Ensure your `.env` file (copied from `example.env`) has the correct database connection details:
    ```env
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=job_recommender_db
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    ```

4.  **Table Creation:**
    The necessary database tables (`cached_searches`, `job_details`, `job_analysis_results`) will be created automatically by the application if they do not already exist when it first connects to the database, thanks to the `create_tables` utility function that uses SQLAlchemy's metadata.

## Usage

### Scraping Job Descriptions

```bash
job-scraper --query "software engineer" --location "New York, NY" --num-jobs 20 --sites indeed linkedin
```

### Analyzing Your Resume

The `job-analyzer` now reads job descriptions directly from the database.

```bash
job-analyzer --resume path/to/your/resume.pdf 
```
You can optionally specify which jobs to analyze using their URLs:
```bash
job-analyzer --resume path/to/your/resume.pdf --job-ids <URL1> --job-ids <URL2>
```
If no `--job-ids` are provided, it will analyze against all job descriptions found in the database.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=job_recommender

# Run only integration tests
pytest -m integration
```

### Project Structure

```
job_recommender/
├── job_recommender/
│   ├── __init__.py
│   ├── job_scraper.py
│   ├── job_analyzer.py
│   ├── cache.py
│   ├── db_schema.py
│   └── db_utils.py
├── tests/
│   ├── __init__.py
│   ├── test_job_scraper.py
│   └── test_job_analyzer.py
├── setup.py
├── requirements.txt
├── example.env
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
