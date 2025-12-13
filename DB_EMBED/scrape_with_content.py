"""
Traffic Law Scraper WITH CONTENT EXTRACTION
Enhanced version that extracts actual legal text from documents

Key Differences from scrape_traffic_laws.py:
- Extracts full document content text
- Focuses on main document pages (no tabs)
- Better content parsing for different page types
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import logging
import time
import signal
import sys
from collections import deque
from datetime import datetime
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"traffic_laws_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(),
    ],
)


class TrafficLawContentScraper:
    def __init__(
        self,
        visited_file="visited_urls_content.txt",
        queue_file="queue_urls_content.txt",
    ):
        self.visited_urls = set()
        self.to_visit = deque()
        self.results = []
        self.visited_file = visited_file
        self.queue_file = queue_file

        # Request settings
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Load cookies if available
        self._load_cookies()

        # Rate limiting
        self.batch_size = 5
        self.batch_pause = 6  # seconds between batches
        self.request_count = 0

        # Load previous state
        self._load_visited_urls()
        self._load_queue()

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        logging.info("\n[SHUTDOWN] Ctrl+C detected. Saving state...")
        self._save_results()
        self._save_queue()
        logging.info("[SHUTDOWN] State saved. Exiting.")
        sys.exit(0)

    def _load_cookies(self):
        """Load cookies from file"""
        try:
            with open("./cookie.txt", "r", encoding="utf-8") as f:
                cookie_str = f.read().strip()
                if cookie_str:
                    cookies = {}
                    for item in cookie_str.split("; "):
                        if "=" in item:
                            key, value = item.split("=", 1)
                            cookies[key] = value
                    self.session.cookies.update(cookies)
                    logging.info("[OK] Loaded cookies from ./cookie.txt")
        except FileNotFoundError:
            logging.warning("[WARN] No cookie.txt found")

    def _load_visited_urls(self):
        """Load visited URLs from file"""
        try:
            with open(self.visited_file, "r", encoding="utf-8") as f:
                self.visited_urls = set(line.strip() for line in f if line.strip())
            logging.info(
                f"[OK] Loaded {len(self.visited_urls)} visited URLs from {self.visited_file}"
            )
        except FileNotFoundError:
            logging.info("[INFO] No previous visited URLs file found")

    def _save_visited_url(self, url):
        """Save a single visited URL immediately"""
        with open(self.visited_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    def _load_queue(self):
        """Load queue from file (JSONL format)"""
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        link = json.loads(line.strip())
                        self.to_visit.append(link)
            logging.info(f"[OK] Loaded {len(self.to_visit)} URLs from queue file")
        except FileNotFoundError:
            logging.info("[INFO] No previous queue file found")

    def _save_queue(self):
        """Save queue to file (JSONL format)"""
        with open(self.queue_file, "w", encoding="utf-8") as f:
            for link in self.to_visit:
                f.write(json.dumps(link, ensure_ascii=False) + "\n")
        logging.info(f"[SAVE] Saved {len(self.to_visit)} URLs to queue")

    def _save_results(self):
        """Save results to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"traffic_laws_content_{timestamp}"

        import os

        os.makedirs(output_dir, exist_ok=True)

        # Save as JSONL (one object per line)
        jsonl_file = f"{output_dir}/scraped_data.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for item in self.results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # Save as complete JSON array
        json_file = f"{output_dir}/scraped_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logging.info(f"[SAVE] Saved {len(self.results)} documents to {output_dir}/")

    def _make_request(self, url):
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response
        except Exception as e:
            logging.error(f"[ERROR] Request failed for {url}: {e}")
            return None

    def _extract_content(self, soup, url):
        """
        Extract main content text from different page types

        Strategies:
        1. Look for main content divs (document body)
        2. Extract article text for Q&A pages
        3. Get all paragraph text as fallback
        """
        content_text = ""

        try:
            # Strategy 1: Van ban (official documents) - look for content1 or content-detail
            content_divs = soup.find_all(
                "div", class_=["content1", "content-detail", "noidung1", "noi-dung"]
            )
            if content_divs:
                for div in content_divs:
                    # Remove script and style tags
                    for script in div(["script", "style", "iframe"]):
                        script.decompose()
                    content_text += div.get_text(separator="\n", strip=True) + "\n\n"

            # Strategy 2: Articles/Q&A pages - look for article body
            if not content_text:
                article_divs = soup.find_all(
                    "div", class_=["article-body", "article-content", "baiviet-content"]
                )
                for div in article_divs:
                    for script in div(["script", "style", "iframe"]):
                        script.decompose()
                    content_text += div.get_text(separator="\n", strip=True) + "\n\n"

            # Strategy 3: Look for specific content areas by id
            if not content_text:
                content_by_id = soup.find(
                    "div", id=re.compile(r"(content|noidung|article)", re.IGNORECASE)
                )
                if content_by_id:
                    for script in content_by_id(["script", "style", "iframe"]):
                        script.decompose()
                    content_text = content_by_id.get_text(separator="\n", strip=True)

            # Strategy 4: Fallback - get all paragraphs in main content area
            if not content_text or len(content_text) < 200:
                paragraphs = soup.find_all("p")
                temp_content = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Only substantial paragraphs
                        temp_content.append(text)

                if temp_content:
                    content_text = "\n\n".join(temp_content)

            # Clean up the content
            content_text = content_text.strip()

            # Remove excessive whitespace
            content_text = re.sub(r"\n{3,}", "\n\n", content_text)
            content_text = re.sub(r" {2,}", " ", content_text)

        except Exception as e:
            logging.error(f"[ERROR] Content extraction failed for {url}: {e}")

        return content_text

    def _is_main_document_page(self, url):
        """
        Check if URL is a main document page (not tabs, anchors, etc.)
        We want the base document URL only
        """
        url_lower = url.lower()

        # Skip tab variants
        if "?tab=" in url_lower:
            return False

        # Skip anchor links (but keep base URLs with #)
        if "?anchor=" in url_lower or "#dieu_" in url_lower or "#khoan_" in url_lower:
            return False

        # Skip query parameters that aren't the main page
        if "?rel=" in url_lower or "?q=" in url_lower:
            return False

        # Must be van-ban (official document) or legal article
        if "/van-ban/" in url_lower:
            return True

        if (
            "/phap-luat/ho-tro-phap-luat/" in url_lower
            or "/chinh-sach-phap-luat-moi/" in url_lower
        ):
            return True

        return False

    def _is_traffic_law_related(self, text, url):
        """Check if content is related to traffic laws"""
        text_lower = text.lower()
        url_lower = url.lower()

        # Blacklist patterns
        blacklist = [
            "doanh-nghiep",
            "lao-dong",
            "bat-dong-san",
            "thuong-mai",
            "tag?keyword=",
            "/phap-luat/tag/",
            "/iThong/tra-cuu-xu-phat",
        ]

        if any(pattern in url_lower for pattern in blacklist):
            return False

        # Must have traffic keywords
        keywords = [
            "giao thông",
            "giao-thong",
            "đường bộ",
            "duong-bo",
            "lái xe",
            "lai-xe",
            "xe cơ giới",
            "đăng kiểm",
            "dang-kiem",
            "biển số",
            "vi phạm giao thông",
            "xu-phat.*giao-thong",
        ]

        return any(k in text_lower or k in url_lower for k in keywords)

    def _extract_document_info(self, soup, url):
        """Extract document information WITH CONTENT"""
        info = {
            "url": url,
            "title": "",
            "type": "",
            "number": "",
            "date": "",
            "status": "",
            "content": "",  # THIS IS THE KEY DIFFERENCE!
            "related_links": [],
            "found_via": "",
            "document_type": "Unknown",
        }

        try:
            # Title
            title_tag = (
                soup.find("h1") or soup.find("h2", class_="nqTitle") or soup.find("h2")
            )
            if title_tag:
                info["title"] = title_tag.get_text(strip=True)

            # Document number
            number_match = re.search(r"Số:?\s*([^\n]+)", soup.get_text())
            if number_match:
                info["number"] = number_match.group(1).strip()

            # Date
            date_match = re.search(
                r"ngày\s+(\d{1,2}/\d{1,2}/\d{4})", soup.get_text(), re.IGNORECASE
            )
            if date_match:
                info["date"] = date_match.group(1)

            # Document type
            if "/luat-" in url.lower() or "luật" in info["title"].lower():
                info["document_type"] = "Luật"
            elif "/nghi-dinh-" in url.lower() or "nghị định" in info["title"].lower():
                info["document_type"] = "Nghị định"
            elif "/thong-tu-" in url.lower() or "thông tư" in info["title"].lower():
                info["document_type"] = "Thông tư"
            elif "/quyet-dinh-" in url.lower():
                info["document_type"] = "Quyết định"
            elif "/cong-van-" in url.lower():
                info["document_type"] = "Công văn"

            # **EXTRACT CONTENT** - This is the main addition!
            info["content"] = self._extract_content(soup, url)

            # Extract related links (limit to 10 to keep it manageable)
            related_links = []
            for a_tag in soup.find_all("a", href=True, limit=50):
                href = a_tag["href"]
                text = a_tag.get_text(strip=True)

                if not text or len(text) > 200:
                    continue

                full_url = urljoin(url, href)

                if "thuvienphapluat.vn" in full_url and self._is_traffic_law_related(
                    text, full_url
                ):
                    if (
                        self._is_main_document_page(full_url)
                        and full_url not in self.visited_urls
                    ):
                        related_links.append({"url": full_url, "text": text})

                        if len(related_links) >= 10:
                            break

            info["related_links"] = related_links

        except Exception as e:
            logging.error(f"[ERROR] Document extraction failed: {e}")

        return info

    def scrape_page(self, url):
        """Scrape a page and extract content"""
        if url in self.visited_urls:
            return None

        logging.info(f"[SCRAPING] {url}")
        self.visited_urls.add(url)
        self._save_visited_url(url)

        response = self._make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract document with content
        doc_info = self._extract_document_info(soup, url)

        # Log content length
        content_len = len(doc_info.get("content", ""))
        if content_len > 0:
            logging.info(f"[CONTENT] Extracted {content_len} chars from {url}")
        else:
            logging.warning(f"[NO CONTENT] Empty content for {url}")

        # Add related links to queue
        for link in doc_info.get("related_links", []):
            if link["url"] not in self.visited_urls:
                self.to_visit.append(link)

        return doc_info

    def scrape_all(self, start_url):
        """Main scraping loop"""
        # Add start URL if queue is empty
        if not self.to_visit:
            self.to_visit.append({"url": start_url, "text": "Start", "type": "Start"})

        logging.info(f"[START] Starting scrape from: {start_url}")
        logging.info(
            f"[CONFIG] Rate limit: {self.batch_size} links/batch, {self.batch_pause}s pause"
        )
        logging.info(
            f"[RESUME] Already visited: {len(self.visited_urls)} URLs, Queue: {len(self.to_visit)} URLs"
        )

        try:
            while self.to_visit:
                link = self.to_visit.popleft()
                url = link["url"]

                # Only scrape main document pages
                if not self._is_main_document_page(url):
                    continue

                # Scrape the page
                doc_info = self.scrape_page(url)

                if doc_info:
                    self.results.append(doc_info)

                self.request_count += 1

                # Rate limiting
                if self.request_count % self.batch_size == 0:
                    logging.info(
                        f"[PAUSE] Rate limit: Pausing for {self.batch_pause} seconds..."
                    )
                    time.sleep(self.batch_pause)

                # Progress update and save every 10 documents
                if len(self.results) % 10 == 0:
                    logging.info(
                        f"[PROGRESS] {len(self.results)} docs processed, {len(self.to_visit)} in queue"
                    )
                    self._save_results()
                    self._save_queue()

        except Exception as e:
            logging.error(f"[ERROR] Scraping failed: {e}")
        finally:
            # Final save
            self._save_results()
            self._save_queue()
            logging.info(
                f"[DONE] Scraping complete. Total documents: {len(self.results)}"
            )


if __name__ == "__main__":
    scraper = TrafficLawContentScraper()

    # Start URL - main traffic law hub page
    start_url = "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/luat-giao-thong-2025-va-cac-nghi-dinh-thong-tu-huong-dan-moi-nhat-luat-giao-thong-2025-gom-cac-luat-939767-198964.html"

    scraper.scrape_all(start_url)
