# Hospital Bulk Processing System

A robust, production-grade bulk processing API that integrates with the Hospital Directory API to handle CSV uploads and process hospital records in batches.

## 🎯 Project Overview

This system accepts CSV files containing hospital records, validates the data, creates each hospital through the Hospital Directory API with concurrent requests, and activates the entire batch once all hospitals are successfully created. It features comprehensive error handling, retry logic for transient failures, state persistence, and a complete testing suite.

### Key Features

- ✅ **Bulk CSV Upload** - Process up to 20 hospitals per batch
- ✅ **Concurrent Processing** - AsyncIO-based concurrent hospital creation
- ✅ **Intelligent Retry Logic** - Exponential backoff for transient failures (5xx, timeouts, connection errors)
- ✅ **Partial Failure Handling** - Skip activation if any hospital fails; detailed failure reporting
- ✅ **State Persistence** - In-memory storage with automatic disk serialization for recovery
- ✅ **Progress Tracking** - Polling endpoint to check batch status in real-time
- ✅ **Resume Capability** - Retry failed hospitals in partially failed batches
- ✅ **CSV Validation** - Inline validation with detailed error messages
- ✅ **Comprehensive Testing** - Unit + integration tests with 80%+ coverage
- ✅ **Docker Support** - Dockerfile + docker-compose.yml for easy deployment
- ✅ **Production Ready** - Gunicorn server, health checks, extensive logging

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Client        │
│  (CSV Upload)   │
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│  Flask Routes        │
│  - POST /hospitals/  │
│  - GET /batches/     │
│  - POST /batches/    │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────────┐
│  BatchProcessor          │
│  (Orchestration)         │
└────┬─────────┬───────────┘
     │         │
     ▼         ▼
┌─────────┐  ┌──────────────────┐
│CSV      │  │Hospital API      │
│Service  │  │Client            │
└─────────┘  ├──────────────────┤
             │ Retry Policy     │
             │ - Max 3 retries  │
             │ - 1s, 2s, 4s     │
             │   backoff        │
             └────────┬─────────┘
                      │
                      ▼
            ┌──────────────────┐
            │Hospital          │
            │Directory API     │
            │(External)        │
            └──────────────────┘

┌──────────────────────┐
│ Batch Repository     │
│ - In-memory store    │
│ - Disk persistence   │
│ - Recovery on start  │
└──────────────────────┘
```

---

## 🚀 Quick Start

### Local Development Setup

#### Prerequisites
- Python 3.12+
- pip

#### Installation

```bash
# Clone repository
git clone <repository-url>
cd Hospital-Bulk-Processing-System

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

#### Running Locally

```bash
# Start development server
python run.py

# Server runs on http://localhost:5000

# In another terminal, test the health endpoint
curl http://localhost:5000/health
```

---

### Docker Setup

#### Using Docker Compose (Recommended)

```bash
# Build and start container
docker-compose up

# Server runs on http://localhost:5000

# In another terminal, test health
curl http://localhost:5000/health

# Stop container
docker-compose down
```

#### Using Docker Directly

```bash
# Build image
docker build -t hospital-bulk-processor .

# Run container
docker run -p 5000:5000 \
  -e HOSPITAL_API_URL=https://hospital-directory.onrender.com \
  -v $(pwd)/data:/app/data \
  hospital-bulk-processor

# Test
curl http://localhost:5000/health
```

---

## 📚 API Documentation

### Base URL
- **Local**: `http://localhost:5000`
- **Production**: [Deployed URL]

### Endpoints

#### 1. Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Hospital Bulk Processing System"
}
```

---

#### 2. Bulk Upload Hospitals
```
POST /hospitals/bulk
Content-Type: multipart/form-data
```

**Request:**
- Field: `file` - CSV file with hospitals

**CSV Format:**
```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Medical Center,456 Oak Ave,
```

**Headers:**
- `name` (required): Hospital name
- `address` (required): Hospital address
- `phone` (optional): Hospital phone number

**Constraints:**
- Maximum 20 hospitals per batch
- Maximum 5MB file size

**Response:** (200 OK)
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "total_hospitals": 2,
  "processed_hospitals": 2,
  "failed_hospitals": 0,
  "processing_time_seconds": 15.3,
  "batch_activated": true,
  "activation_status": "success",
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 101,
      "name": "General Hospital",
      "status": "created_and_activated",
      "attempts": 1,
      "failure_reason": null
    }
  ]
}
```

