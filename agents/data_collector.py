import asyncio
import logging
import os
from datetime import datetime
from playwright.async_api import async_playwright
import fitz  # PyMuPDF
import httpx
import urllib.parse

from config.settings import IDX_BASE_URL, OUTPUT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollectorAgent:
    """Agent responsible for collecting and parsing IDX announcements."""

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    async def run(self) -> list[dict]:
        """Main execution: browse IDX, collect today's announcements, parse PDFs."""
        logger.info("Starting Data Collector Agent...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to IDX disclosure page
                logger.info(f"Navigating to {IDX_BASE_URL}")
                await page.goto(IDX_BASE_URL, wait_until="networkidle", timeout=60000)
                
                # Wait for content to load
                await page.wait_for_timeout(3000)
                
                # Collect today's announcements
                announcements = await self._collect_todays_announcements(page)
                logger.info(f"Found {len(announcements)} announcements for today")
                
                # Parse PDFs and extract content
                parsed_data = await self._parse_announcements(announcements)
                
                return parsed_data
                
            except Exception as e:
                logger.error(f"Error in data collection: {e}")
                raise
            finally:
                await browser.close()

    async def _collect_todays_announcements(self, page) -> list[dict]:
        """Scrape today's announcements from the IDX page."""
        today = datetime.now().strftime("%d %b %Y")  # Format: "14 Apr 2026"
        today_iso = datetime.now().strftime("%Y-%m-%d")
        
        announcements = []
        
        try:
            # Look for table rows or list items containing announcements
            # Adjust selectors based on actual IDX page structure
            rows = await page.query_selector_all("table tbody tr")
            
            if not rows:
                # Try alternative selectors
                rows = await page.query_selector_all(".listing-item") or \
                       await page.query_selector_all("tr")
            
            for row in rows:
                try:
                    # Extract date, company, and PDF link
                    # Note: Selectors need to be adjusted based on actual page structure
                    date_elem = await row.query_selector("td:nth-child(1)")
                    company_elem = await row.query_selector("td:nth-child(2)")
                    link_elem = await row.query_selector("a[href$='.pdf']")
                    
                    if not link_elem:
                        continue
                    
                    date_text = await date_elem.inner_text() if date_elem else ""
                    company_text = await company_elem.inner_text() if company_elem else ""
                    pdf_url = await link_elem.get_attribute("href")
                    title = await link_elem.inner_text()
                    
                    # Check if date matches today
                    if today.split()[0] in date_text or today_iso in date_text:
                        # Extract ticker from company name/code
                        ticker = self._extract_ticker(company_text)
                        
                        announcements.append({
                            "ticker": ticker,
                            "title": title.strip(),
                            "date": today_iso,
                            "pdf_url": pdf_url,
                            "content": ""
                        })
                        
                except Exception as e:
                    logger.warning(f"Error processing row: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping announcements: {e}")
            
            # Fallback: Try to get all PDF links on the page
            pdf_links = await page.query_selector_all("a[href$='.pdf']")
            for link in pdf_links:
                pdf_url = await link.get_attribute("href")
                title = await link.inner_text()
                
                announcements.append({
                    "ticker": "UNKNOWN",
                    "title": title.strip(),
                    "date": today_iso,
                    "pdf_url": pdf_url,
                    "content": ""
                })
        
        return announcements

    async def _parse_announcements(self, announcements: list[dict]) -> list[dict]:
        """Download and parse PDF content for each announcement."""
        parsed_data = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for ann in announcements:
                try:
                    logger.info(f"Downloading PDF: {ann['pdf_url']}")
                    response = await client.get(ann['pdf_url'])
                    
                    if response.status_code == 200:
                        # Save PDF temporarily
                        pdf_path = os.path.join(
                            self.output_dir, 
                            f"{ann['ticker']}_{ann['date'].replace('-', '')}.pdf"
                        )
                        with open(pdf_path, "wb") as f:
                            f.write(response.content)
                        
                        # Extract text from PDF
                        text = self._extract_text_from_pdf(pdf_path)
                        ann['content'] = text
                        
                        parsed_data.append(ann)
                        logger.info(f"Successfully parsed: {ann['ticker']}")
                    else:
                        logger.warning(f"Failed to download PDF: {ann['pdf_url']}")
                        
                except Exception as e:
                    logger.error(f"Error parsing PDF {ann['pdf_url']}: {e}")
                    continue
        
        return parsed_data

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file using PyMuPDF."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    def _extract_ticker(self, company_text: str) -> str:
        """Extract stock ticker from company name/code."""
        # Simple extraction - can be improved based on actual format
        # Look for common ticker patterns (usually 3-4 uppercase letters)
        import re
        
        # Try to find ticker in parentheses or brackets
        match = re.search(r'\(([A-Z]{3,4})\)', company_text)
        if match:
            return match.group(1)
        
        # Fallback: use first few characters or full text
        return company_text.strip()[:10]
