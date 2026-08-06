"""HTML fetcher for the 5 fixed Groww scheme URLs.
Captures raw HTML, status codes, and timestamps with zero PDF logic.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict
import requests

from ingestion.models import SchemeSource, RawPage


class GrowwFetcher:
    """Fetches HTML content for registered Groww scheme URLs."""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 15, max_retries: int = 3, retry_delay: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def fetch_page(self, source: SchemeSource) -> RawPage:
        """Fetches a single scheme page with retry logic."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(
                    source.url,
                    headers=self.DEFAULT_HEADERS,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    return RawPage(
                        source_id=source.id,
                        url=source.url,
                        scheme_name=source.name,
                        html_content=response.text,
                        fetched_at=today_str,
                        status_code=response.status_code
                    )
                else:
                    last_error = f"HTTP {response.status_code}"
            except Exception as e:
                last_error = str(e)

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)

        raise RuntimeError(f"Failed to fetch {source.url} after {self.max_retries} attempts. Last error: {last_error}")

    def fetch_all(self, sources: List[SchemeSource]) -> List[RawPage]:
        """Fetches all scheme sources in the registry."""
        pages = []
        for s in sources:
            page = self.fetch_page(s)
            pages.append(page)
        return pages
