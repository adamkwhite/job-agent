# Flask API Local Development Setup

This guide covers running the Company Monitoring API locally for development and testing.

## Quick Start

```bash
# Activate virtual environment
source job-agent-venv/bin/activate

# Run Flask API (production mode - debug disabled)
python -m src.api.app

# Or run with auto-reload for development
FLASK_DEBUG=1 python -m src.api.app
```

The API will be available at `http://127.0.0.1:5000`

## Environment Variables

### FLASK_DEBUG

Controls Flask debug mode and auto-reload.

**Default:** `false` (production mode)

**Values:**
- `1`, `true`, or `yes` - Enable debug mode
- `0`, `false`, or `no` - Disable debug mode (production)

**Example:**
```bash
# Enable debug mode for local development
export FLASK_DEBUG=1
python -m src.api.app

# Or inline
FLASK_DEBUG=1 python -m src.api.app
```

**⚠️ Security Warning:**
Never enable debug mode in production. Debug mode exposes the Werkzeug debugger which allows arbitrary code execution.

### FLASK_CORS_ORIGINS

Controls which origins can make cross-origin requests to the API.

**Default:** `chrome-extension://*,http://localhost:*`

**Format:** Comma-separated list of origin patterns

**Example:**
```bash
# Allow only specific Chrome extension
export FLASK_CORS_ORIGINS="chrome-extension://abc123xyz,http://localhost:3000"
python -m src.api.app

# Allow all origins (NOT RECOMMENDED for production)
export FLASK_CORS_ORIGINS="*"
python -m src.api.app
```

## API Endpoints

### Health Check
```bash
curl http://127.0.0.1:5000/
```

**Response:**
```json
{
  "status": "ok",
  "message": "Job Agent Company Monitoring API",
  "version": "1.0",
  "endpoints": {
    "POST /add-company": "Add a company to monitor",
    "GET /companies": "List all monitored companies",
    "GET /company/<id>": "Get a specific company",
    "POST /company/<id>/toggle": "Enable/disable monitoring"
  }
}
```

### Add Company
```bash
curl -X POST http://127.0.0.1:5000/add-company \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Boston Dynamics",
    "careers_url": "https://bostondynamics.com/careers",
    "notes": "Robotics leader"
  }'
```

### List Companies
```bash
# Get all active companies
curl http://127.0.0.1:5000/companies

# Get all companies (including inactive)
curl http://127.0.0.1:5000/companies?active_only=false
```

### Get Specific Company
```bash
curl http://127.0.0.1:5000/company/1
```

### Toggle Company Status
```bash
curl -X POST http://127.0.0.1:5000/company/1/toggle
```

## Testing

Run the test suite:
```bash
# All tests with coverage
pytest tests/unit/test_api_simple.py tests/unit/test_company_service.py -v --cov=src/api

# Just API endpoint tests
pytest tests/unit/test_api_simple.py -v

# Just database service tests
pytest tests/unit/test_company_service.py -v
```

## Database

The API uses SQLite with the database located at `data/jobs.db`.

**Schema:** `companies` table
- `id` - Auto-incrementing primary key
- `name` - Company name
- `careers_url` - URL to careers page
- `scraper_type` - Type of scraper to use (default: 'generic')
- `active` - Boolean flag (1 = active, 0 = inactive)
- `last_checked` - Timestamp of last scrape
- `notes` - Optional notes
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

**Constraint:** UNIQUE(name, careers_url) prevents duplicates

## Troubleshooting

### Pre-commit Safety Hook Cache Issue

If the pre-commit Safety hook reports vulnerabilities for dependencies that have been upgraded:

```bash
# Clear pre-commit cache
pre-commit clean

# Re-run hooks
pre-commit run --all-files
```

### Port Already in Use

If port 5000 is already in use:

```bash
# Find process using port 5000
lsof -i :5000

# Kill process (replace PID with actual process ID)
kill <PID>
```

### Database Locked

If you get "database is locked" errors, ensure no other processes are accessing `data/jobs.db`:

```bash
# Check for processes accessing the database
lsof data/jobs.db

# Or restart the API server
```

## Chrome Extension Integration

The Chrome extension (`chrome-extension/`) connects to this API to add companies while browsing.

1. Load the extension in Chrome:
   - Open `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` directory

2. Start the Flask API:
   ```bash
   FLASK_DEBUG=1 python -m src.api.app
   ```

3. Navigate to a company's careers page and click the extension icon to add the company.

## Production Deployment

For production deployment:

1. **Disable debug mode** - Use `FLASK_DEBUG=0` or omit the variable
2. **Use a production WSGI server** - gunicorn, uWSGI, or similar (not Flask's built-in server)
3. **Restrict CORS origins** - Set `FLASK_CORS_ORIGINS` to specific trusted origins
4. **Use environment secrets** - Store sensitive config in environment variables, not in code
5. **Enable HTTPS** - Use TLS/SSL certificates
6. **Database backups** - Regular backups of `data/jobs.db`

Example gunicorn command:
```bash
gunicorn -w 4 -b 127.0.0.1:5000 "src.api.app:app"
```
