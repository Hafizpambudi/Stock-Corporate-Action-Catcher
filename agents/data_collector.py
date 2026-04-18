import asyncio
import logging
import os
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth as stealth_module
import fitz  # PyMuPDF
import httpx
import urllib.parse

from config.settings import IDX_BASE_URL, OUTPUT_DIR, RAW_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug directory for screenshots and HTML dumps
DEBUG_DIR = os.path.join(OUTPUT_DIR, "_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)


# Raw PDF storage directory - created dynamically per run
def get_raw_pdf_dir() -> str:
    """Create and return the raw PDF directory for today."""
    raw_dir = os.path.join(RAW_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(raw_dir, exist_ok=True)
    return raw_dir


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
                await page.goto(
                    IDX_BASE_URL, wait_until="domcontentloaded", timeout=120000
                )

                # Check for Cloudflare challenge page
                title = await page.title()
                if "cloudflare" in title.lower() or "attention" in title.lower():
                    logger.warning(
                        "Cloudflare challenge detected, waiting for resolution..."
                    )
                    # Wait for Cloudflare challenge to complete (max 2 minutes)
                    for _ in range(120):
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

                # Parse PDFs and save to raw directory using httpx with browser cookies
                parsed_data = []

                # Get browser cookies for authenticated PDF downloads
                browser_context = page.context
                cookies = await browser_context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in cookies}

                # Get origin URL for referer
                origin_url = page.url

                logger.info(f"Got {len(cookie_dict)} cookies from browser session")
                logger.info(f"Cookie names: {list(cookie_dict.keys())}")

                # Create raw PDF directory for today
                raw_pdf_dir = get_raw_pdf_dir()

                # Process each announcement
                for ann in announcements:
                    try:
                        logger.info(f"Processing: {ann['title'][:50]}")

                        content = ""
                        pdf_saved = False
                        pdf_path = None

                        # Download PDF using httpx with browser cookies and proper headers
                        pdf_url = ann["pdf_url"]
                        success, pdf_data = await self._download_pdf_with_cookies(
                            pdf_url, cookie_dict, origin_url
                        )

                        if success and pdf_data and len(pdf_data) > 100:
                            # Save as .txt with safe filename
                            safe_title = "".join(
                                c for c in ann["title"] if c.isalnum() or c in " -_"
                            ).strip()[:50]
                            txt_filename = (
                                f"{ann['ticker']}_{ann['date']}_{safe_title}.txt"
                            )
                            txt_path = os.path.join(raw_pdf_dir, txt_filename)

                            # Extract text from PDF
                            import fitz
                            import io

                            pdf_buffer = io.BytesIO(pdf_data)
                            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
                            content = ""
                            for page in doc:
                                content += page.get_text()
                            doc.close()

                            # Save as .txt
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write(content)
                            pdf_saved = True
                            logger.info(
                                f"Saved TXT: {txt_filename} ({len(content)} chars)"
                            )
                        else:
                            logger.warning(
                                f"Failed to download PDF: {ann['pdf_url'][-50:]}"
                            )

                        ann["content"] = (
                            content
                            if content
                            else f"Title: {ann['title']}\nTicker: {ann['ticker']}\nDate: {ann['date']}"
                        )
                        ann["pdf_saved"] = pdf_saved
                        ann["pdf_path"] = txt_path if pdf_saved else None

                        parsed_data.append(ann)
                        logger.info(f"Added: {ann['ticker']}")

                        # Brief delay to avoid rate limiting
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error processing {ann['title'][:30]}: {e}")
                        ann["content"] = (
                            f"Title: {ann['title']}\nTicker: {ann['ticker']}\nDate: {ann['date']}"
                        )
                        ann["pdf_saved"] = False
                        parsed_data.append(ann)
                        continue

                saved_count = len([a for a in parsed_data if a.get("pdf_saved")])
                logger.info(f"Saved {saved_count} TXT files to {raw_pdf_dir}")

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

    async def _parse_by_clicking(self, announcements: list[dict], page) -> list[dict]:
        """Download PDFs by clicking on PDF links within the page context."""
        parsed_data = []

        # Get all PDF links from the page
        all_links = await page.query_selector_all("a[href$='.pdf']")

        # Create a mapping of URLs to elements
        link_map = {}
        for link in all_links:
            href = await link.get_attribute("href")
            if href:
                link_map[href] = link

        for ann in announcements:
            try:
                logger.info(f"Downloading PDF: {ann['pdf_url']}")

                # Check if this link exists on the page
                if ann["pdf_url"] in link_map:
                    link_element = link_map[ann["pdf_url"]]

                    # Get parent row/container to check if it's for today
                    parent = await link_element.evaluate("""(el) => {
                        let parent = el.closest('tr') || el.closest('div') || el.parentElement;
                        return parent ? parent.innerText : '';
                    }""")

                    # Check if the parent contains today's date
                    today = datetime.now().strftime("%d")
                    if today in parent:
                        # Click the link - this should navigate to/open the PDF
                        await link_element.click()

                        # Wait for navigation or new page
                        await page.wait_for_timeout(2000)

                        # Check if a new page was opened
                        if len(page.context.pages) > 1:
                            # Switch to the new page (the PDF)
                            pdf_page = page.context.pages[-1]

                            # Get the content
                            try:
                                content = await pdf_page.content()

                                # Check if it's a PDF (starts with %PDF)
                                if content.startswith("%PDF") or len(content) > 100:
                                    pdf_path = os.path.join(
                                        self.output_dir,
                                        f"{ann['ticker']}_{ann['date'].replace('-', '')}.pdf",
                                    )
                                    with open(pdf_path, "wb") as f:
                                        f.write(content.encode("latin-1"))

                                    text = self._extract_text_from_pdf(pdf_path)
                                    ann["content"] = text
                                    parsed_data.append(ann)
                                    logger.info(f"Successfully parsed: {ann['ticker']}")

                                    await pdf_page.close()
                                    continue
                            except Exception as e:
                                logger.warning(f"Error reading PDF page: {e}")
                                await pdf_page.close()

                        # Go back to main page
                        await page.go_back()
                        await page.wait_for_timeout(500)
                    else:
                        logger.warning(
                            f"PDF link not in today's announcements: {ann['pdf_url']}"
                        )
                else:
                    logger.warning(f"PDF link not found on page: {ann['pdf_url']}")

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

    async def _download_pdf_with_cookies(
        self, pdf_url: str, cookies: dict, origin_url: str
    ) -> tuple[bool, bytes]:
        """Download PDF using httpx with browser cookies and proper headers."""
        try:
            # Prepare headers to mimic browser request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": origin_url,
                "Origin": "https://www.idx.co.id",
            }

            async with httpx.AsyncClient(
                cookies=cookies,
                headers=headers,
                follow_redirects=True,
                timeout=30.0,
            ) as client:
                # First try with cookies
                response = await client.get(pdf_url)

                if response.status_code == 200 and b"%PDF" in response.content[:100]:
                    return True, response.content

                # If 403, try without auth cookies but with proper headers
                if response.status_code == 403:
                    logger.info(f"Got 403, retrying without auth cookies...")

                    # Simple headers without cookies
                    simple_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "application/pdf,*/*",
                        "Referer": "https://www.idx.co.id/",
                    }

                    async with httpx.AsyncClient(
                        headers=simple_headers,
                        follow_redirects=True,
                        timeout=30.0,
                    ) as simple_client:
                        response = await simple_client.get(pdf_url)
                        if response.status_code == 200:
                            return True, response.content

                logger.warning(
                    f"PDF download failed: {response.status_code} for {pdf_url[-40:]}"
                )
                return False, b""

        except httpx.TimeoutException:
            logger.warning(f"Timeout downloading PDF: {pdf_url[-40:]}")
            return False, b""
        except Exception as e:
            logger.warning(f"Error downloading PDF: {e}")
            return False, b""
