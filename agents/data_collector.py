import asyncio
import logging
import os
import io
from datetime import datetime
from scrapling.fetchers import AsyncStealthySession
import fitz  # PyMuPDF
import httpx
import urllib.parse
from typing import Optional, Tuple

from config.settings import IDX_BASE_URL, OUTPUT_DIR, RAW_DIR, MONGO_URI

try:
    from pymongo import MongoClient

    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log MongoDB configuration status on module load
if MONGO_URI:
    logger.info(f"MongoDB configured: URI present ({len(MONGO_URI)} chars)")
    if MONGO_AVAILABLE:
        logger.info("MongoDB: pymongo available - auto-ingestion enabled")
    else:
        logger.warning("MongoDB: pymongo NOT installed - auto-ingestion disabled")
else:
    logger.info("MongoDB: MONGO_URI not set - auto-ingestion disabled")

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
        logger.info("Starting Data Collector Agent with Scrapling StealthyFetcher...")

        # Prepare debug file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(DEBUG_DIR, f"page_initial_{timestamp}.png")
        html_path = os.path.join(DEBUG_DIR, f"page_initial_{timestamp}.html")

        # Page action to capture screenshot before page closes
        async def debug_page_action(page):
            """Capture screenshot for debugging."""
            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")

        async with AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            block_webrtc=True,
            hide_canvas=True,
            block_ads=True,
            timeout=120000,
            network_idle=True,
            load_dom=True,
            real_chrome=True,
            locale="en-US",
            timezone_id="Asia/Jakarta",
            retries=3,
            retry_delay=2,
        ) as session:
            logger.info(f"Navigating to {IDX_BASE_URL}")
            response = await session.fetch(
                IDX_BASE_URL,
                wait_selector="table tbody tr, .listing-item, .announcement-item",
                timeout=120000,
                wait=5000,  # Wait 5s after page load for JS to finish
            )

            logger.info(f"Response status: {response.status}")

            # Dump HTML from response body
            html_content = response.text
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML dump saved: {html_path} ({len(html_content)} bytes)")

            # Get page title
            title_text = response.css('title::text').get()
            if title_text:
                logger.info(f"Page title: {title_text}")

            # Diagnose page structure
            await self._diagnose_page_structure(response)

            # Collect today's announcements
            announcements = await self._collect_todays_announcements(response)
            logger.info(f"Found {len(announcements)} announcements for today")

            # Parse PDFs
            parsed_data = []

            # Build cookie dict from the browser context to include all cookies
            try:
                cookies_list = await session.context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies_list if 'name' in c and 'value' in c}
            except Exception as e:
                logger.warning(f"Could not get context cookies: {e}, falling back to response cookies")
                cookie_dict = {}
                for cookie in response.cookies:
                    if isinstance(cookie, dict):
                        name = cookie.get('name')
                        value = cookie.get('value')
                        if name and value:
                            cookie_dict[name] = value

            origin_url = response.url
            logger.info(f"Got {len(cookie_dict)} cookies from browser session")
            logger.info(f"Cookie names: {list(cookie_dict.keys())}")

            # Create raw PDF directory for today
            raw_pdf_dir = get_raw_pdf_dir()

            # Process each announcement (limit to first 1 for debugging)
            for ann in announcements[:1]:
                try:
                    logger.info(f"Processing: {ann['title'][:50]}")

                    content_parts = []
                    pdf_saved = False
                    txt_path = None

                    # Get all PDF URLs for this announcement
                    all_pdf_urls = ann.get(
                        "all_pdf_urls",
                        [ann["pdf_url"]] if ann.get("pdf_url") else [],
                    )

                    if not all_pdf_urls:
                        logger.warning(
                            f"No PDF URLs for announcement: {ann['title']}"
                        )
                        ann["content"] = (
                            f"Title: {ann['title']}\nTicker: {ann['ticker']}\nDate: {ann['date']}"
                        )
                        ann["pdf_saved"] = False
                        ann["pdf_path"] = None
                        parsed_data.append(ann)
                        continue

                    # Download and extract text from ALL PDFs
                    for pdf_idx, pdf_url in enumerate(all_pdf_urls):
                        logger.info(
                            f"  Downloading PDF {pdf_idx + 1}/{len(all_pdf_urls)}: {urllib.parse.urlparse(pdf_url).path}"
                        )

                        # Download PDF using Scrapling session (byasses 403)
                        try:
                            pdf_response = await session.fetch(
                                pdf_url,
                                network_idle=False,
                                load_dom=False,
                                wait_selector=None,
                                timeout=60000,
                                google_search=False,
                                extra_headers={'Referer': origin_url},
                            )

                            # Validate PDF magic bytes
                            if pdf_data[:5] == b'%PDF-':
                                logger.info(f"PDF downloaded successfully via Scrapling")
                            else:
                                # Show first 200 chars of HTML for debugging
                                snippet = pdf_data[:500].decode('utf-8', errors='replace')
                                logger.warning(f"Downloaded content not a PDF (starts with: {snippet})")
                                pdf_data = b""
                        except Exception as e:
                            logger.warning(f"Scrapling PDF fetch failed: {e}")
                            pdf_data = b""

                        if pdf_data and len(pdf_data) > 100:
                            pdf_buffer = io.BytesIO(pdf_data)
                            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
                            for page_idx, page_doc in enumerate(doc):
                                page_text = page_doc.get_text()
                                if page_text.strip():
                                    content_parts.append(
                                        f"--- PDF {pdf_idx + 1}, Page {page_idx + 1} ---\n"
                                    )
                                    content_parts.append(page_text)
                            doc.close()
                            logger.info(
                                f"  Extracted PDF {pdf_idx + 1}: {len(content_parts)} chars accumulated"
                            )
                        else:
                            logger.warning(
                                f"  Failed to download PDF {pdf_idx + 1}: {urllib.parse.urlparse(pdf_url).path}"
                            )

                    combined_content = "\n\n".join(content_parts) if content_parts else ""

                    if combined_content:
                        safe_title = "".join(
                            c for c in ann["title"] if c.isalnum() or c in " -_"
                        ).strip()[:50]
                        txt_filename = f"{ann['ticker']}_{ann['date']}_{safe_title}.txt"
                        txt_path = os.path.join(raw_pdf_dir, txt_filename)

                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(combined_content)
                        pdf_saved = True
                        logger.info(
                            f"Saved combined TXT: {txt_filename} ({len(combined_content)} chars from {len(all_pdf_urls)} PDFs)"
                        )
                        ann["content"] = combined_content
                    else:
                        logger.warning(
                            f"  No content extracted from any PDF for {ann['ticker']}"
                        )
                        ann["content"] = (
                            f"Title: {ann['title']}\nTicker: {ann['ticker']}\nDate: {ann['date']}"
                        )

                    ann["pdf_saved"] = pdf_saved
                    ann["pdf_path"] = txt_path if pdf_saved else None

                    parsed_data.append(ann)
                    logger.info(f"Added: {ann['ticker']}")

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing {ann['title'][:30]}: {e}")
                    ann["content"] = (
                        f"Title: {ann['title']}\nTicker: {ann['ticker']}\nDate: {ann['date']}"
                    )
                    ann["pdf_saved"] = False
                    ann["pdf_path"] = None
                    parsed_data.append(ann)
                    continue

            saved_count = len([a for a in parsed_data if a.get("pdf_saved")])
            logger.info(f"Saved {saved_count} TXT files to {raw_pdf_dir}")

            # MongoDB ingestion
            if MONGO_AVAILABLE and MONGO_URI:
                try:
                    logger.info(f"Attempting MongoDB ingestion: {len(parsed_data)} documents")
                    client = MongoClient(
                        MONGO_URI,
                        connect=False,
                        maxPoolSize=1,
                        connectTimeoutMS=30000,
                        socketTimeoutMS=30000,
                        retryWrites=True,
                        serverSelectionTimeoutMS=30000,
                    )
                    db = client["idx_news"]
                    collection = db["Daily_News"]
                    if parsed_data:
                        result = collection.insert_many(parsed_data)
                        logger.info(
                            f"✓ Inserted {len(result.inserted_ids)} docs into MongoDB (db: idx_news, collection: Daily_News)"
                        )
                    else:
                        logger.warning("No data to ingest")
                    client.close()
                except Exception as db_err:
                    logger.error(f"MongoDB ingestion failed: {db_err}")
            elif MONGO_URI and not MONGO_AVAILABLE:
                logger.warning("MongoDB ingestion skipped: pymongo not installed")
            elif not MONGO_URI:
                logger.info("MongoDB ingestion skipped: MONGO_URI not configured")

            return parsed_data

    async def _collect_using_base_selector(
        self, response, today_iso: str, today_day: str
    ) -> list[dict]:
        """Collect announcements using the known base container element provided by user."""
        logger.info("Trying base selector strategy...")

        announcements = []

        # Base selector: containers that wrap each announcement
        # Use attribute selectors for classes with double hyphens to avoid CSS parsing errors
        base_selector = (
            "#app "
            "div[class~='sticky-footer-container-item'][class~='--pushed'] "
            "main "
            "div.tab-content.disclosure-tab "
            "div:nth-child(2) div > div"
        )

        try:
            containers = response.css(base_selector)
        except Exception as e:
            logger.warning(f"Base selector syntax error: {e}, skipping base strategy")
            return []

        logger.info(f"Base selector found {len(containers)} containers")

        for idx, container in enumerate(containers):
            try:
                # Extract ticker from h6 element within container
                h6_text = container.css("h6::text").get()
                if not h6_text:
                    logger.debug(f"Container {idx}: no h6 element, skipping")
                    continue

                ticker = self._extract_ticker(h6_text)

                # Gather ALL PDF links within this container
                pdf_links = container.css('a[href$=".pdf"]')
                all_pdf_urls = []

                for link in pdf_links:
                    pdf_url = link.attrib.get('href')
                    if pdf_url:
                        all_pdf_urls.append(pdf_url)

                if not all_pdf_urls:
                    logger.debug(f"Container {idx}: no PDF links found, skipping")
                    continue

                # Title from h6 text (clean it)
                title = h6_text.strip()

                # Date verification: check if container text contains today's day
                container_text = container.get()
                if today_day not in container_text:
                    logger.debug(
                        f"Container {idx}: date mismatch (no '{today_day}'), skipping"
                    )
                    continue

                announcements.append(
                    {
                        "ticker": ticker,
                        "title": title,
                        "date": today_iso,
                        "pdf_url": all_pdf_urls[0],  # First PDF for backward compatibility
                        "all_pdf_urls": all_pdf_urls,  # Complete list of all PDFs
                        "content": "",
                    }
                )

                logger.info(
                    f"Base selector found: {ticker} - {title[:50]} ({len(all_pdf_urls)} PDFs)"
                )

            except Exception as e:
                logger.warning(f"Error processing base selector container {idx}: {e}")
                continue

        return announcements

    async def _diagnose_page_structure(self, response) -> None:
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
                elements = response.css(selector)
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
            elements = response.css(selector)
            if elements:
                logger.info(f"Found date input: {selector}")

        # Check for "Load More" or pagination buttons (simple text matching)
        load_more_buttons = response.xpath("//button[contains(., 'Load More') or contains(., 'Muat Lain')]")
        if load_more_buttons:
            logger.info("Found 'Load More' button - page uses pagination")

        logger.info("=== End diagnosis ===")

    async def _collect_todays_announcements(self, response) -> list[dict]:
        """Scrape today's announcements from the IDX page."""
        today = datetime.now()
        today_day = today.strftime("%d")  # Day: "16"
        today_month = today.strftime("%m")  # Month: "04"
        today_year = today.strftime("%Y")  # Year: "2026"
        today_iso = today.strftime("%Y-%m-%d")

        # Common date formats on IDX: "16 Apr 2026", "16/04/2026", "16-04-2026", "2026-04-16"
        today_str = today.strftime("%d %b %Y")  # "16 Apr 2026"

        announcements = []

        rows = response.css("table tbody tr")
        cell_selector = "td"

        for i, row in enumerate(rows):
            try:
                # Try to extract date, company, and ALL PDF links from the row
                date_text = ""
                company_text = ""
                title = ""
                all_pdf_urls = []

                # Get all cells in the row
                cells = row.css(cell_selector)

                for cell_idx, cell in enumerate(cells[:4]):  # Check first 4 cells
                    cell_text = cell.get()

                    # Check if this cell contains PDF links - collect ALL in this cell
                    cell_pdf_links = cell.css('a[href$=".pdf"]')
                    for link in cell_pdf_links:
                        pdf_url = link.attrib.get('href')
                        if pdf_url:
                            all_pdf_urls.append(pdf_url)
                            # Use first link's text as title if not already set
                            if not title:
                                link_text = link.get().strip()
                                title = link_text or cell_text

                    # Check if this cell contains a date
                    if (
                        any(char.isdigit() for char in cell_text)
                        and len(cell_text) < 20
                    ):
                        if today_day in cell_text:
                            date_text = cell_text
                            break  # Assume first match is date

                # If no PDFs found in cells, search whole row for ALL links
                if not all_pdf_urls:
                    row_pdf_links = row.css('a[href$=".pdf"]')
                    for link in row_pdf_links:
                        pdf_url = link.attrib.get('href')
                        if pdf_url:
                            all_pdf_urls.append(pdf_url)
                            if not title:
                                title = link.get().strip()

                if not all_pdf_urls:
                    continue

                # Use second cell as company if available
                if len(cells) >= 2:
                    company_text = cells[1].get()

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
                    row_text = row.get()
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
                            "pdf_url": all_pdf_urls[0],  # First PDF for backward compatibility
                            "all_pdf_urls": all_pdf_urls,  # All PDFs list
                            "content": "",
                        }
                    )
                    logger.info(
                        f"Found announcement: {ticker} - {title[:50]} ({len(all_pdf_urls)} PDFs)"
                    )

            except Exception as e:
                logger.warning(f"Error processing row {i}: {e}")
                continue

        # If no date-specific matches, fall back to collecting all PDFs
        if not announcements:
            logger.info("No date-specific matches found, falling back to all PDFs")
            return await self._fallback_collect_pdfs(response, today_iso)

        return announcements

    async def _fallback_collect_pdfs(self, response, today_iso: str) -> list[dict]:
        """Fallback: collect all PDF links on page with today's date context."""
        logger.info("Attempting fallback PDF collection...")

        announcements = []
        pdf_elements = response.css('a[href$=".pdf"]')

        for link in pdf_elements:
            try:
                pdf_url = link.attrib.get('href')
                title = link.get().strip() if link else ""

                # Check parent context for date
                parent = link.parent
                parent_text = parent.get() if parent else ""

                # Extract potential date from context
                today_day = datetime.now().strftime("%d")
                if today_day in parent_text:
                    announcements.append(
                        {
                            "ticker": "UNKNOWN",
                            "title": title if title else "PDF Announcement",
                            "date": today_iso,
                            "pdf_url": pdf_url,
                            "all_pdf_urls": [pdf_url],  # Single-item list
                            "content": "",
                        }
                    )
            except Exception as e:
                logger.warning(f"Error processing PDF link: {e}")

        if not announcements:
            # Last resort: collect all PDFs
            logger.warning("No date context found, collecting all PDFs")
            for link in pdf_elements:
                pdf_url = link.attrib.get('href')
                title = link.get().strip() if link else ""
                announcements.append(
                    {
                        "ticker": "UNKNOWN",
                        "title": title if title else "PDF Announcement",
                        "date": today_iso,
                        "pdf_url": pdf_url,
                        "all_pdf_urls": [pdf_url],  # Single-item list
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
        """Extract stock ticker from announcement title using bracket or parentheses pattern."""
        import re

        if not company_text:
            return "UNKNOWN"

        # IDX format: "Title [TICKER" (brackets with optional trailing space)
        # Examples: "[SKRN ]", "[MINE ]", "[ADRO]"
        bracket_match = re.search(r"\[([A-Z]{3,4})\s?\]", company_text)
        if bracket_match:
            return bracket_match.group(1)

        # Fallback: parentheses pattern "(TICKER)"
        paren_match = re.search(r"\(([A-Z]{3,4})\)", company_text)
        if paren_match:
            return paren_match.group(1)

        # Fallback: standalone uppercase 3-4 letter word
        word_match = re.search(r"\b([A-Z]{3,4})\b", company_text)
        if word_match:
            return word_match.group(1)

        # Last resort: first 10 characters
        return company_text.strip()[:10] if company_text else "UNKNOWN"

    async def _download_pdf_with_cookies(
        self, pdf_url: str, cookies: dict, origin_url: str
    ) -> tuple[bool, bytes]:
        """Download PDF using httpx with browser cookies passed from session."""
        # Use httpx with the cookies from Scrapling session
        # Scrapling already handled Cloudflare on the main page, cookies are valid
        max_retries = 5

        # Comprehensive user agents to rotate through
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        ]

        # Base headers that mimic real browser requests
        base_headers = {
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
        }

        for attempt in range(max_retries):
            try:
                # Rotate user agent per attempt
                current_ua = user_agents[attempt % len(user_agents)]
                headers = base_headers.copy()
                headers["User-Agent"] = current_ua
                headers["Referer"] = origin_url

                logger.debug(f"PDF download attempt {attempt + 1}/{max_retries} with UA: {current_ua[:50]}...")

                # Try with cookies from Scrapling session
                async with httpx.AsyncClient(
                    cookies=cookies,
                    headers=headers,
                    follow_redirects=True,
                    timeout=45.0,
                ) as client:
                    response = await client.get(pdf_url)

                    if response.status_code == 200:
                        # Validate it's actually a PDF
                        content_start = response.content[:200]
                        if b"%PDF" in content_start or b"PDF" in content_start:
                            logger.info(f"PDF downloaded successfully on attempt {attempt + 1}")
                            return True, response.content
                        else:
                            logger.warning(f"Response not a PDF (starts with: {content_start[:50]})")
                            return False, b""

                    elif response.status_code == 403:
                        logger.debug(f"403 Forbidden on attempt {attempt + 1}, retrying...")
                        # Wait longer before retry
                        if attempt < max_retries - 1:
                            await asyncio.sleep(5 * (2 ** attempt))
                        continue

                    elif response.status_code == 429:
                        # Rate limited - wait longer
                        wait_time = 5 * (2 ** attempt)
                        logger.warning(f"Rate limited (429), waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(3)

            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}: {urllib.parse.urlparse(pdf_url).path}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue

            except Exception as e:
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue

        # All attempts failed
        logger.error(f"All {max_retries} download attempts failed for {urllib.parse.urlparse(pdf_url).path}")
        return False, b""
