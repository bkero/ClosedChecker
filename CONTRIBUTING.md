# Contributing to Google Maps Closed Places Manager

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate in all interactions. We welcome contributors of all backgrounds and experience levels.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/gmaps-closed/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)
   - Relevant logs or error messages

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue describing:
   - The feature and its use case
   - Why it would be valuable
   - Possible implementation approaches

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass: `pytest`
6. Format your code: `black app tests`
7. Lint your code: `ruff check app tests`
8. Commit with a clear message
9. Push and create a Pull Request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Local Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/gmaps-closed.git
cd gmaps-closed

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with dev extras
pip install -e ".[dev]"

# Install Playwright browsers (for full functionality)
playwright install chromium
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_takeout_parser.py

# Run with verbose output
pytest -v
```

### Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting (line length 100)
- **Ruff**: Linting
- **mypy**: Type checking (optional but encouraged)

```bash
# Format code
black app tests

# Check formatting without changes
black --check app tests

# Lint
ruff check app tests

# Auto-fix lint issues
ruff check --fix app tests

# Type check
mypy app --ignore-missing-imports
```

### Project Structure

```
app/
├── api/
│   ├── routes/      # API endpoint handlers
│   └── websocket.py # WebSocket handlers
├── core/            # Core utilities and exceptions
├── models/          # Pydantic data models
├── services/        # Business logic services
├── config.py        # Application configuration
└── main.py          # FastAPI application entry
tests/               # Test files
templates/           # Jinja2 HTML templates
static/              # CSS and JavaScript files
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test names that explain what is being tested
- Use fixtures from `conftest.py` when appropriate
- Aim for high coverage of critical paths

Example:

```python
def test_parse_geojson_extracts_place_name():
    """Test that place names are correctly extracted from GeoJSON."""
    parser = TakeoutParser()
    places = parser.parse_file(sample_data, "test.json")
    assert places[0].name == "Expected Name"
```

### Commit Messages

Use clear, descriptive commit messages:

- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 72 characters
- Add details in the body if needed

Examples:
- `Add CSV export functionality`
- `Fix CID extraction from new URL format`
- `Update README with installation instructions`

## Questions?

Feel free to open an issue for questions or discussions about the project.
