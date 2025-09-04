# API Reference Guide

## 🌐 Base Information

- **Base URL**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)
- **Health Check**: `http://localhost:8000/health`

## 🔐 Authentication

All protected endpoints require JWT token authentication:
```
Authorization: Bearer <your_jwt_token>
```

### Getting Started with Authentication

1. **Register a new user**
2. **Login to get JWT token**  
3. **Use token in Authorization header for protected endpoints**

## 📖 API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Login User
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

#### Get Current User Profile
```http
GET /api/auth/me
Authorization: Bearer <token>
```

**Response**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

### Jobs Endpoints

#### List Jobs
```http
GET /api/jobs/?skip=0&limit=100&location=Seattle&title=engineer
Authorization: Bearer <token>
```

**Query Parameters**:
- `skip` (int): Number of records to skip (pagination)
- `limit` (int): Maximum records to return (max 100)  
- `location` (string): Filter by job location
- `title` (string): Filter by job title
- `company` (string): Filter by company name
- `remote_type` (string): Filter by remote work type

**Response**:
```json
{
  "jobs": [
    {
      "id": 1,
      "title": "Senior Software Engineer",
      "company": "Tech Corp",
      "location": "Seattle, WA",
      "description": "We are looking for...",
      "salary_min": 120000,
      "salary_max": 180000,
      "remote_type": "hybrid",
      "posted_date": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 100
}
```

#### Get Specific Job
```http
GET /api/jobs/1
Authorization: Bearer <token>
```

#### Create Job  
```http
POST /api/jobs/
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Software Engineer",
  "company": "Amazing Tech",
  "description": "Full job description here...",
  "location": "San Francisco, CA",
  "salary_min": 100000,
  "salary_max": 150000,
  "remote_type": "remote",
  "job_type": "full-time"
}
```

#### Trigger Job Scraping
```http
POST /api/jobs/scrape
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "python developer",
  "location": "New York",
  "max_jobs": 50,
  "sites": ["indeed", "linkedin", "glassdoor"]
}
```

### Resumes Endpoints

#### Upload Resume
```http
POST /api/resumes/
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <resume.pdf>
```

