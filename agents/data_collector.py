import asyncio
import logging
import os
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth as stealth_module
import fitz  # PyMuPDF
import httpx
import urllib.parse

from config.settings import IDX_BASE_URL, OUTPUT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug directory for screenshots and HTML dumps
DEBUG_DIR = os.path.join(OUTPUT_DIR, "_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)


class DataCollectorAgent:
    """Agent responsible for collecting and parsing IDX announcements."""

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    async def run(self) -> list[dict]:
        """Main execution: browse IDX, collect today's announcements, parse PDFs."""
        logger.info("Starting Data Collector Agent...")

        # Use playwright-stealth to bypass Cloudflare anti-bot protection
        stealth = stealth_module.Stealth(
            navigator_webdriver=True,  # Hide webdriver property
            navigator_plugins=True,  # Hide plugins
            navigator_permissions=True,  # Hide permissions
        )

        async with stealth.use_async(async_playwright()) as p:
            # Launch browser with stealth
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            page = await browser.new_page()

            # Set realistic viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})

            try:
                # Navigate to IDX disclosure page
                logger.info(f"Navigating to {IDX_BASE_URL}")
                await page.goto(IDX_BASE_URL, wait_until="networkidle", timeout=60000)

                # Check for Cloudflare challenge page
                title = await page.title()
                if "cloudflare" in title.lower() or "attention" in title.lower():
                    logger.warning(
                        "Cloudflare challenge detected, waiting for resolution..."
                    )
                    # Wait for Cloudflare challenge to complete (max 30 seconds)
                    for _ in range(30):
                        await page.wait_for_timeout(1000)
                        title = await page.title()
                        if (
                            "cloudflare" not in title.lower()
                            and "attention" not in title.lower()
                        ):
                            logger.info("Cloudflare challenge passed")
                            break
                    else:
                        logger.error("Cloudflare challenge not resolved after 30s")

                # Wait for dynamic content (table rows) to load
                # IDX uses JavaScript to render announcements, need to wait for them
                logger.info("Waiting for table content to render...")
                await page.wait_for_timeout(5000)  # Extended wait for JS rendering

                # Save initial page state for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(
                    DEBUG_DIR, f"page_initial_{timestamp}.png"
                )
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")

                # Dump HTML for analysis (first 50KB to avoid huge files)
                html_path = os.path.join(DEBUG_DIR, f"page_initial_{timestamp}.html")
                html_content = await page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content[:50000])  # First 50KB
                logger.info(f"HTML dump saved: {html_path} ({len(html_content)} bytes)")

                # Log page title and URL for verification
                title = await page.title()
                logger.info(f"Page title: {title}")

                # Try multiple selectors to find announcement tables
                await self._diagnose_page_structure(page)

                # Collect today's announcements
                announcements = await self._collect_todays_announcements(page)
                logger.info(f"Found {len(announcements)} announcements for today")

                # Get cookies from the main page to use in HTTP requests
                cookies = await page.context.cookies()
                cookie_header = "; ".join(
                    [f"{c['name']}={c['value']}" for c in cookies]
                )

                # Parse PDFs using cookies from browser session
                parsed_data = await self._parse_with_cookies(
                    announcements, cookie_header
                )

                return parsed_data

            except Exception as e:
                logger.error(f"Error in data collection: {e}")
                raise
            finally:
                await browser.close()

    async def _diagnose_page_structure(self, page) -> None:
        """Diagnose what selectors work on the current page structure."""
        logger.info("=== Diagnosing page structure ===")

        # Try different selectors and log results
        selector_tests = [
            ("table tbody tr", "Standard table rows"),
            ("table tr", "Any table row"),
            (".listing-item", "Listing items"),
            (".announcement-item", "Announcement items"),
            ("[data-testid*='announcement']", "Data testid pattern"),
            (".MuiTableRow-root", "Material UI table rows"),
            (".MuiDataTableRow-root", "Material UI DataTable"),
            (".jsx-", "React JSX classes pattern"),
            ("div[class*='row']", "Div rows pattern"),
            ("ul.listing li", "Listing list items"),
        ]

        for selector, description in selector_tests:
            try:
                elements = await page.query_selector_all(selector)
                logger.info(
                    f"Selector '{selector}' ({description}): found {len(elements)} elements"
                )
            except Exception as e:
                logger.warning(f"Selector '{selector}' error: {e}")

        # Check for common date input patterns
        date_selectors = [
            "input[type='date']",
            "input[placeholder*='date']",
            "input[name*='date']",
            ".date-picker",
            "input[class*='date']",
        ]

        for selector in date_selectors:
            element = await page.query_selector(selector)
            if element:
                logger.info(f"Found date input: {selector}")

        # Check for "Load More" or pagination buttons
        load_more = (
            await page.query_selector("button:has-text('Load More')")
            or await page.query_selector("button:has-text('Muat Lain')")
            or await page.query_selector("[aria-label*='load']")
        )
        if load_more:
            logger.info("Found 'Load More' button - page uses pagination")

        logger.info("=== End diagnosis ===")

    async def _collect_todays_announcements(self, page) -> list[dict]:
        """Scrape today's announcements from the IDX page."""
        today = datetime.now()
        today_day = today.strftime("%d")  # Day: "16"
        today_month = today.strftime("%m")  # Month: "04"
        today_year = today.strftime("%Y")  # Year: "2026"
        today_iso = today.strftime("%Y-%m-%d")

        # Common date formats on IDX: "16 Apr 2026", "16/04/2026", "16-04-2026", "2026-04-16"
        today_str = today.strftime("%d %b %Y")  # "16 Apr 2026"

        announcements = []

        # Try multiple selector strategies for table rows
        selector_strategies = [
            ("table tbody tr", "td", "Standard table"),
            ("table tr", "td", "Any table row"),
            (".listing-item", "div", "Listing item"),
            (".MuiTableRow-root", "td", "Material UI table"),
            (".announcement-row", "div", "Announcement row"),
            ("div[class*='row']", "div", "Div row pattern"),
        ]

        rows = []
        used_selector = None
        cell_selector = None

        for selector, cell_sel, description in selector_strategies:
            rows = await page.query_selector_all(selector)
            logger.info(f"Trying '{selector}' ({description}): found {len(rows)} rows")
            if rows:
                used_selector = selector
                cell_selector = cell_sel
                break

        if not rows:
            logger.warning("No table rows found with any selector strategy")
            # Fallback: Try to get all PDF links on the page
            return await self._fallback_collect_pdfs(page, today_iso)

        for i, row in enumerate(rows):
            try:
                # Try to extract date, company, and PDF link from various cell positions
                # Try first 3 cells for date
                date_text = ""
                company_text = ""
                pdf_url = ""
                title = ""

                # Get all cells in the row
                cells = await row.query_selector_all(cell_selector)

                for cell_idx, cell in enumerate(cells[:4]):  # Check first 4 cells
                    cell_text = await cell.inner_text()

                    # Check if this cell contains a PDF link
                    link_elem = await cell.query_selector("a[href$='.pdf']")
                    if link_elem:
                        pdf_url = await link_elem.get_attribute("href")
                        title = (await link_elem.inner_text()).strip() or cell_text

                    # Check if this cell contains a date
                    # Date typically contains day number and month/year
                    if (
                        any(char.isdigit() for char in cell_text)
                        and len(cell_text) < 20
                    ):
                        if today_day in cell_text:
                            date_text = cell_text
                            break  # Assume first match is date

                # If no PDF link found in cells, search whole row
                if not pdf_url:
                    link_elem = await row.query_selector("a[href$='.pdf']")
                    if link_elem:
                        pdf_url = await link_elem.get_attribute("href")
                        title = (await link_elem.inner_text()).strip()

                if not pdf_url:
                    continue

                # Use second cell as company if available
                if len(cells) >= 2:
                    company_text = await cells[1].inner_text()

                # Check if date matches today more robustly
                date_matches = (
                    today_day in date_text
                    or today_iso in date_text
                    or (
                        today_day in company_text
                        and any(
                            m in company_text.lower()
                            for m in [
                                "jan",
                                "feb",
                                "mar",
                                "apr",
                                "may",
                                "jun",
                                "jul",
                                "aug",
                                "sep",
                                "oct",
                                "nov",
                                "dec",
                            ]
                        )
                    )
                )

                if not date_matches and date_text:
                    # Also check row's text content for today's date
                    row_text = await row.inner_text()
                    if today_day in row_text and (
                        today_year in row_text or today_str.split()[1] in row_text
                    ):
                        date_matches = True

                if date_matches:
                    ticker = self._extract_ticker(company_text or title)

                    announcements.append(
                        {
                            "ticker": ticker,
                            "title": title.strip(),
                            "date": today_iso,
                            "pdf_url": pdf_url,
                            "content": "",
                        }
                    )
                    logger.info(f"Found announcement: {ticker} - {title[:50]}")

            except Exception as e:
                logger.warning(f"Error processing row {i}: {e}")
                continue

        # If no date-specific matches, fall back to collecting all PDFs
        if not announcements:
            logger.info("No date-specific matches found, falling back to all PDFs")
            return await self._fallback_collect_pdfs(page, today_iso)

        return announcements

    async def _fallback_collect_pdfs(self, page, today_iso: str) -> list[dict]:
        """Fallback: collect all PDF links on page with today's date context."""
        logger.info("Attempting fallback PDF collection...")

        announcements = []
        pdf_links = await page.query_selector_all("a[href$='.pdf']")

        for link in pdf_links:
            try:
                pdf_url = await link.get_attribute("href")
                title = (await link.inner_text()).strip() if link else ""

                # Check parent context for date
                parent = await page.evaluate("""(el) => el && el.parentElement""", link)
                parent_text = parent.inner_text() if parent else ""

                # Extract potential date from context
                today_day = datetime.now().strftime("%d")
                if today_day in parent_text:
                    announcements.append(
                        {
                            "ticker": "UNKNOWN",
                            "title": title if title else "PDF Announcement",
                            "date": today_iso,
                            "pdf_url": pdf_url,
                            "content": "",
                        }
                    )
            except Exception as e:
                logger.warning(f"Error processing PDF link: {e}")

        if not announcements:
            # Last resort: collect all PDFs
            logger.warning("No date context found, collecting all PDFs")
            for link in pdf_links:
                pdf_url = await link.get_attribute("href")
                title = (await link.inner_text()).strip() if link else ""
                announcements.append(
                    {
                        "ticker": "UNKNOWN",
                        "title": title if title else "PDF Announcement",
                        "date": today_iso,
                        "pdf_url": pdf_url,
                        "content": "",
                    }
                )

        return announcements

    async def _parse_with_cookies(
        self, announcements: list[dict], cookie_header: str
    ) -> list[dict]:
        """Download PDFs using cookies from browser session."""
        parsed_data = []

        async with httpx.AsyncClient(
            timeout=30, headers={"Cookie": cookie_header}
        ) as client:
            for ann in announcements:
                try:
                    logger.info(f"Downloading PDF: {ann['pdf_url']}")
                    response = await client.get(ann["pdf_url"])

                    if response.status_code == 200:
                        pdf_path = os.path.join(
                            self.output_dir,
                            f"{ann['ticker']}_{ann['date'].replace('-', '')}.pdf",
                        )
                        with open(pdf_path, "wb") as f:
                            f.write(response.content)

                        text = self._extract_text_from_pdf(pdf_path)
                        ann["content"] = text

                        parsed_data.append(ann)
                        logger.info(f"Successfully parsed: {ann['ticker']}")
                    else:
                        logger.warning(
                            f"Failed to download PDF: {ann['pdf_url']} (status: {response.status_code})"
                        )

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
        match = re.search(r"\(([A-Z]{3,4})\)", company_text)
        if match:
            return match.group(1)

        # Fallback: use first few characters or full text
        return company_text.strip()[:10]
