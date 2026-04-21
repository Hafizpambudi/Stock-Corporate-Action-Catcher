# AGENTS.md - Developer Guide for Investor Relation Automation

This file provides guidelines and instructions for agentic coding agents operating in this repository.

## Project Overview

Python-based agentic system that monitors Indonesian Stock Exchange (IDX) announcements, parses PDFs, and provides AI-powered financial sentiment analysis using OpenRouter LLMs.

**Tech Stack**: Python, Playwright, PyMuPDF, httpx, APScheduler, OpenRouter API

---

## Build & Run Commands

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Playwright Browsers

```bash
playwright install
```

### Run the Application

```bash
# Run immediately (default)
python main.py

# Explicit immediate run
python main.py --run-now

# Run in scheduled mode (daily at 08:00)
python main.py --schedule
```

### Running Tests

**Note**: This project currently has no test suite. When adding tests:

```bash
# Run all tests (pytest)
pytest

# Run a single test file
pytest tests/test_financial_expert.py

# Run a single test function
pytest tests/test_financial_expert.py::TestFinancialExpert::test_analyze
```

**Recommended test structure**:
- Place tests in `tests/` directory
- Use `pytest` as the test framework
- Mock external APIs (OpenRouter, IDX) to avoid network dependencies

---

## Code Style Guidelines

### Imports

- **Standard library first**, then third-party, then local
- Use absolute imports (e.g., `from agents.data_collector import ...`)
- Group: stdlib, third-party, local
- Sort within groups alphabetically

```python
# Correct
import asyncio
import logging
import os
from datetime import datetime

from playwright.async_api import async_playwright
import fitz
import httpx

from agents.data_collector import DataCollectorAgent
from config.settings import IDX_BASE_URL
```

### Formatting

- Line length: 100 characters max
- Indentation: 4 spaces (no tabs)
- Use Black formatting when available
- Use trailing commas in multi-line calls

```python
# Good
response = requests.post(
    url=self.api_url,
    headers=self.headers,
    data=json.dumps({...}),
)
```

### Type Hints

- Use type hints for function signatures and return values
- Use built-in types (`list`, `dict`, `str`) not typing modules when possible
- Be explicit with complex types

```python
# Good
async def run(self) -> list[dict]:
def analyze(self, announcement_data: dict) -> dict:
def _extract_text_from_pdf(self, pdf_path: str) -> str:

# Avoid
async def run(self):
def analyze(self, data):
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `DataCollectorAgent`)
- **Functions/methods**: `snake_case` (e.g., `run()`, `_extract_ticker()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `OPENROUTER_API_KEY`)
- **Private methods**: prefix with `_` (e.g., `_collect_todays_announcements`)
- **Descriptive names**: avoid single letters except loop vars

### Error Handling

- Use specific exception types when possible
- Log errors with context before re-raising
- Return meaningful error messages to callers
- Never swallow exceptions silently

```python
# Good
try:
    response = await client.get(ann['pdf_url'])
    if response.status_code == 200:
        # process
except httpx.TimeoutException as e:
    logger.error(f"Timeout downloading PDF: {ann['pdf_url']}", exc_info=True)
    continue
except Exception as e:
    logger.error(f"Error parsing PDF {ann['pdf_url']}: {e}")
    raise
```

### Async/Await Patterns

- Use `async_playwright()` as context manager for proper cleanup
- Always await async operations
- Use `asyncio.run()` for top-level async calls

```python
# Good
async def run(self) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # ...
```

### Configuration

- All config via `config/settings.py` or `.env`
- Never hardcode credentials or URLs
- Use `os.getenv()` with sensible defaults

### Comments

- **DO NOT add any comments** in generated code unless explicitly requested by the user
- Code should be self-explanatory through clear naming and structure

---

## Project Structure

```
Investor Relation Automation/
├── agents/                    # Agent implementations
│   ├── data_collector.py     # Web scraping & PDF parsing
│   └── financial_expert.py   # LLM-based analysis
├── config/                   # Configuration
│   └── settings.py           # Environment-based config
├── data/output/              # Generated reports
├── main.py                   # Orchestration & scheduling
├── requirements.txt          # Dependencies
└── .env                      # Local environment (not committed)
```

---

## Agent-Specific Guidelines (from CoderDev)

### Plan Mode
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions)
- Write detailed specs upfront to reduce ambiguity
- If something goes sideways, STOP and re-plan immediately

### Self-Improvement
- After any correction: capture the pattern to prevent recurrence
- Write rules for yourself that prevent the same mistake

### Verification Before Done
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask: "Would a staff engineer approve this?"

### Bug Fixing
- When given a bug report: just fix it
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user

### Core Principles
- **Simplicity First**: Make every change as simple as possible
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Elegance**: For non-trivial changes, ask "is there a more elegant way?"

---

## Common Tasks Reference

### Adding a new agent
1. Create `agents/new_agent.py` with class inheriting appropriate base
2. Import and use in `main.py`
3. Add configuration to `config/settings.py` if needed

### Modifying selectors
IDX website structure may change. CSS selectors in `data_collector.py`:
```python
rows = await page.query_selector_all("table tbody tr")
```
Use browser dev tools to inspect and adjust.

### Changing LLM model
Edit `.env`:
```env
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | Required. API key for OpenRouter |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API endpoint |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.1-70b-instruct` | Model to use |
| `IDX_BASE_URL` | IDX disclosure page | Target URL |
| `OUTPUT_DIR` | `data/output` | Where to save results |
| `SCHEDULE_HOUR` | `8` | Daily run hour |
| `SCHEDULE_MINUTE` | `0` | Daily run minute |

---

## Important Notes

- Respect rate limits when scraping IDX
- Failed PDF downloads are logged and skipped gracefully
- Check logs for detailed troubleshooting
- The system only runs on weekdays (mon-fri) in scheduled mode