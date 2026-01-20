# Google Maps Closed Places Manager

A Python web application that helps you identify and remove closed businesses from your Google Maps saved places lists.

[![CI](https://github.com/bkero/ClosedChecker/actions/workflows/ci.yml/badge.svg)](https://github.com/bkero/ClosedChecker/actions/workflows/ci.yml)

## Features

- **Import Google Takeout Data**: Upload your Google Takeout export (ZIP or JSON) containing saved places
- **Check Business Status**: Uses Google Places API to check if businesses are still operational
- **Filter by Status**: View places filtered by OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY, or UNKNOWN
- **Export Results**: Download results as JSON or CSV for further analysis
- **Remove Closed Places**: Automated browser-based removal of selected places from your saved lists

## Screenshots

The web interface provides a simple workflow:

1. Upload your Google Takeout export
2. Enter your Google Places API key to check business status
3. Review results and filter by status
4. Export or remove closed places

## Prerequisites

- Python 3.11 or higher
- Google Places API key (see setup below)
- Google Takeout export of your saved places

### Setting Up Google Places API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Places API (New)**:
   - Navigate to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
   - Search for "Places API (New)"
   - Click on it and press "Enable"
4. Create an API key:
   - Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
   - Click "Create Credentials" > "API Key"
   - (Recommended) Restrict the key to only the Places API (New)

**Important**: This application uses the **Places API (New)**, not the legacy Places API. Make sure you enable the correct one.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ClosedChecker.git
cd ClosedChecker

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for removal feature)
playwright install chromium
```

### Configuration

Copy the example environment file and customize if needed:

```bash
cp .env.example .env
```

Available configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `127.0.0.1` | Server bind address |
| `APP_PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `PLAYWRIGHT_HEADLESS` | `false` | Run browser in headless mode |
| `PLACES_API_DELAY_MS` | `100` | Delay between API requests (rate limiting) |
| `MAX_UPLOAD_SIZE_MB` | `100` | Maximum upload file size |

## Usage

### 1. Export Your Saved Places from Google

1. Go to [Google Takeout](https://takeout.google.com/)
2. Deselect all products
3. Select only "Maps (your places)"
4. Create and download the export

### 2. Start the Application

```bash
# Start the server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or with auto-reload for development
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser.

### 3. Upload and Check Status

1. Upload your Google Takeout ZIP or JSON file
2. Enter your Google Places API key
3. Click "Check Status" to query the Places API
4. Review the results filtered by business status

### 4. Export or Remove Places

- **Export**: Download results as JSON or CSV
- **Remove**: Use the removal feature to remove places from your saved lists
  - Requires one-time Google authentication via browser
  - Places are removed one at a time using browser automation

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/file` | Upload Takeout ZIP/JSON |
| `POST` | `/api/places/check` | Start status check |
| `GET` | `/api/places/check/{job_id}` | Get check progress |
| `GET` | `/api/places/results/{session_id}` | Get places with status |
| `GET` | `/api/export/json/{session_id}` | Export as JSON |
| `GET` | `/api/export/csv/{session_id}` | Export as CSV |
| `GET` | `/api/removal/auth/status` | Check auth status |
| `POST` | `/api/removal/auth/start` | Start auth session |
| `POST` | `/api/removal/execute` | Remove places |
| `WS` | `/ws/progress/{job_id}` | Real-time progress |

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Code Formatting

```bash
# Format code
black app tests

# Lint
ruff check app tests
```

## Limitations

- **No Direct API Access**: Google doesn't provide API access to user's saved places, so removal requires browser automation
- **Manual Login Required**: Google blocks automated login, so you must log in manually once
- **Auth Expiration**: Saved browser session may expire after about a week
- **Rate Limits**: Google Places API has quotas; large lists may take time to process

## How It Works

1. **Parsing**: The app parses Google Takeout GeoJSON files and extracts place identifiers (CID or place_id) from URLs
2. **Status Check**: Uses Google Places API to query `business_status` for each place
3. **Removal**: Uses Playwright browser automation to:
   - Load your authenticated Google session
   - Navigate to each place's Google Maps page
   - Click the "Saved" button to unsave the place

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use to manage your own Google Maps saved places. Use responsibly and in accordance with Google's Terms of Service. The authors are not responsible for any misuse or consequences of using this tool.
