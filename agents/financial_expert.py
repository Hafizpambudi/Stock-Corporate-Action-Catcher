import json
import logging
import requests
import time
from datetime import datetime
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialExpertAgent:
    """Agent responsible for analyzing IDX announcements for sentiment and investor impact."""

    # Class-level configuration constants
    SHORT_THRESHOLD = 3000  # Use single-pass for content < 3000 chars
    MEDIUM_THRESHOLD = 10000  # Use sequential map for content 3000-10000 chars
    CHUNK_SIZE = 2000  # Target chunk size for processing
    CHUNK_OVERLAP = 200  # Overlap between chunks to preserve context

    # Rate limiting configuration (class-level for easy tuning)
    RPM_LIMIT = 20  # Free tier: 20 requests per minute
    DAILY_LIMIT = 50  # Free tier: 50 requests per day
    MIN_DELAY_SECONDS = 60 / RPM_LIMIT  # 3 seconds between requests

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

    # Prompt for analyzing individual chunks
    CHUNK_ANALYSIS_PROMPT = """Anda adalah analis keuangan yang menganalisis bagian-bagian dari pengumuman korporate.

    **Identitas Pengumuman:**
    - Ticker: {ticker}
    - Judul: {title}
    - Tanggal: {date}

    **Bagian Dokumen (Bagian {chunk_index} dari {total_chunks}):**
    {chunk_content}

    **Instruksi:**
    Kumpulkan dan analisis informasi kunci dari bagian ini saja. Fokus pada:
    1. Fakta finansial dan korporat utama yang ditemukan
    2. Angka atau data penting (revenue, profit, dll)
    3. Tindakan atau peristiwa bisnis yang signifikan
    4. Implikasipotensi untuk investor

    Berikan output dalam format JSON:
    {{
        "chunk_index": {chunk_index},
        "key_facts": ["facts utama 1", "facts utama 2", ...],
        "financial_data": {{"revenue": "...", "profit": "...", "other": "..."}},
        "sentiment_indicators": ["indikator positif/negatif/netral"],
        "business_events": ["event bisnis penting"],
        "investor_implications": ["implikasi untuk investor"],
        "confidence": "HIGH/MEDIUM/LOW"
    }}

    Jangan berikan analisis lengkap—hanya ekstraksi dan analisis bagian ini saja."""

    # Prompt for synthesizing multiple chunk analyses
    SYNTHESIS_PROMPT = """Anda adalah analis keuangan senior yang menyintesiskan analisis dari multiple bagian dokumen.

    **Identitas Pengumuman:**
    - Ticker: {ticker}
    - Judul: {title}
    - Tanggal: {date}

    **Ringkasan Analisis per Bagian:**
    {chunk_summaries}

    **Tugas Sintesis:**
    Berdasarkan semua analisis bagian di atas, buat satu analisis komprehensif yang koheren dan lengkap.
    Integrasikan insights dari semua bagian, hindari redundansi, dan buat narasi yang jelas.

    **Output yang diharapkan (dalam BAHASA INDONESIA):**
    1. Ringkasan eksekutif pengumuman
    2. Implikasi finansial dan korporat utama ( Gabungkan dari semua chunks )
    3. Penilaian sentiment keseluruhan (POSITIVE/NEGATIVE/NEUTRAL) dengan justifikasi
    4. Expected investor impact (HIGH/MEDIUM/LOW) dengan alasan
    5. Rekomendasi aksi untuk investor

    Berikan analisis yang profesional, faktual, dan berguna untuk keputusan investasi."""

    # Prompt for sequential map approach (carrying forward context)
    SEQUENTIAL_MAP_PROMPT = """Anda adalah analis keuangan yang menganalisis bagian dari dokumen panjang dengan konteks sebelumnya.

    **Identitas Pengumuman:**
    - Ticker: {ticker}
    - Judul: {title}
    - Tanggal: {date}

    **Bagian Saat Ini (Bagian {current_index} dari {total_chunks}):**
    {current_content}

    **Insights Penting dari Bagian Sebelumnya:**
    {previous_insights}

    **Tugas:**
    Analisis bagian ini sambil mempertimbangkan insights sebelumnya.identifikasi:
    1. Informasi baru yang belum disebutkan sebelumnya
    2. Konfirmasi atau kontradiksi dengan insights sebelumnya
    3. Dampak berurutan dari informasi di berbagai bagian

    Berikan output dalam format JSON:
    {{
        "key_facts": ["fakta penting dari bagian ini"],
        "business_events": ["event bisnis yang ditemukan"],
        "investor_implications": ["implikasi untuk investor"],
        "confidence": "HIGH/MEDIUM/LOW",
        "updated_insights": ["insight utama yang perlu dibawa ke chunk berikutnya (3-5 poin)"]
    }}

    Pastikan `updated_insights` berisi 3-5 poin singkat yang merangkum nilai terpenting dari bagian ini untuk dibawa ke chunk berikutnya."""

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
        Supports short, medium, and long content via hierarchical processing.

        Args:
            announcement_data: Dict with ticker, title, date, pdf_url, content

        Returns:
            Dict with Ticker, analysis, and source
        """
        logger.info(f"Analyzing announcement for {announcement_data['ticker']}...")

        content = announcement_data.get("content", "")
        content_length = len(content)

        logger.info(f"Content length: {content_length} characters")

        # Route to appropriate processing strategy based on content length
        if content_length <= self.SHORT_THRESHOLD:
            logger.info("Using single-pass analysis (short content)")
            return self._analyze_single_pass(announcement_data)
        elif content_length <= self.MEDIUM_THRESHOLD:
            logger.info("Using sequential map analysis (medium content)")
            return self._analyze_sequential_map(announcement_data)
        else:
            logger.info("Using map-reduce analysis (long content)")
            return self._analyze_map_reduce(announcement_data)

    def _analyze_single_pass(self, announcement_data: dict) -> dict:
        """
        Single-pass analysis for short content using existing approach.

        Args:
            announcement_data: Dict with announcement metadata and content

        Returns:
            Dict with analysis results
        """
        user_prompt = self._build_single_pass_prompt(announcement_data)

        # Apply rate limiting before making request
        self._apply_rate_limit()

        max_retries = 5
        base_delay = 5

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
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = int(retry_after)
                    else:
                        delay = base_delay * (2**attempt)

                    logger.warning(
                        f"Rate limited. Waiting {delay}s before retry {attempt + 1}/{max_retries}"
                    )
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                result = response.json()
                analysis_text = result["choices"][0]["message"]["content"].strip()

                self._track_request()

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
                return self._error_response(announcement_data, str(e))
            except Exception as e:
                logger.error(f"Error analyzing announcement: {e}")
                return self._error_response(announcement_data, str(e))

        logger.error(f"Max retries exceeded for {announcement_data['ticker']}")
        return self._error_response(
            announcement_data, "Max retries exceeded due to rate limiting"
        )

    def _analyze_sequential_map(self, announcement_data: dict) -> dict:
        """
        Sequential map analysis for medium-length content.
        Process chunks sequentially, carrying forward key insights.

        Args:
            announcement_data: Dict with announcement metadata and content

        Returns:
            Dict with synthesized analysis results
        """
        chunks = self._create_chunks(announcement_data["content"])
        logger.info(f"Created {len(chunks)} chunks for sequential processing")

        previous_insights = []
        all_chunk_analyses = []

        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)} sequentially")

            # Build prompt with previous insights as context
            user_prompt = self._build_sequential_prompt(
                announcement_data, chunk, i, len(chunks), previous_insights
            )

            self._apply_rate_limit()

            max_retries = 5
            base_delay = 5

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
                                "max_tokens": 800,
                            }
                        ),
                    )

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        delay = int(retry_after) if retry_after else base_delay * (2**attempt)
                        logger.warning(f"Rate limited. Waiting {delay}s before retry")
                        time.sleep(delay)
                        continue

                    response.raise_for_status()
                    result = response.json()

                    # Try to parse JSON response, fallback to text
                    chunk_result = self._parse_chunk_response(
                        result["choices"][0]["message"]["content"].strip(), i
                    )

                    self._track_request()

                    # Extract key insights to carry forward (top 3-5 points)
                    previous_insights = chunk_result.get("updated_insights", [])[:5]
                    all_chunk_analyses.append(chunk_result)

                    break  # Success, exit retry loop

                except requests.exceptions.HTTPError as e:
                    if e.response and e.response.status_code == 429:
                        delay = base_delay * (2**attempt)
                        time.sleep(delay)
                        continue
                    logger.error(f"Error in chunk {i}: {e}")
                    all_chunk_analyses.append({"chunk_index": i, "error": str(e)})
                    break
                except Exception as e:
                    logger.error(f"Error in chunk {i}: {e}")
                    all_chunk_analyses.append({"chunk_index": i, "error": str(e)})
                    break

            # Small delay between sequential chunks (already covered by rate limit, but add buffer)
            if i < len(chunks):
                time.sleep(1)

        # Synthesize final analysis from all chunk analyses
        return self._synthesize_analysis(announcement_data, all_chunk_analyses)

    def _analyze_map_reduce(self, announcement_data: dict) -> dict:
        """
        Map-reduce analysis for long content.
        Process chunks independently in sequence (rate-limited), then synthesize.

        Args:
            announcement_data: Dict with announcement metadata and content

        Returns:
            Dict with synthesized analysis results
        """
        chunks = self._create_chunks(announcement_data["content"])
        logger.info(f"Created {len(chunks)} chunks for map-reduce processing")

        all_chunk_analyses = []

        # MAP PHASE: Analyze each chunk independently
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Map: Analyzing chunk {i}/{len(chunks)}")

            user_prompt = self._build_chunk_prompt(announcement_data, chunk, i, len(chunks))

            self._apply_rate_limit()

            max_retries = 5
            base_delay = 5

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
                                "max_tokens": 600,
                            }
                        ),
                    )

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        delay = int(retry_after) if retry_after else base_delay * (2**attempt)
                        logger.warning(f"Rate limited. Waiting {delay}s before retry")
                        time.sleep(delay)
                        continue

                    response.raise_for_status()
                    result = response.json()

                    # Parse JSON response from chunk
                    chunk_analysis = self._parse_chunk_response(
                        result["choices"][0]["message"]["content"].strip(), i
                    )
                    chunk_analysis["chunk_index"] = i
                    chunk_analysis["original_content"] = chunk[:500] + "..."  # Truncated for logging

                    self._track_request()
                    all_chunk_analyses.append(chunk_analysis)

                    break

                except requests.exceptions.HTTPError as e:
                    if e.response and e.response.status_code == 429:
                        delay = base_delay * (2**attempt)
                        time.sleep(delay)
                        continue
                    logger.error(f"Error in chunk {i}: {e}")
                    all_chunk_analyses.append({"chunk_index": i, "error": str(e)})
                    break
                except Exception as e:
                    logger.error(f"Error in chunk {i}: {e}")
                    all_chunk_analyses.append({"chunk_index": i, "error": str(e)})
                    break

            # Brief delay between chunks (rate limiting already enforced, but add small buffer)
            if i < len(chunks):
                time.sleep(0.5)

        # REDUCE PHASE: Synthesize all chunk analyses
        return self._synthesize_analysis(announcement_data, all_chunk_analyses)

    def _build_single_pass_prompt(self, announcement_data: dict) -> str:
        """Build prompt for single-pass analysis of short content."""
        return f"""
