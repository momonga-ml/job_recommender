# Job Recommender System - Developer Guide

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Development Workflow](#development-workflow)
- [API Documentation](#api-documentation)
- [Frontend Development](#frontend-development)
- [CLI Tools](#cli-tools)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

The Job Recommender System is a comprehensive full-stack application with the following components:

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│  React Frontend │ ←→ │  FastAPI Backend │ ←→ │  SQLite Database  │
│  (Port 3000)    │    │   (Port 8000)    │    │   (job_recommender│
│                 │    │                  │    │        .db)       │
│  • Material-UI  │    │  • 25+ Endpoints │    │  • 6+ Tables     │
│  • Redux State  │    │  • JWT Auth      │    │  • Relations     │
│  • TypeScript   │    │  • OpenAPI Docs  │    │  • Migrations    │
└─────────────────┘    └──────────────────┘    └───────────────────┘
         │                       │                        │
         ↓                       ↓                        │
┌─────────────────┐    ┌──────────────────┐               │
│   Job Scraper   │    │   OpenAI API     │               │
│   CLI Tool      │    │   Integration    │               │
│   (Selenium)    │    │   (GPT-4)        │               │
└─────────────────┘    └──────────────────┘               │
                                │                         │
                       ┌──────────────────┐               │
                       │  Redis Cache     │               │
                       │  (Optional)      │               │
                       │  Background Jobs │               │
                       └──────────────────┘               │
```

### Key Features
- **AI-Powered Resume Analysis**: OpenAI GPT-4 integration for resume parsing and job matching
- **Web Job Scraping**: Automated scraping from Indeed, LinkedIn, Glassdoor
- **Full-Stack Web Application**: React TypeScript frontend with FastAPI Python backend
- **Real-time Matching**: Skills extraction, TF-IDF analysis, and compatibility scoring
- **Comprehensive API**: 25+ REST endpoints with automatic OpenAPI documentation
- **Background Processing**: Celery integration for async tasks

## Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 16+
- OpenAI API key
- Chrome browser (for web scraping)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd job_recommender
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Required: OPENAI_API_KEY
# Optional: Redis, PostgreSQL (defaults to SQLite)
```

### 3. Install Dependencies
```bash
# Python backend dependencies
python -m pip install -r requirements.txt
python -m pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary redis celery flower python-jose passlib python-multipart bcrypt aiofiles slowapi "pydantic[email]" email-validator

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 4. Run the Application
```bash
# Terminal 1: Start Backend API
python -m uvicorn job_recommender.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Frontend  
cd frontend
npm start

# Terminal 3: Test CLI Tools
python -m job_recommender.job_analyzer --help
```

### 5. Access Applications
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## Environment Setup

### Required Environment Variables

```env
# Database Configuration (SQLite default)
DATABASE_URL=sqlite:///./job_recommender.db

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT Authentication
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI Configuration (Required for AI features)
OPENAI_API_KEY=your-openai-api-key-here

# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# File Upload Settings
MAX_FILE_SIZE=5242880
UPLOAD_DIRECTORY=uploads/resumes

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### Database Options

#### SQLite (Default - No Setup Required)
```env
DATABASE_URL=sqlite:///./job_recommender.db
```

#### PostgreSQL (Production Recommended)
```bash
# Install and start PostgreSQL
# Create database: job_recommender

DATABASE_URL=postgresql://username:password@localhost:5432/job_recommender
```

#### Redis (Optional - Improves Performance)
```bash
# Install and start Redis
# Application gracefully degrades without Redis

REDIS_URL=redis://localhost:6379/0
```

## Development Workflow

### Backend Development

#### 1. Database Migrations
```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

#### 2. Start Development Server
```bash
# With auto-reload
python -m uvicorn job_recommender.api.main:app --host 0.0.0.0 --port 8000 --reload

# Alternative: Use development script
python start_dev.py
```

#### 3. API Testing
```bash
# View API documentation
open http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/health

# Test root endpoint
curl http://localhost:8000/
```

### Frontend Development

#### 1. Start Development Server
```bash
cd frontend
npm start
```

#### 2. Build for Production
```bash
cd frontend
npm run build
```

#### 3. Run Tests
```bash
cd frontend
npm test
```

### CLI Tools Development

#### Job Analyzer
```bash
# Basic usage
python -m job_recommender.job_analyzer resume.pdf

# With options
python -m job_recommender.job_analyzer resume.pdf --format json --max-skills 15 --output results.json

# Help
python -m job_recommender.job_analyzer --help
```

#### Job Scraper
```bash
# Basic scraping
python -m job_recommender.job_scraper --query "software engineer" --location "Seattle" --num-jobs 10

# Multiple sites
python -m job_recommender.job_scraper --query "data scientist" --location "New York" --sites "indeed,linkedin" --num-jobs 20

# Help
python -m job_recommender.job_scraper --help
```

## API Documentation

### Authentication Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh JWT token
- `GET /api/auth/me` - Get current user profile
- `PUT /api/auth/me` - Update user profile

### Jobs Endpoints
- `GET /api/jobs/` - List jobs with filtering
- `POST /api/jobs/` - Create new job
- `GET /api/jobs/{job_id}` - Get specific job
- `PUT /api/jobs/{job_id}` - Update job
- `DELETE /api/jobs/{job_id}` - Delete job
- `POST /api/jobs/scrape` - Trigger job scraping

### Resumes Endpoints
- `GET /api/resumes/` - List user resumes
- `POST /api/resumes/` - Upload resume
- `GET /api/resumes/{resume_id}` - Get resume details
- `PUT /api/resumes/{resume_id}` - Update resume
- `DELETE /api/resumes/{resume_id}` - Delete resume
- `GET /api/resumes/{resume_id}/status` - Check processing status

### Analysis Endpoints
- `POST /api/analysis/` - Create job-resume analysis
- `GET /api/analysis/` - List user analyses
- `GET /api/analysis/{analysis_id}` - Get specific analysis
- `DELETE /api/analysis/{analysis_id}` - Delete analysis

### Recommendations Endpoints
- `GET /api/recommendations/` - Get personalized job recommendations
- `POST /api/recommendations/feedback` - Provide feedback on recommendations
- `GET /api/recommendations/insights` - Get recommendation insights

### System Endpoints
- `GET /` - API root information
- `GET /health` - Health check
- `GET /api/stats` - API statistics

## Frontend Development

### Project Structure
```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── navigation/     # Navigation components
│   │   └── auth/           # Authentication components
│   ├── pages/              # Page components
│   │   ├── Landing.tsx     # Landing page
│   │   ├── Login.tsx       # Login page
│   │   ├── Register.tsx    # Registration page
│   │   ├── Dashboard.tsx   # User dashboard
│   │   ├── Jobs.tsx        # Jobs listing
│   │   └── Resumes.tsx     # Resume management
│   ├── store/              # Redux store
│   │   └── slices/         # Redux slices
│   ├── services/           # API service functions
│   └── types/              # TypeScript type definitions
├── public/                 # Static assets
└── package.json           # Dependencies and scripts
```

### Key Technologies
- **React 19** - UI library
- **TypeScript** - Type safety
- **Material-UI** - Component library
- **Redux Toolkit** - State management
- **React Router** - Navigation
- **Axios** - HTTP client

### Adding New Features
1. Create components in appropriate directories
2. Add Redux slices for state management
3. Create API service functions
4. Update routing in App.tsx
5. Add TypeScript types

## CLI Tools

### Job Analyzer Features
- **Resume Parsing**: Supports PDF and TXT formats
- **Skills Extraction**: TF-IDF based skill identification
- **Job Analysis**: Analyzes job descriptions for requirements
- **AI Matching**: OpenAI-powered compatibility scoring
- **Multiple Outputs**: Console, JSON, CSV, plain text formats

### Job Scraper Features
- **Multi-Platform**: Indeed, LinkedIn, Glassdoor support
- **Parallel Processing**: Concurrent scraping for speed
- **Caching**: Redis-based caching with configurable TTL
- **Rate Limiting**: Respectful scraping with delays
- **Data Quality**: Automatic data validation and cleaning

## Testing

### Running Tests

#### Python Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific test files
python -m pytest tests/test_job_analyzer.py -v
python -m pytest tests/test_job_scraper.py -v

# Basic functionality test
python test_basic_functionality.py

# With coverage
python -m pytest --cov=job_recommender --cov-report=term-missing
```

#### Frontend Tests
```bash
cd frontend
npm test
```

### Test Structure
- `tests/test_job_analyzer.py` - Resume analysis tests
- `tests/test_job_scraper.py` - Web scraping tests  
- `test_basic_functionality.py` - Integration tests
- `frontend/src/**/*.test.tsx` - React component tests

## Deployment

### Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Deployment

#### Backend
```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment
export ENVIRONMENT=production

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker job_recommender.api.main:app --bind 0.0.0.0:8000
```

#### Frontend
```bash
cd frontend
npm run build

# Serve with nginx or static file server
```

#### Background Workers (Optional)
```bash
# Start Celery worker
celery -A job_recommender.celery_app worker --loglevel=info

# Start Celery beat (scheduler)  
celery -A job_recommender.celery_app beat --loglevel=info

# Monitor with Flower
celery -A job_recommender.celery_app flower --port=5555
```

## Troubleshooting

### Common Issues

#### 1. Unicode Encoding Issues (Windows)
```bash
# Set environment variable
set PYTHONIOENCODING=utf-8

# Or use in command
PYTHONIOENCODING=utf-8 python -m job_recommender.job_analyzer resume.pdf
```

#### 2. OpenAI API Errors
- Verify API key in .env file
- Check OpenAI account balance and rate limits
- Ensure model name is correct (gpt-4-turbo-preview)

#### 3. Database Connection Issues
- SQLite: Check file permissions and path
- PostgreSQL: Verify connection string and database exists
- Check DATABASE_URL format in .env

#### 4. Redis Connection Failures
- Application works without Redis (graceful degradation)
- Install and start Redis: `redis-server`
- Check REDIS_URL in .env

#### 5. Selenium WebDriver Issues
- Chrome browser required for scraping
- WebDriver auto-downloads but may need manual installation
- Check firewall settings for Chrome driver

### Debug Commands
```bash
# Check environment
python -c "import os; print(os.getenv('OPENAI_API_KEY', 'Not set'))"

# Test database connection
python -c "from job_recommender.models.database import engine; print(engine)"

# Test imports
python -c "from job_recommender import JobCache; print('Imports successful')"

# Check API health
curl http://localhost:8000/health
```

### Performance Optimization
- Enable Redis for caching
- Use PostgreSQL for production
- Configure Celery for background tasks
- Enable frontend build optimizations
- Use CDN for static assets

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Run tests: `python -m pytest tests/`
4. Commit changes: `git commit -am 'Add new feature'`
5. Push to branch: `git push origin feature/new-feature`
6. Create Pull Request

### Code Style
- Python: Follow PEP 8, use Black for formatting
- TypeScript: Follow project ESLint configuration
- Documentation: Update README and docs/ for new features

---

## Support

For issues and questions:
1. Check this documentation
2. Review GitHub issues
3. Check API documentation at `/docs`
4. Run diagnostic commands above

**Happy coding! 🚀**