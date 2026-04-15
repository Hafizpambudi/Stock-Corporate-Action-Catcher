import json
import logging
import requests
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

Provide a detailed, professional analysis that helps investors understand the implications."""

    def __init__(self):
        self.api_url = f"{OPENROUTER_BASE_URL}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        self.model = OPENROUTER_MODEL

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

        try:
            response = requests.post(
                url=self.api_url,
                headers=self.headers,
                data=json.dumps({
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                })
            )

            response.raise_for_status()
            result = response.json()
            analysis_text = result['choices'][0]['message']['content'].strip()

            return {
                "Ticker": announcement_data['ticker'],
                "analysis": analysis_text,
                "source": announcement_data['pdf_url']
            }

        except Exception as e:
            logger.error(f"Error analyzing announcement: {e}")
            return {
                "Ticker": announcement_data['ticker'],
                "analysis": f"Error during analysis: {str(e)}",
                "source": announcement_data['pdf_url']
            }

    def analyze_batch(self, announcements: list[dict]) -> list[dict]:
        """
        Analyze multiple announcements.
        
        Args:
            announcements: List of announcement data dicts
            
        Returns:
            List of analysis results
        """
        results = []
        
        for announcement in announcements:
            result = self.analyze(announcement)
            results.append(result)
        
        return results

    def _build_prompt(self, announcement_data: dict) -> str:
        """Build the analysis prompt for the LLM."""
        return f"""
Please analyze the following IDX announcement and provide your expert assessment:

**Company Ticker:** {announcement_data['ticker']}
**Announcement Title:** {announcement_data['title']}
**Date:** {announcement_data['date']}
**Source:** {announcement_data['pdf_url']}

**Announcement Content:**
{announcement_data['content'][:5000]}  # Limit to first 5000 chars to manage token usage

**Please provide:**
1. Summary of the announcement
2. Key financial/corporate implications
3. Sentiment assessment (POSITIVE/NEGATIVE/NEUTRAL)
4. Expected investor impact level (HIGH/MEDIUM/LOW)
5. Recommended investor action or attention points
"""
