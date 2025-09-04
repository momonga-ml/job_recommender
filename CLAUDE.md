# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Running Tests
```bash
# Run all tests
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m pytest tests/ -v

# Run specific test files  
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m pytest tests/test_job_analyzer.py -v
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m pytest tests/test_job_scraper.py -v

# Run basic functionality tests
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m pytest test_basic_functionality.py -v

# Run with coverage
python -m pytest --cov=job_recommender --cov-report=term-missing

# Skip slow/integration tests
python -m pytest -m "not slow"
python -m pytest -m "not integration"
```

### Running the Application
```bash
# Job analysis CLI
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m job_recommender.job_analyzer path/to/resume.pdf

# Job scraping CLI  
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m job_recommender.job_scraper --query "software engineer" --location "New York"

# Get CLI help
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m job_recommender.job_analyzer --help
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m job_recommender.job_scraper --help
```

### Install Dependencies
```bash
/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe -m pip install -r requirements.txt
```

## Architecture Overview

This is a full-stack job recommendation system with both CLI tools and a web API/frontend:

### Core Components
- **CLI Tools**: Job scraping and resume analysis command-line interfaces
- **Web API**: FastAPI backend with database models and REST endpoints  
- **Frontend**: React/TypeScript SPA with Redux state management
- **Background Tasks**: Celery for asynchronous job processing
- **Database**: SQLAlchemy ORM with Alembic migrations

### Key Modules
- `job_recommender/job_analyzer.py`: Resume analysis CLI using OpenAI API and NLP
- `job_recommender/job_scraper.py`: Web scraping CLI with Selenium for Indeed/LinkedIn/Glassdoor
- `job_recommender/parallel_scraper.py`: Concurrent scraping coordination
- `job_recommender/api/`: FastAPI web server with authentication and CRUD endpoints
- `job_recommender/models/`: SQLAlchemy database models for users, jobs, resumes, skills
- `job_recommender/tasks/`: Celery background tasks for scraping and analysis
- `frontend/src/`: React application with TypeScript and Redux Toolkit

### Data Flow
1. **Job Scraping**: CLI scrapes job sites → saves to `job_descriptions/` folder
2. **Resume Analysis**: CLI reads resume PDF/text + job descriptions → OpenAI analysis → formatted output
3. **Web Interface**: Users upload resumes → background analysis → results displayed in dashboard

### Testing Architecture
- `tests/test_job_analyzer.py`: Resume analysis unit tests
- `tests/test_job_scraper.py`: Web scraping unit tests with mocking
- `test_basic_functionality.py`: End-to-end integration tests
- Pytest markers for `slow` and `integration` tests

### Configuration
- Environment variables defined in `example.env`
- OpenAI API key required for resume analysis
- Selenium WebDriver auto-managed for scraping
- Rich console output with progress bars and formatting

### Output Formats
The job analyzer supports multiple output formats: console (rich formatted), JSON, plain text, and CSV.

## Important Notes
- Uses Windows Python path: `/c/Users/charl/AppData/Local/Microsoft/WindowsApps/python.exe`
- Requires OpenAI API key in `.env` file for analysis features
- Web scraping uses Selenium with Chrome WebDriver (auto-installed)
- All CLI commands use module execution pattern (`python -m job_recommender.module_name`)
- Database migrations managed through Alembic
- Frontend development server runs on different port from API