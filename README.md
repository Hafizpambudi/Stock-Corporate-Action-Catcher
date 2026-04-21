# Investor Relation Automation System

*Last updated: 2026-04-15T21:48:24+07:00*

An agentic system that automatically monitors Indonesian Stock Exchange (IDX) announcements, parses them, and provides AI-powered financial sentiment analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌───────────────────┐          ┌──────────────────────┐
│  Data Collector   │          │ Financial Expert     │
│  Agent            │─────────▶│ Agent                │
│                   │  Data    │                      │
│ - Web scraping    │          │ - LLM analysis       │
│ - PDF parsing     │          │ - Sentiment detection│
│ - Data extraction │          │ - Impact assessment  │
└───────────────────┘          └──────────────────────┘
```

## Features

- **Automated Daily Monitoring**: Scrapes IDX disclosures every trading day
- **PDF Parsing**: Extracts text from announcement PDFs
- **AI-Powered Analysis**: Uses OpenRouter models for financial sentiment analysis
- **Structured Output**: Generates JSON reports with ticker, analysis, and source
- **Scheduling**: Runs automatically during market hours

## Tech Stack

- **Browser Automation**: Playwright
- **PDF Processing**: PyMuPDF (fitz)
- **LLM Integration**: OpenRouter API (compatible with multiple models)
- **Scheduling**: APScheduler
- **HTTP Client**: httpx

## Setup

### 1. Install Dependencies

Using uv (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install
```

### 3. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
copy .env.example .env
```

Edit `.env`:
```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
```

### 4. Create Output Directory

```bash
mkdir -p data/output
```

## Usage

### Run Immediately

```bash
python main.py --run-now
```

### Run in Scheduled Mode (Daily at configured time)

```bash
python main.py --schedule
```

Default schedule: Monday-Friday at 08:00

## Viewing the Dashboard

After running the analysis, you can view the results in the web dashboard:

### Option 1: Python HTTP Server (Recommended)

From the project root, serve the `frontend` directory:

```bash
cd frontend && python -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

### Option 2: Direct File Access

Open `frontend/index.html` directly in your browser. The dashboard will attempt to fetch the latest results JSON from `../data/output/results_YYYY-MM-DD.json`.

### Option 3: Any Static Server

You can use any static file server (VS Code Live Server, nginx, etc.) pointing to the `frontend/` directory.

**Note**: The dashboard loads the results file for today's date automatically. Ensure the JSON file exists in `data/output/` before opening the dashboard.

## Output Format

Results are saved to `data/output/results_YYYY-MM-DD.json`:

```json
[
  {
    "Ticker": "BBCA",
    "analysis": "This announcement discusses Q4 2025 financial results showing a 15% increase in net profit...\n\nSentiment: POSITIVE\nInvestor Impact: HIGH\n\nKey Points:\n- Revenue growth exceeded market expectations\n- Strong loan portfolio expansion\n- Improved net interest margin...",
    "source": "https://www.idx.co.id/Portals/.../announcement.pdf"
  }
]
```

## Project Structure

```
Investor Relation Automation/
├── agents/
│   ├── __init__.py
│   ├── data_collector.py       # Web scraping & PDF parsing
│   └── financial_expert.py     # LLM-based analysis
├── config/
│   ├── __init__.py
│   └── settings.py             # Configuration management
├── data/
│   └── output/                 # Generated reports
├── frontend/
│   └── index.html              # Dashboard UI
├── .env.example
├── .gitignore
├── main.py                     # Orchestration & scheduling
├── pyproject.toml              # Project configuration and dependencies
└── requirements.txt
```

## Configuration

Edit `config/settings.py` or `.env` to customize:

- **OPENROUTER_MODEL**: Choose different models available on OpenRouter
- **IDX_BASE_URL**: Change if IDX updates their URL structure
- **OUTPUT_DIR**: Custom output directory
- **SCHEDULE_HOUR/SCHEDULE_MINUTE**: Adjust run time

## Important Notes

### Web Scraping Selectors

The IDX website structure may change. If the scraper fails to find announcements, you may need to update the CSS selectors in `agents/data_collector.py`:

```python
rows = await page.query_selector_all("table tbody tr")
```

Use browser dev tools to inspect the actual page structure and adjust accordingly.

### Rate Limiting

- Be respectful of IDX's servers
- The system includes built-in delays
- Don't run too frequently during non-trading hours

### Error Handling

- Failed PDF downloads are logged and skipped
- LLM analysis errors return error messages in output
- Check logs for detailed troubleshooting info

## Future Enhancements

- [ ] Add notification system (email/Telegram) for high-impact announcements
- [ ] Implement caching to avoid re-processing same announcements
- [ ] Add database storage for historical analysis
- [ ] Support for multiple stock exchanges
- [ ] Web dashboard for viewing results
- [ ] Improved ticker extraction with validation
- [ ] Handle pagination on IDX website

## License

MIT

## Disclaimer

This tool is for informational purposes only. Not financial advice. Always do your own research before making investment decisions.
