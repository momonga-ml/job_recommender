# Job Recommender - Quick Reference

## 🚀 Quick Start Commands

### Start Development Environment
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 2. Install dependencies
python -m pip install -r requirements.txt
python -m pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary redis celery flower python-jose passlib python-multipart bcrypt aiofiles slowapi "pydantic[email]" email-validator
cd frontend && npm install && cd ..

# 3. Start services (3 terminals)
# Terminal 1: Backend
python -m uvicorn job_recommender.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend  
cd frontend && npm start

# Terminal 3: Test CLI
python -m job_recommender.job_analyzer --help
```

### Access URLs
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📋 CLI Commands

### Job Analyzer
```bash
# Basic analysis
python -m job_recommender.job_analyzer resume.pdf

# With custom job folder and output format
python -m job_recommender.job_analyzer resume.pdf --job-folder ./jobs --format json --output results.json --max-skills 15

# Supported formats: console, json, text, csv
```

### Job Scraper
```bash
# Basic scraping
python -m job_recommender.job_scraper --query "software engineer" --location "Seattle" --num-jobs 10

# Multiple sites and advanced options
python -m job_recommender.job_scraper --query "data scientist" --location "New York" --sites "indeed,linkedin,glassdoor" --num-jobs 20 --max-workers 3 --clear-cache
```

## 🧪 Testing Commands

```bash
# Run all Python tests
python -m pytest tests/ -v

# Run basic functionality test
python test_basic_functionality.py

# Run specific test files
python -m pytest tests/test_job_analyzer.py -v
python -m pytest tests/test_job_scraper.py -v

# Frontend tests
cd frontend && npm test
```

## 🔧 Development Commands

### Database
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

### Build & Deploy
```bash
# Build frontend for production
cd frontend && npm run build

# Run with Docker Compose
docker-compose up -d

# View Docker logs
docker-compose logs -f api
```

## 📡 API Examples

### Authentication
```bash
# Register user
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com", 
    "password": "SecurePass123!"
  }'
```

### Jobs
```bash
# List jobs
curl -X GET "http://localhost:8000/api/jobs/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific job
curl -X GET "http://localhost:8000/api/jobs/1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Trigger job scraping
curl -X POST "http://localhost:8000/api/jobs/scrape" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python developer",
    "location": "San Francisco",
    "max_jobs": 50,
    "sites": ["indeed", "linkedin"]
  }'
```

### Resumes
```bash
# Upload resume
curl -X POST "http://localhost:8000/api/resumes/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf"

# List user resumes
curl -X GET "http://localhost:8000/api/resumes/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get resume processing status
curl -X GET "http://localhost:8000/api/resumes/1/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Analysis
```bash
# Create job-resume analysis
curl -X POST "http://localhost:8000/api/analysis/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "resume_id": 1
  }'

# Get analysis results
curl -X GET "http://localhost:8000/api/analysis/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛠️ Environment Variables

### Required
```env
OPENAI_API_KEY=your-openai-api-key-here
```

### Database Options
```env
# SQLite (default)
DATABASE_URL=sqlite:///./job_recommender.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:pass@localhost:5432/job_recommender
```

### Optional
```env
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-in-production
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

### Common Fixes
```bash
# Unicode issues (Windows)
set PYTHONIOENCODING=utf-8

# Check environment
python -c "import os; print('OpenAI Key:', os.getenv('OPENAI_API_KEY', 'Not set')[:10] + '...')"

# Test database connection
python -c "from job_recommender.models.database import engine; print('Database:', engine)"

# Health check
curl http://localhost:8000/health
```

### Port Issues
```bash
# Check what's running on ports
netstat -an | findstr :3000
netstat -an | findstr :8000

# Kill processes if needed
taskkill /F /PID <process_id>
```

## 📁 Project Structure

```
job_recommender/
├── job_recommender/           # Python package
│   ├── api/                  # FastAPI application
│   ├── models/               # Database models
│   ├── tasks/                # Celery background tasks
│   ├── job_analyzer.py       # Resume analysis CLI
│   ├── job_scraper.py        # Web scraping CLI
│   └── parallel_scraper.py   # Multi-threaded scraping
├── frontend/                 # React TypeScript app
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── pages/            # Page components
│   │   ├── store/            # Redux store
│   │   └── services/         # API services
│   └── public/
├── tests/                    # Python tests
├── docs/                     # Documentation
├── alembic/                  # Database migrations
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Docker services
└── .env                      # Environment variables
```

## 🔗 Useful Links

- **Frontend**: http://localhost:3000
- **API Docs (Swagger)**: http://localhost:8000/docs  
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Stats**: http://localhost:8000/api/stats
- **Flower (Celery Monitor)**: http://localhost:5555 (if running)

## 💡 Pro Tips

1. **Use SQLite for development** - No setup required
2. **Enable Redis for production** - Significant performance improvement
3. **Check API docs first** - Complete interactive documentation at `/docs`
4. **Use environment variables** - Keep secrets in `.env` file
5. **Run tests frequently** - Catch issues early with comprehensive test suite
6. **Monitor logs** - Both frontend and backend provide detailed logging