**Error Response:** (400 Validation Error)
```json
{
  "status": "validation_error",
  "message": "Missing required header: address",
  "details": ["Row 1: address is required"]
}
```

---

#### 3. Get Batch Status
```
GET /batches/{batch_id}
```

**Parameters:**
- `batch_id` (path): Unique batch identifier

**Response:** (200 OK)
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "total_hospitals": 2,
  "processed_hospitals": 1,
  "failed_hospitals": 0,
  "batch_activated": false,
  "activation_status": "pending",
  "started_at": "2026-06-27T16:00:00",
  "completed_at": null,
  "processing_time_seconds": null,
  "hospitals": [...]
}
```

**Error Response:** (404 Not Found)
```json
{
  "status": "error",
  "message": "Batch not found: invalid-id"
}
```

---

#### 4. Resume Failed Batch
```
POST /batches/{batch_id}/resume
```

**Parameters:**
- `batch_id` (path): Batch ID in PARTIAL_FAILURE or FAILED state

**Response:** (200 OK)
- Same as bulk upload response

**Error Response:** (400 Validation Error)
```json
{
  "status": "validation_error",
  "message": "Batch cannot be resumed. Current status: COMPLETED. Only PARTIAL_FAILURE or FAILED batches can be resumed.",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 📊 Batch States

```
UPLOADED → VALIDATING → PROCESSING → COMPLETED
                              ↓
                        (if any fail)
                              ↓
                       PARTIAL_FAILURE → [Resume] → COMPLETED
                              ↓
                          (if all fail)
                              ↓
                           FAILED → [Resume] → COMPLETED/PARTIAL_FAILURE
```

### Status Meanings

| Status | Meaning |
|--------|---------|
| `UPLOADED` | CSV file received |
| `VALIDATING` | Validating CSV format |
| `PROCESSING` | Creating hospitals concurrently |
| `COMPLETED` | All hospitals created and activated |
| `PARTIAL_FAILURE` | Some hospitals failed; activation skipped |
| `FAILED` | All hospitals failed or critical error |

### Item Status

| Status | Meaning |
|--------|---------|
| `created_and_activated` | Hospital created and batch activated |
| `creation_failed` | Hospital creation failed (permanent error) |

---

## 🧪 Testing

### Run All Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_csv_service.py

# Run specific test
pytest tests/unit/test_csv_service.py::TestCSVService::test_parse_csv_valid

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── test_csv_service.py     # CSV parsing and validation
│   ├── test_retry_policy.py    # Retry logic
│   └── test_batch_repository.py # State persistence
└── integration/
    └── test_bulk_endpoint.py   # Full endpoint tests
```

### Coverage

Current test coverage: ~80%+

```bash
pytest --cov=app --cov-report=term-missing
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment (development, production, testing) |
| `HOSPITAL_API_URL` | `https://hospital-directory.onrender.com` | Hospital Directory API base URL |
| `REQUEST_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `MAX_RETRIES` | `3` | Maximum retry attempts for transient failures |
| `MAX_BATCH_SIZE` | `20` | Maximum hospitals per batch |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DATA_DIR` | `data` | Directory for persisting batch data |

### Create `.env` File

```bash
cp .env.example .env
# Edit .env with your values
```

---

## 📝 Logging

The application logs all important operations:

```
2026-06-27 16:08:03 - app - INFO - Creating Flask app with config: DevelopmentConfig
2026-06-27 16:08:04 - batch_processor - INFO - Starting batch processing: batch_id=xyz-123
2026-06-27 16:08:05 - hospital_client - DEBUG - Making POST request to https://...
2026-06-27 16:08:05 - retry_policy - WARNING - Retryable error on attempt 1: timeout. Retrying in 1s...
2026-06-27 16:08:06 - hospital_client - DEBUG - Request successful: POST /hospitals/
```

Logs include:
- Batch lifecycle events
- Hospital creation attempts and retries
- Validation errors
- API communication
- State persistence operations

---

## 🚢 Deployment

### Render Deployment

1. **Create Render Account**
   - Visit https://render.com
   - Sign up and connect GitHub

2. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect GitHub repository
   - Select repository

3. **Configure Service**
   - **Name**: `hospital-bulk-processor`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`

4. **Set Environment Variables**
   - `FLASK_ENV`: `production`
   - `HOSPITAL_API_URL`: `https://hospital-directory.onrender.com`
   - Other variables as needed

5. **Deploy**
   - Click "Create Web Service"
   - Monitor deployment progress
   - Once running, test health endpoint

### Verifying Deployment

```bash
# Test health endpoint
curl https://[your-render-url]/health

# Test bulk upload (from your machine)
curl -F "file=@hospitals.csv" https://[your-render-url]/hospitals/bulk

# Check batch status
curl https://[your-render-url]/batches/{batch_id}
```

---

## 🔄 Design Principles

### Architecture

- **Separation of Concerns**: Each layer (routes, services, repository) has distinct responsibilities
- **Dependency Injection**: Services receive dependencies rather than creating them
- **Repository Pattern**: Abstract storage layer enables easy future database migration
- **Service Layer**: Business logic isolated from HTTP handling

### Error Handling

- **Retryable Errors** (5xx, timeout, connection): Exponential backoff with 3 attempts (1s, 2s, 4s)
- **Non-Retryable Errors** (4xx): Fail immediately with detailed message
- **Partial Failures**: Report individual hospital failures without failing entire batch

### Performance

- **Concurrent Processing**: All hospitals created simultaneously using AsyncIO
- **Efficient Validation**: Pre-validation before any API calls
- **Minimal State**: In-memory storage with lazy disk persistence

### Reliability

- **Crash Recovery**: All batches persisted to disk; automatically recovered on restart
- **Detailed Logging**: Every significant operation logged with batch ID and context
- **Health Checks**: Built-in health endpoint for monitoring

---

## 📦 Dependencies

### Core
- **Flask**: Web framework
- **httpx**: Async HTTP client
- **Pydantic**: Data validation
- **python-dotenv**: Environment configuration

### Production
- **Gunicorn**: WSGI server

### Development & Testing
- **pytest**: Testing framework
- **pytest-mock**: Test mocking
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support

---

## 🛠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app'"

**Solution**: Ensure you're running from the project root directory and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: "Connection timeout to Hospital API"

**Solution**: Check that the API URL is correct and accessible:
```bash
curl https://hospital-directory.onrender.com/docs
```

### Issue: Batches not persisting after restart

**Solution**: Ensure `data/` directory exists and is writable:
```bash
mkdir -p data
chmod 755 data
```

### Issue: Tests failing with "Event loop is closed"

**Solution**: This is a known asyncio issue on Windows. Use pytest-asyncio:
```bash
pip install pytest-asyncio
pytest --asyncio-mode=auto
```

---

## 📈 Performance Metrics

### Typical Performance (with 20 hospitals)

| Metric | Expected |
|--------|----------|
| CSV Parsing | <100ms |
| Concurrent Creation | 5-30s (depends on API) |
| Batch Activation | 1-5s |
| **Total Processing** | **10-45s** |

### Scalability

- Handles 20 hospitals per batch (API constraint)
- Concurrent requests minimize total processing time
- Retry logic ensures reliability despite network issues
- Disk persistence prevents data loss on crashes

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/name`
2. Commit changes: `git commit -m "Description"`
3. Push to branch: `git push origin feature/name`
4. Create Pull Request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests for new features
- Maintain 80%+ test coverage

---

## 📄 License

This project is part of the Paribus Python Challenge.

---

## 🔗 References

- **Hospital Directory API**: https://hospital-directory.onrender.com/docs
- **Flask Documentation**: https://flask.palletsprojects.com/
- **AsyncIO Guide**: https://docs.python.org/3/library/asyncio.html
- **Pytest Documentation**: https://docs.pytest.org/

---

## ✨ Key Implementation Details

### Concurrent Hospital Creation

```python
# Create all hospitals simultaneously
async with HospitalAPIClient() as client:
    tasks = [
        client.create_hospital(name, address, phone, batch_id)
        for name, address, phone in hospitals
    ]
    results = await asyncio.gather(*tasks)
```

### Intelligent Retry Logic

```python
# Automatic exponential backoff
async def execute_with_retry(func):
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except RetryableError:
            if attempt < max_retries:
                await asyncio.sleep(DELAYS[attempt])  # 1s, 2s, 4s
            else:
                raise
```

### State Persistence

```python
# Automatic disk backup on every save
batch.save(repository)
# → Saves to memory
# → Persists to data/{batch_id}.json
# → Recovers on restart
```

---

**Built with ❤️ for the Paribus Interview Challenge**