Silakan analisis pengumuman IDX berikut dan berikan penilaian ahli dalam BAHASA INDONESIA:

**Ticker Perusahaan:** {announcement_data["ticker"]}
**Judul Pengumuman:** {announcement_data["title"]}
**Tanggal:** {announcement_data["date"]}
**Sumber:** {announcement_data["pdf_url"]}

**Isi Pengumuman:**
{announcement_data["content"]}

**Harap berikan dalam BAHASA INDONESIA:**
1. Ringkasan lengkap pengumuman
2. Implikasi finansial/korporat utama
3. Penilaian sentiment (POSITIVE/NEGATIVE/NEUTRAL)
4. Ekspektasi dampak terhadap investor (HIGH/MEDIUM/LOW)
5. Rekomendasi tindakan atau poin perhatian untuk investor

Analisis harus profesional, faktual, dan membantu keputusan investasi."""

    def _build_chunk_prompt(self, announcement_data: dict, chunk: str, chunk_index: int, total_chunks: int) -> str:
        """Build prompt for analyzing a single chunk in map-reduce approach."""
        return self.CHUNK_ANALYSIS_PROMPT.format(
            ticker=announcement_data["ticker"],
            title=announcement_data["title"],
            date=announcement_data["date"],
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_content=chunk,
        )

    def _build_sequential_prompt(
        self, announcement_data: dict, chunk: str, current_index: int, total_chunks: int, previous_insights: list
    ) -> str:
        """Build prompt for sequential map with context carry-forward."""
        previous_insights_text = "\n".join([f"- {insight}" for insight in previous_insights]) if previous_insights else "Belum ada insights sebelumnya."

        return self.SEQUENTIAL_MAP_PROMPT.format(
            ticker=announcement_data["ticker"],
            title=announcement_data["title"],
            date=announcement_data["date"],
            current_index=current_index,
            total_chunks=total_chunks,
            current_content=chunk,
            previous_insights=previous_insights_text,
        )

    def _synthesize_analysis(self, announcement_data: dict, chunk_analyses: list[dict]) -> dict:
        """
        Synthesize multiple chunk analyses into a coherent final analysis.

        Args:
            announcement_data: Original announcement metadata
            chunk_analyses: List of individual chunk analysis results

        Returns:
            Dict with synthesized analysis
        """
        logger.info("Synthesizing final analysis from chunk results")

        # Build summary of chunk analyses
        chunk_summaries = []
        for analysis in chunk_analyses:
            if "error" in analysis:
                chunk_summaries.append(f"Chunk {analysis['chunk_index']}: Error - {analysis['error']}")
                continue

            # Extract relevant info for synthesis
            facts = "\n  - ".join(analysis.get("key_facts", []))
            events = "\n  - ".join(analysis.get("business_events", []))
            implications = "\n  - ".join(analysis.get("investor_implications", []))

            summary = f"""
