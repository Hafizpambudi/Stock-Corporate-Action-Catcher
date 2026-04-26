import json
import logging
import requests
import time
from datetime import datetime
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting configuration
RPM_LIMIT = 20  # Free tier: 20 requests per minute
DAILY_LIMIT = 50  # Free tier: 50 requests per day
MIN_DELAY_SECONDS = 60 / RPM_LIMIT  # 3 seconds between requests


class FinancialExpertAgent:
    """Agent responsible for analyzing IDX announcements for sentiment and investor impact."""

    SYSTEM_PROMPT = """You are a seasoned financial analyst specializing in Indonesian stock market (IDX)
    corporate announcements. Your role is to:

    1. Analyze the announcement content carefully and objectively
    2. Identify key financial implications and business impact
    3. Determine the sentiment (POSITIVE, NEGATIVE, or NEUTRAL)
    4. Assess the likely investor reaction and market impact (HIGH, MEDIUM, or LOW)

    Consider these factors:
    - Financial performance (earnings, revenue, profit changes)
    - Corporate actions (dividends, stock splits, mergers)
    - Regulatory compliance or violations
    - Management changes
    - Business expansion or contraction
    - Industry trends and market conditions

    Provide a detailed, professional analysis in BAHASA INDONESIA (not English)
    that helps investors understand the implications. Use clear, formal Indonesian
    business language."""

    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        self.model = OPENROUTER_MODEL
        # Rate limiting state
        self._request_times = []
        self._daily_request_count = 0
        self._last_day = datetime.now().day

    def analyze(self, announcement_data: dict) -> dict:
        """
        Analyze a single announcement and return structured insights.

        Args:
            announcement_data: Dict with ticker, title, date, pdf_url, content

        Returns:
            Dict with Ticker, analysis, and source
        """
        logger.info(f"Analyzing announcement for {announcement_data['ticker']}...")

        user_prompt = self._build_prompt(announcement_data)

        # Apply rate limiting before making request
        self._apply_rate_limit()

        max_retries = 5
        base_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url=self.api_url,
                    headers=self.headers,
                    data=json.dumps(
                        {
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": self.SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.3,
                            "max_tokens": 1000,
                        }
                    ),
                )

                if response.status_code == 429:
                    # Rate limited - extract retry delay from headers or use exponential backoff
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = int(retry_after)
                    else:
                        delay = base_delay * (2**attempt)  # Exponential backoff

                    logger.warning(
                        f"Rate limited. Waiting {delay}s before retry {attempt + 1}/{max_retries}"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                result = response.json()
                analysis_text = result["choices"][0]["message"]["content"].strip()

                # Track successful request
                self._track_request()

                # Extract ticker from analysis if original is UNKNOWN
                extracted_ticker = announcement_data["ticker"]
                if extracted_ticker == "UNKNOWN":
                    extracted_ticker = self._extract_ticker_from_analysis(
                        analysis_text, announcement_data.get("title", "")
                    )

                return {
                    "Ticker": extracted_ticker,
                    "analysis": analysis_text,
                    "source": announcement_data["pdf_url"],
                }

            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 429:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Rate limited (HTTPError). Waiting {delay}s before retry {attempt + 1}/{max_retries}"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"Error analyzing announcement: {e}")
                return {
                    "Ticker": announcement_data["ticker"],
                    "analysis": f"Error during analysis: {str(e)}",
                    "source": announcement_data["pdf_url"],
                }
            except Exception as e:
                logger.error(f"Error analyzing announcement: {e}")
                return {
                    "Ticker": announcement_data["ticker"],
                    "analysis": f"Error during analysis: {str(e)}",
                    "source": announcement_data["pdf_url"],
                }

        # All retries exhausted
        logger.error(f"Max retries exceeded for {announcement_data['ticker']}")
        return {
            "Ticker": announcement_data["ticker"],
            "analysis": "Error during analysis: Max retries exceeded due to rate limiting",
            "source": announcement_data["pdf_url"],
        }

    def _apply_rate_limit(self):
        """Apply rate limiting by adding delay between requests."""
        current_time = time.time()

        # Reset daily count if new day
        today = datetime.now().day
        if today != self._last_day:
            self._daily_request_count = 0
            self._last_day = today
            self._request_times = []

        # Check daily limit
        if self._daily_request_count >= DAILY_LIMIT:
            logger.warning(
                f"Daily limit ({DAILY_LIMIT}) reached. Waiting until tomorrow..."
            )
            # Calculate seconds until midnight
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = tomorrow.replace(day=today + 1)
            wait_seconds = (tomorrow - datetime.now()).total_seconds()
            time.sleep(min(wait_seconds, 3600))  # Wait max 1 hour
            self._daily_request_count = 0
            self._request_times = []

        # Clean old timestamps (older than 1 minute)
        self._request_times = [t for t in self._request_times if current_time - t < 60]

        # Apply minimum delay between requests
        if self._request_times:
            time_since_last = current_time - self._request_times[-1]
            if time_since_last < MIN_DELAY_SECONDS:
                sleep_time = MIN_DELAY_SECONDS - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

    def _track_request(self):
        """Track a successful request for rate limiting."""
        self._request_times.append(time.time())
        self._daily_request_count += 1

    def _extract_ticker_from_analysis(self, analysis_text: str, title: str) -> str:
        """Extract ticker from analysis text or title when original is UNKNOWN."""
        import re

        combined = f"{title} {analysis_text}"

        # Look for patterns like (TICKER) or code at start of line
        patterns = [
            r"\b([A-Z]{4})\b",  # 4-letter stock codes
            r"\b([A-Z]{3})\b",  # 3-letter stock codes
            r"code[:\s]+([A-Z]{3,4})",  # "code: XYZ"
            r"ticker[:\s]+([A-Z]{3,4})",  # "ticker: XYZ"
            r"PT\s+([A-Z][a-zA-Z]+\s+Tbk)",  # PT Name Tbk
        ]

        # Common Indonesian stock patterns
        common_tickers = [
            "GRPM",
            "PMUI",
            "MDRN",
            "KREN",
            "FAST",
            "KOTA",
            "ADRO",
            "KBAG",
            "BBCA",
            "BBRI",
            "BMRI",
            "TLKM",
            "ASII",
            "UNVR",
            "HMSP",
            "PGNO",
            "INKP",
            "SMGR",
            "PATY",
            "ACES",
            "PLNN",
            "MITI",
            "LPKR",
            "BNLI",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                if match in common_tickers:
                    logger.info(f"Extracted ticker: {match} from analysis")
                    return match

        # Try to find PT Name Tbk pattern
        pt_match = re.search(r"PT\s+([A-Za-z]+)\s+Tbk", combined)
        if pt_match:
            name = pt_match.group(1).upper()[:4]
            logger.info(f"Extracted ticker: {name} from PT name")
            return name

        return "UNKNOWN"

    def analyze_batch(self, announcements: list[dict]) -> list[dict]:
        """Analyze multiple announcements with rate limiting."""
        results = []

        for i, announcement in enumerate(announcements):
            logger.info(f"Processing {i + 1}/{len(announcements)}...")
            result = self.analyze(announcement)
            results.append(result)

            if i < len(announcements) - 1:
                time.sleep(1)

        return results

    def _build_prompt(self, announcement_data: dict) -> str:
        """Build the analysis prompt for the LLM."""
        return f"""
Please analyze the following IDX announcement and provide your expert assessment in BAHASA INDONESIA:

**Company Ticker:** {announcement_data["ticker"]}
**Announcement Title:** {announcement_data["title"]}
**Date:** {announcement_data["date"]}
**Source:** {announcement_data["pdf_url"]}

**Announcement Content:**
{announcement_data["content"][:5000]}  # Limit to first 5000 chars to manage token usage

**Please provide in BAHASA INDONESIA:**
1. Summary of the announcement
2. Key financial/corporate implications
3. Sentiment assessment (POSITIVE/NEGATIVE/NEUTRAL)
4. Expected investor impact level (HIGH/MEDIUM/LOW)
5. Recommended investor action or attention points
"""
