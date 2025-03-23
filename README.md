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
# Edit .env and add your OpenAI API key
```

## Usage

### Scraping Job Descriptions

```bash
job-scraper --query "software engineer" --location "New York, NY" --num-jobs 20 --sites indeed linkedin
```

### Analyzing Your Resume

```bash
job-analyzer --job-folder job_descriptions --resume path/to/your/resume.pdf
```

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
│   └── job_analyzer.py
├── tests/
│   ├── __init__.py
│   ├── test_job_scraper.py
│   └── test_job_analyzer.py
├── setup.py
├── requirements.txt
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