**Chunk {analysis['chunk_index']}:**
- Key Facts:
  - {facts}
- Business Events:
  - {events}
- Investor Implications:
  - {implications}
- Confidence: {analysis.get("confidence", "MEDIUM")}
"""
            chunk_summaries.append(summary)

        summaries_text = "\n".join(chunk_summaries)

        synthesis_prompt = self.SYNTHESIS_PROMPT.format(
            ticker=announcement_data["ticker"],
            title=announcement_data["title"],
            date=announcement_data["date"],
            chunk_summaries=summaries_text,
        )

        self._apply_rate_limit()

        max_retries = 5
        base_delay = 5

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
                                {"role": "user", "content": synthesis_prompt},
                            ],
                            "temperature": 0.2,  # Lower temperature for more deterministic synthesis
                            "max_tokens": 1200,  # Allow longer output for comprehensive analysis
                        }
                    ),
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after else base_delay * (2**attempt)
                    logger.warning(f"Rate limited during synthesis. Waiting {delay}s")
                    time.sleep(delay)
                    continue

                response.raise_for_status()
                result = response.json()
                analysis_text = result["choices"][0]["message"]["content"].strip()

                self._track_request()

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
                    time.sleep(delay)
                    continue
                logger.error(f"Error during synthesis: {e}")
                return self._error_response(announcement_data, str(e))
            except Exception as e:
                logger.error(f"Error during synthesis: {e}")
                return self._error_response(announcement_data, str(e))

        logger.error("Max retries exceeded during synthesis")
        return self._error_response(
            announcement_data, "Max retries exceeded during synthesis"
        )

    def _create_chunks(self, content: str) -> list[str]:
        """
        Split content into overlapping chunks preserving document structure.

        Uses paragraph-based splitting when possible, falls back to fixed-size
        chunks with overlap to maintain context continuity.

        Args:
            content: Full text content to chunk

        Returns:
            List of content chunks
        """
        # Try to split by paragraphs first (preserves semantic structure)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        # If we have clear paragraph breaks, use them
        if len(paragraphs) > 1:
            chunks = []
            current_chunk = []
            current_length = 0

            for para in paragraphs:
                para_len = len(para)

                # If paragraph itself is longer than self.CHUNK_SIZE, split it
                if para_len > self.CHUNK_SIZE:
                    # Flush current chunk if it has content
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                        current_chunk = []
                        current_length = 0

                    # Split long paragraph into overlapping segments
                    para_chunks = self._split_long_paragraph(para)
                    chunks.extend(para_chunks)
                else:
                    # Normal paragraph aggregation
                    if current_length + para_len > self.CHUNK_SIZE and current_chunk:
                        # Flush current chunk
                        chunks.append("\n\n".join(current_chunk))
                        current_chunk = [para]
                        current_length = para_len
                    else:
                        current_chunk.append(para)
                        current_length += para_len

            # Flush remaining
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))

            # Ensure we don't have too many tiny chunks at the end - merge if needed
            if len(chunks) > 1 and len(chunks[-1]) < 300:
                chunks[-2] = chunks[-2] + "\n\n" + chunks[-1]
                chunks.pop()

            return chunks if chunks else [content]

        # Fallback: fixed-size chunking with overlap
        return self._fixed_size_chunks(content)

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        """Split a single paragraph that exceeds chunk size into overlapping segments."""
        chunks = []
        start = 0
        paragraph_len = len(paragraph)

        while start < paragraph_len:
            end = start + self.CHUNK_SIZE

            # If not at the end, try to break at sentence boundary
            if end < paragraph_len:
                # Look for sentence endings within the last 200 chars
                lookback_start = max(start + self.CHUNK_SIZE - 200, start)
                sentence_break = -1

                for sep in [". ", "! ", "? ", "\n", "; "]:
                    pos = paragraph.rfind(sep, lookback_start, end)
                    if pos > start:
                        sentence_break = pos + len(sep)
                        break

                if sentence_break != -1:
                    end = sentence_break

            chunk = paragraph[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = max(start + self.CHUNK_SIZE - self.CHUNK_OVERLAP, end - self.CHUNK_OVERLAP)

        return chunks

    def _fixed_size_chunks(self, content: str) -> list[str]:
        """Create fixed-size chunks with overlap when paragraph splitting isn't viable."""
        chunks = []
        start = 0
        content_len = len(content)

        while start < content_len:
            end = min(start + self.CHUNK_SIZE, content_len)

            # If not at end, try to find a good break point
            if end < content_len:
                # Look for newline or sentence break near the boundary
                lookback = content[max(start + self.CHUNK_SIZE - 300, start):end]
                for sep in ["\n\n", "\n", ". ", "! ", "? "]:
                    pos = lookback.rfind(sep)
                    if pos != -1:
                        end = start + self.CHUNK_SIZE - 300 + pos + len(sep)
                        break

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.CHUNK_OVERLAP if end < content_len else content_len

        return chunks if chunks else [content]

    def _parse_chunk_response(self, response_text: str, chunk_index: int) -> dict:
        """
        Parse LLM response for chunk analysis. Expected to be JSON.

        Args:
            response_text: Raw LLM response
            chunk_index: Index of the chunk

        Returns:
            Parsed dict with chunk analysis data
        """
        import json
        import re

        # Try to extract JSON from response
        try:
            # Look for JSON block in response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fallback: create structured dict from text
        return {
            "chunk_index": chunk_index,
            "key_facts": [response_text[:200]],
            "financial_data": {},
            "sentiment_indicators": [],
            "business_events": [],
            "investor_implications": [],
            "confidence": "MEDIUM",
            "raw_response": response_text,
        }

    def _build_prompt(self, announcement_data: dict) -> str:
        """
        Legacy prompt builder - kept for backward compatibility.
        Now delegates to single-pass prompt builder.
        """
        return self._build_single_pass_prompt(announcement_data)

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
        if self._daily_request_count >= self.DAILY_LIMIT:
            logger.warning(
                f"Daily limit ({DAILY_LIMIT}) reached. Waiting until tomorrow..."
            )
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = tomorrow.replace(day=today + 1)
            wait_seconds = (tomorrow - datetime.now()).total_seconds()
            time.sleep(min(wait_seconds, 3600))
            self._daily_request_count = 0
            self._request_times = []

        # Clean old timestamps (older than 1 minute)
        self._request_times = [t for t in self._request_times if current_time - t < 60]

        # Apply minimum delay between requests
        if self._request_times:
            time_since_last = current_time - self._request_times[-1]
            if time_since_last < self.MIN_DELAY_SECONDS:
                sleep_time = self.MIN_DELAY_SECONDS - time_since_last
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

        patterns = [
            r"\b([A-Z]{4})\b",
            r"\b([A-Z]{3})\b",
            r"code[:\s]+([A-Z]{3,4})",
            r"ticker[:\s]+([A-Z]{3,4})",
            r"PT\s+([A-Z][a-zA-Z]+\s+Tbk)",
        ]

        common_tickers = [
            "GRPM", "PMUI", "MDRN", "KREN", "FAST", "KOTA", "ADRO", "KBAG",
            "BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR", "HMSP", "PGNO",
            "INKP", "SMGR", "PATY", "ACES", "PLNN", "MITI", "LPKR", "BNLI",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                if match in common_tickers:
                    logger.info(f"Extracted ticker: {match} from analysis")
                    return match

        pt_match = re.search(r"PT\s+([A-Za-z]+)\s+Tbk", combined)
        if pt_match:
            name = pt_match.group(1).upper()[:4]
            logger.info(f"Extracted ticker: {name} from PT name")
            return name

        return "UNKNOWN"

    def _error_response(self, announcement_data: dict, error_msg: str) -> dict:
        """Create standardized error response."""
        return {
            "Ticker": announcement_data["ticker"],
            "analysis": f"Error during analysis: {error_msg}",
            "source": announcement_data["pdf_url"],
        }
