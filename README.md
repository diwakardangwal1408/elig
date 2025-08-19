# Dental Insurance Eligibility Automation System

An AI-powered system for automating dental insurance eligibility updates using agentic AI to parse semi-structured data and persist changes via APIs.

## 🎯 Overview

This system automates the workflow of processing dental insurance eligibility updates that EDI analysts typically receive through emails, Excel files, and other data formats. It uses Large Language Models (LLMs) to parse semi-structured data, validates the information, and automatically updates insurance systems via APIs.

## 🏗️ Architecture

### Core Components

1. **Data Parsing Agent** (`dental_eligibility_agent.py`)
   - LLM-powered parsing of emails and Excel files
   - Data validation and enrichment
   - Structured output generation

2. **API Service** (`api_service.py`)
   - FastAPI backend with RESTful endpoints
   - PostgreSQL database integration
   - Celery for background processing
   - External insurance API integration

3. **Workflow Orchestrator** (`workflow_orchestrator.py`)
   - End-to-end workflow management
   - Job status tracking
   - Email notifications
   - Error handling and retries

4. **Streamlit UI** (`streamlit_ui.py`)
   - User-friendly interface for EDI analysts
   - Data upload and review capabilities
   - Real-time monitoring and analytics
   - Batch processing management

### Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **AI/ML**: LangChain, OpenAI API, Pydantic
- **Task Queue**: Celery, Redis
- **Frontend**: Streamlit, Plotly
- **Deployment**: Docker, Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Insurance provider API credentials

### Installation

1. **Clone and setup the project:**
```bash
git clone <repository-url>
cd dental-eligibility-system
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Start the services:**
```bash
docker-compose up -d
```

4. **Access the applications:**
python -m streamlit run streamlit_ui.py --server.port 8501
- **Streamlit UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📋 Usage

### 1. Configure API Keys

In the Streamlit UI sidebar, enter your OpenAI API key to enable LLM parsing capabilities.

### 2. Upload Data

Choose from three input methods:

**Email Content:**
- Paste email content containing eligibility updates
- AI agent will parse and extract structured data

**Excel Upload:**
- Upload Excel files with eligibility information
- Automatic parsing and validation

**Manual Entry:**
- Direct form input for individual records
- Real-time validation

### 3. Review and Process

- Review parsed data for accuracy
- Validate against business rules
- Process valid items individually or in batches
- Monitor progress in real-time

### 4. Monitor Results

- View processing metrics and analytics
- Track success rates and error patterns
- Export reports in multiple formats

## 🔧 API Endpoints

### Core Endpoints

- `POST /api/v1/eligibility/update` - Single eligibility update
- `POST /api/v1/eligibility/bulk-update` - Batch processing
- `GET /api/v1/eligibility/status/{request_id}` - Check processing status
- `GET /api/v1/eligibility/member/{member_id}` - Member lookup
- `GET /api/v1/eligibility/search` - Search eligibility records

### Example API Usage

```python
import requests

# Single update
response = requests.post("http://localhost:8000/api/v1/eligibility/update", json={
    "member_id": "12345678",
    "policy_number": "DEN-2024-001",
    "benefit_type": "preventive",
    "coverage_percentage": 100.0,
    "annual_maximum": 1500.0,
    "effective_date": "2025-01-01"
})

# Batch update
response = requests.post("http://localhost:8000/api/v1/eligibility/bulk-update", json={
    "updates": [
        # Array of eligibility updates
    ]
})
```

## 🛠️ Development

### Local Development Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Setup database:**
```bash
# Start PostgreSQL and Redis
docker-compose up postgres redis -d

# Run migrations
alembic upgrade head
```

3. **Start services individually:**
```bash
# API Server
uvicorn api_service:app --reload --port 8000

# Celery Worker
celery -A api_service.celery_app worker --loglevel=info

# Streamlit UI
streamlit run streamlit_ui.py --server.port 8501
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## 📊 Data Models

### EligibilityUpdate Schema

```python
{
    "member_id": "string",
    "policy_number": "string", 
    "benefit_type": "preventive|basic|major|orthodontic|emergency",
    "coverage_percentage": "float",
    "annual_maximum": "float",
    "deductible": "float",
    "waiting_period": "integer",
    "effective_date": "YYYY-MM-DD",
    "expiration_date": "YYYY-MM-DD",
    "provider_network": "in-network|out-of-network",
    "procedure_codes": ["array of CDT codes"]
}
```

## 🔐 Security Considerations

- API keys stored as environment variables
- Database credentials secured
- Input validation and sanitization
- Rate limiting on API endpoints
- Audit logging for all changes

## 📈 Monitoring and Analytics

The system provides comprehensive monitoring through:

- **Processing Metrics**: Success rates, processing times, error counts
- **Data Quality**: Validation failure patterns, data completeness
- **Performance**: API response times, queue lengths, system resource usage
- **Business KPIs**: Daily processing volumes, analyst productivity

## 🔄 Integration

### External Insurance API Integration

The system is designed to integrate with external insurance provider APIs:

```python
# Example external API call
async def update_external_system(member_id: str, updates: dict):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = await httpx.post(
        f"{base_url}/eligibility/update",
        json={"member_id": member_id, "updates": updates},
        headers=headers
    )
    return response.json()
```

### Notification System

Automated email notifications for:
- Processing completion
- Error alerts
- Daily summary reports
- System health status

## 🆘 Troubleshooting

### Common Issues

1. **LLM Parsing Errors**
   - Verify OpenAI API key is valid
   - Check input data format
   - Review parsing prompts

2. **Database Connection Issues**
   - Ensure PostgreSQL is running
   - Check connection string in .env
   - Verify database permissions

3. **API Integration Failures**
   - Validate external API credentials
   - Check network connectivity
   - Review API endpoint URLs

### Logs and Debugging

```bash
# View API logs
docker-compose logs api

# View worker logs  
docker-compose logs celery_worker

# View UI logs
docker-compose logs ui
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki

---

**Note**: This is a production-ready system designed for healthcare environments. Ensure compliance with HIPAA and other relevant regulations when handling protected health information.