**Response**:
```json
{
  "id": 1,
  "filename": "resume_processed.pdf",
  "original_filename": "resume.pdf",
  "file_size": 245760,
  "file_type": "application/pdf",
  "processing_status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List User Resumes
```http
GET /api/resumes/
Authorization: Bearer <token>
```

#### Get Resume Processing Status
```http
GET /api/resumes/1/status
Authorization: Bearer <token>
```

**Response**:
```json
{
  "resume_id": 1,
  "status": "completed",
  "progress": 100,
  "processing_time": 45.2,
  "error_message": null,
  "skills_extracted": 25,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

#### Reprocess Resume
```http
POST /api/resumes/1/reprocess
Authorization: Bearer <token>
```

### Analysis Endpoints

#### Create Job-Resume Analysis
```http
POST /api/analysis/
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": 1,
  "resume_id": 1
}
```

**Response**:
```json
{
  "id": 1,
  "job_id": 1,
  "resume_id": 1,
  "overall_match_score": 85.5,
  "skills_match_score": 90.0,
  "experience_match_score": 80.0,
  "education_match_score": 95.0,
  "matching_skills": ["Python", "React", "PostgreSQL"],
  "missing_skills": ["Kubernetes", "AWS"],
  "recommendations": "Focus on cloud technologies...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List User Analyses
```http
GET /api/analysis/?skip=0&limit=50
Authorization: Bearer <token>
```

#### Get Specific Analysis
```http
GET /api/analysis/1
Authorization: Bearer <token>
```

#### Provide Analysis Feedback
```http
PUT /api/analysis/1/feedback
Authorization: Bearer <token>
Content-Type: application/json

{
  "rating": 4,
  "feedback": "Very helpful analysis, accurate recommendations"
}
```

### Recommendations Endpoints

#### Get Job Recommendations
```http
GET /api/recommendations/?limit=20&min_score=70
Authorization: Bearer <token>
```

**Query Parameters**:
- `limit` (int): Maximum recommendations to return
- `min_score` (float): Minimum compatibility score (0-100)
- `location` (string): Filter by location preference
- `remote_only` (bool): Only remote positions

**Response**:
```json
{
  "recommendations": [
    {
      "job_id": 1,
      "job": {
        "title": "Senior Python Developer",
        "company": "Tech Innovations",
        "location": "Remote"
      },
      "match_score": 92.5,
      "confidence": 88.0,
      "reasons": [
        "Strong Python skills match",
        "Experience level aligns perfectly",
        "Location preference satisfied"
      ],
      "skill_gaps": ["Docker", "Kubernetes"],
      "recommended_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total_recommendations": 45,
  "user_profile_completeness": 85
}
```

#### Provide Recommendation Feedback
```http
POST /api/recommendations/feedback
Authorization: Bearer <token>
Content-Type: application/json

{
  "job_id": 1,
  "feedback_type": "applied",
  "rating": 5,
  "comments": "Perfect match, got an interview!"
}
```

#### Get Recommendation Insights
```http
GET /api/recommendations/insights
Authorization: Bearer <token>
```

**Response**:
```json
{
  "trending_skills": ["Python", "React", "AWS"],
  "salary_insights": {
    "average_for_profile": 125000,
    "range": [95000, 165000],
    "growth_trend": "increasing"
  },
  "location_insights": {
    "top_locations": ["San Francisco", "Seattle", "Remote"],
    "remote_percentage": 65
  },
  "recommendation_accuracy": 87.3,
  "profile_improvement_suggestions": [
    "Add cloud computing skills",
    "Include project management experience"
  ]
}
```

### System Endpoints

#### Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1672531200.0,
  "database": "connected",
  "redis": "connected"
}
```

#### API Statistics
```http
GET /api/stats
```

**Response**:
```json
{
  "total_jobs": 15420,
  "active_jobs": 12350,
  "total_users": 2840,
  "active_users": 2165,
  "total_resumes": 3200,
  "total_analyses": 8750
}
```

## 📝 Request/Response Formats

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created successfully  
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation failed)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

## 🔄 Pagination

Most list endpoints support pagination:

```http
GET /api/jobs/?skip=20&limit=10
```

**Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50, max: 100)

**Response includes**:
```json
{
  "items": [...],
  "total": 500,
  "skip": 20,
  "limit": 10
}
```

## 🚦 Rate Limiting

- **General API**: 100 requests per hour
- **Authentication**: 20 requests per 15 minutes
- **File Upload**: 10 requests per hour
- **Scraping**: 5 requests per hour

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95  
X-RateLimit-Reset: 1672531800
```

## 🔍 Filtering and Search

### Job Search Parameters
```http
GET /api/jobs/?title=engineer&location=Seattle&salary_min=100000&remote_type=remote
```

### Advanced Filtering
```http  
GET /api/jobs/?skills=python,react&experience_level=senior&company_size=startup
```

## 📤 File Uploads

### Supported Resume Formats
- **PDF**: `.pdf` (recommended)
- **Text**: `.txt`  
- **Word**: `.doc`, `.docx`

### Upload Limits  
- **Max File Size**: 5MB
- **Max Files per User**: 10 active resumes

### Upload Example
```bash
curl -X POST "http://localhost:8000/api/resumes/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf"
```

## 🔗 Webhook Support

### Analysis Complete Webhook
```json
POST /your-webhook-url
{
  "event": "analysis_completed",
  "analysis_id": 123,
  "user_id": 456,
  "match_score": 85.5,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 💡 Best Practices

### Authentication
1. **Store JWT securely** (httpOnly cookies recommended)
2. **Implement refresh token rotation**
3. **Handle token expiration gracefully**

### API Usage
1. **Implement exponential backoff** for retries
2. **Cache frequently accessed data**
3. **Use pagination for large datasets**
4. **Handle rate limiting appropriately**

### File Processing
1. **Check processing status** before assuming completion
2. **Implement progress tracking** for user experience
3. **Handle processing failures** gracefully

## 🛠️ SDKs and Libraries

### Python Client Example
```python
import requests

class JobRecommenderClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def get_recommendations(self, limit=20):
        response = requests.get(
            f"{self.base_url}/api/recommendations/",
            headers=self.headers,
            params={"limit": limit}
        )
        return response.json()
    
    def upload_resume(self, file_path):
        with open(file_path, 'rb') as f:
            files = {"file": f}
            response = requests.post(
                f"{self.base_url}/api/resumes/",
                headers=self.headers,
                files=files
            )
        return response.json()
```

### JavaScript Client Example
```javascript
class JobRecommenderClient {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.token = token;
    }
    
    async getRecommendations(limit = 20) {
        const response = await fetch(`${this.baseUrl}/api/recommendations/?limit=${limit}`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        return response.json();
    }
    
    async uploadResume(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${this.baseUrl}/api/resumes/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`
            },
            body: formData
        });
        return response.json();
    }
}
```

## 🚀 Interactive Testing

Visit `http://localhost:8000/docs` for interactive API testing with Swagger UI. You can:

1. **Explore all endpoints** with detailed schemas
2. **Test requests directly** in the browser  
3. **View response examples** and formats
4. **Authenticate and test protected endpoints**
5. **Download OpenAPI specification**

---

For more detailed examples and advanced usage, see the [Developer Guide](DEVELOPER_GUIDE.md).