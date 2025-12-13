"""
Scrape all Vietnamese traffic law links from thuvienphapluat.vn
Rate limited: 5 links per second, 12 second pause between batches
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from urllib.parse import urljoin, urlparse
from collections import deque
import re
import signal
import sys
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'traffic_laws_scrape_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)


class TrafficLawScraper:
    def __init__(
        self,
        cookie_file="./cookie.txt",
        visited_file="visited_urls.txt",
        queue_file="queue_urls.txt",
    ):
        self.base_url = "https://thuvienphapluat.vn"
        self.visited_file = visited_file
        self.queue_file = queue_file
        self.visited_urls = self._load_visited_urls()
        self.to_visit = self._load_queue()
        self.scraped_data = []
        self.cookies = self._load_cookies(cookie_file)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Create a session for better connection handling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies.update(self.cookies)

        # Rate limiting - aggressive to avoid 429 errors
        self.LINKS_PER_BATCH = 3  # Process 3 docs before pause
        self.PAUSE_BETWEEN_BATCHES = 8  # 8 second pause between batches
        self.request_count = 0
        self.consecutive_429_errors = 0  # Track consecutive rate limit errors

        # Output folder
        self.output_folder = f"traffic_laws_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_folder, exist_ok=True)

    def _load_visited_urls(self):
        """Load previously visited URLs from file"""
        if os.path.exists(self.visited_file):
            try:
                with open(self.visited_file, "r", encoding="utf-8") as f:
                    urls = set(line.strip() for line in f if line.strip())
                logging.info(
                    f"[OK] Loaded {len(urls)} visited URLs from {self.visited_file}"
                )
                return urls
            except Exception as e:
                logging.warning(f"Could not load visited URLs: {e}")
                return set()
        return set()

    def _save_visited_url(self, url):
        """Save a visited URL to file immediately"""
        try:
            with open(self.visited_file, "a", encoding="utf-8") as f:
                f.write(f"{url}\n")
        except Exception as e:
            logging.error(f"Could not save visited URL: {e}")

    def _load_queue(self):
        """Load queue from file"""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, "r", encoding="utf-8") as f:
                    urls = deque()
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                # Try to load as JSON dict
                                item = json.loads(line)
                                urls.append(item)
                            except:
                                # Fallback: treat as plain URL string
                                urls.append(
                                    {"url": line, "text": "Resumed", "type": "Unknown"}
                                )
                logging.info(f"[OK] Loaded {len(urls)} URLs from queue file")
                return urls
            except Exception as e:
                logging.warning(f"Could not load queue: {e}")
                return deque()
        return deque()

    def _save_queue(self):
        """Save current queue to file"""
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                for item in self.to_visit:
                    # Save each item as JSON
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            logging.error(f"Could not save queue: {e}")

    def _load_cookies(self, cookie_file):
        """Load cookies from file"""
        try:
            with open(
                cookie_file, "r", encoding="utf-8-sig"
            ) as f:  # utf-8-sig removes BOM
                cookie_string = f.read().strip()

                # Remove any BOM characters that might still be present
                cookie_string = cookie_string.replace("\ufeff", "").replace(
                    "\u200b", ""
                )

                # Convert cookie string to dict
                cookies = {}
                for cookie in cookie_string.split(";"):
                    if "=" in cookie:
                        key, value = cookie.strip().split("=", 1)
                        # Clean key and value from any special characters
                        key = key.strip()
                        value = value.strip()
                        cookies[key] = value

                logging.info(f"[OK] Loaded {len(cookies)} cookies from {cookie_file}")
                return cookies
        except Exception as e:
            logging.warning(f"Could not load cookies: {e}")
            return {}

    def _make_request(self, url, retries=3):
        """Make HTTP request with rate limiting and exponential backoff"""
        for attempt in range(retries):
            try:
                # Rate limiting - pause every N requests
                if (
                    self.request_count > 0
                    and self.request_count % self.LINKS_PER_BATCH == 0
                ):
                    logging.info(
                        f"[PAUSE] Rate limit: Pausing for {self.PAUSE_BETWEEN_BATCHES} seconds..."
                    )
                    time.sleep(self.PAUSE_BETWEEN_BATCHES)
                else:
                    # Micro-delay between individual requests
                    time.sleep(1.5)

                # Use session instead of direct requests.get
                response = self.session.get(url, timeout=30)

                # Explicitly set encoding to handle Vietnamese characters
                response.encoding = response.apparent_encoding or "utf-8"

                self.request_count += 1

                # Handle 429 errors with exponential backoff
                if response.status_code == 429:
                    self.consecutive_429_errors += 1

                    # Exponential backoff: 10s, 20s, 30s, 60s (capped)
                    if self.consecutive_429_errors <= 3:
                        wait_time = 10 * self.consecutive_429_errors
                    else:
                        wait_time = 60  # Cap at 60 seconds

                    logging.warning(
                        f"[RATE LIMIT] 429 error #{self.consecutive_429_errors}. Waiting {wait_time}s... (attempt {attempt+1}/{retries})"
                    )
                    time.sleep(wait_time)

                    if attempt == retries - 1:
                        return None
                    continue

                if response.status_code == 200:
                    # Success! Reset consecutive error counter
                    self.consecutive_429_errors = 0
                    return response
                else:
                    logging.warning(f"Status {response.status_code} for {url}")

            except Exception as e:
                logging.error(f"Request error (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)

        return None

    def _is_traffic_law_related(self, text, url):
        """STRICT: Check if the link is related to traffic laws"""
        if not text and not url:
            return False

        url_lower = url.lower()
        text_lower = (text or "").lower()

        # BLACKLIST: Immediately reject these patterns
        blacklist_patterns = [
            "/iThong/",  # Penalty lookup tool pages (not legal documents)
            "/bulletin/",  # Bulletin pages (403 errors)
            "/phap-luat-doanh-nghiep/",  # Business law pages
            "/phap-luat/tag/",  # Tag pages
            "/phap-luat/tim-",  # Search pages
            "/page/tim-van-ban.aspx",  # Search forms
            "?q=",
            "&loc=",
            "?rel=goi-y",
            "?rel=right_news",  # Query/suggestion links
            "luat-dat-dai",
            "luat-nha-o",  # Land/housing law
            "-lam-nghiep-",
            "-nong-nghiep-",  # Forestry/agriculture law
            "-lao-dong-",
            "-tien-luong-",  # Labor law
            "-so-huu-tri-tue-",  # Intellectual property law
            "/giai-doan/",
            "/cau-hoi-thuong-gap/",  # Generic Q&A pages
            "/bai-viet/",  # Generic articles
        ]

        # Check blacklist first
        for pattern in blacklist_patterns:
            if pattern in url_lower:
                return False

        # MUST have traffic-related keywords in URL or text
        traffic_keywords = [
            "giao thông",
            "giao-thong",
            "đường bộ",
            "duong-bo",
            "trật tự",
            "trat-tu",
            "an toàn giao thông",
            "an-toan-giao-thong",
            "xe cơ giới",
            "xe-co-gioi",
            "lái xe",
            "lai-xe",
            "biển số",
            "bien-so",
            "đăng kiểm",
            "dang-kiem",
            "sát hạch",
            "sat-hach",
            "giấy phép lái xe",
            "giay-phep-lai-xe",
            "vận tải đường bộ",
            "van-tai-duong-bo",
            "tai nạn giao thông",
            "tai-nan-giao-thong",
            "vi phạm giao thông",
            "vi-pham-giao-thong",
            "xử phạt giao thông",
            "xu-phat.*giao-thong",
            "luat-giao-thong",
            "luat-duong-bo",
            "nghi-dinh.*giao-thong",
            "thong-tu.*giao-thong",
        ]

        has_traffic_keyword = any(
            keyword in text_lower or keyword in url_lower
            for keyword in traffic_keywords
        )

        return has_traffic_keyword

    def _extract_links(self, soup, base_url):
        """Extract all relevant links from the page"""
        links = []
        seen_urls = set()

        # Find all <a> tags
        all_a_tags = soup.find_all("a", href=True)
        logging.info(f"[DEBUG] Found {len(all_a_tags)} total <a> tags")

        for a_tag in all_a_tags:
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)

            # Make absolute URL
            full_url = urljoin(base_url, href)

            # Remove anchor fragments for deduplication
            url_without_anchor = full_url.split("#")[0].split("?anchor=")[0]

            # Skip if we've already seen this URL
            if url_without_anchor in seen_urls:
                continue

            # Only process thuvienphapluat.vn links
            if "thuvienphapluat.vn" not in full_url:
                continue

            # Skip non-document links
            skip_patterns = [
                "facebook.com/sharer",  # Facebook sharer links
                "twitter.com/share",  # Twitter share links
                "/iThong/",  # Penalty lookup tool pages (403 errors + no useful links)
                "/page/tim-van-ban.aspx",
                "/page/tim-cong-van",
                "/bulletin/",  # Bulletin pages (403 errors)
                "/search",
                "/dang-nhap",
                "/dang-ky",
                "javascript:",
                "/lich-am",
                "/gia-vang",
                "/goi-dich-vu",
                "/huong-dan",
                "/gioi-thieu",
                "/lien-he",
                "/tin-tuc/",
                "/bieu-thue",
                "/page/ho-tro-phap-luat.aspx",
                "/page/van-ban-lien-quan",
                "/page/search-scroll",
                "/phap-luat/tim-van-ban.aspx",
                "/phap-luat-doanh-nghiep",  # Business law
                "/phap-luat/doanh-nghiep",
                "/phap-luat/lao-dong-tien-luong",
                "/phap-luat/bat-dong-san",
                "/phap-luat/vi-pham-hanh-chinh",
                "/phap-luat/bao-hiem",
                "/phap-luat/quyen-dan-su",
                "/phap-luat/van-hoa-xa-hoi",
                "/phap-luat/thuong-mai",
                "/phap-luat/trach-nhiem-hinh-su",
                "/phap-luat/xay-dung-do-thi",
                "/phap-luat/tag/",  # Tag pages
                "/giai-doan/",  # Generic stages
                "/cau-hoi-thuong-gap/",  # Generic Q&A
                "/bai-viet/",  # Generic articles
                "?q=",
                "&loc=",
                "?rel=goi-y",
                "?rel=right_news",  # Query params
            ]

            if any(pattern in full_url.lower() for pattern in skip_patterns):
                continue

            # Skip if it's just the homepage or generic category pages
            if full_url.rstrip("/") in [
                "https://thuvienphapluat.vn",
                "https://thuvienphapluat.vn/phap-luat",
                "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat",
            ]:
                continue

            # Include links that are van-ban documents
            is_document = "/van-ban/" in full_url.lower()

            # For articles, include if it's a document or legal article about traffic law
            is_legal_article = (
                "/phap-luat/" in full_url.lower()
                and "-ho-tro-phap-luat/" in full_url.lower()
                and "giao-thong" in full_url.lower()
            )

            if is_document or is_legal_article:
                # Additional filter: Only include if related to traffic law
                if self._is_traffic_law_related(url_without_anchor, text):
                    seen_urls.add(url_without_anchor)
                    links.append(
                        {
                            "url": url_without_anchor,
                            "text": text if text else "No title",
                            "type": self._classify_link(url_without_anchor),
                        }
                    )

        logging.info(f"[DEBUG] After filtering: {len(links)} document links")
        return links

    def _classify_link(self, url):
        """Classify the type of legal document"""
        url_lower = url.lower()

        if (
            "van-ban" in url_lower
            or "nghi-dinh" in url_lower
            or "thong-tu" in url_lower
        ):
            if "nghi-dinh" in url_lower:
                return "Nghị định"
            elif "thong-tu" in url_lower:
                return "Thông tư"
            elif "luat" in url_lower:
                return "Luật"
            elif "quyet-dinh" in url_lower:
                return "Quyết định"
            elif "chi-thi" in url_lower:
                return "Chỉ thị"
            else:
                return "Văn bản"
        elif "phap-luat" in url_lower:
            return "Bài viết pháp luật"
        else:
            return "Khác"

    def _extract_document_info(self, soup, url):
        """Extract detailed information from a document page"""
        info = {
            "url": url,
            "title": "",
            "type": "",
            "number": "",
            "date": "",
            "status": "",
            "content": "",
            "related_links": [],
        }

        try:
            # Title
            title_tag = soup.find("h1") or soup.find("h2", class_="nqTitle")
            if title_tag:
                info["title"] = title_tag.get_text(strip=True)

            # Document details
            details = soup.find("div", class_="document-detail") or soup.find(
                "div", class_="content1"
            )
            if details:
                # Extract document number, date, status
                text = details.get_text()

                # Number pattern: Số: 168/2024/NĐ-CP
                number_match = re.search(r"Số:?\s*([^\n]+)", text)
                if number_match:
                    info["number"] = number_match.group(1).strip()

                # Date pattern
                date_match = re.search(
                    r"ngày\s+(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE
                )
                if date_match:
                    info["date"] = date_match.group(1)

                # Status
                status_match = re.search(r"Tình trạng:?\s*([^\n]+)", text)
                if status_match:
                    info["status"] = status_match.group(1).strip()

            # Extract related documents
            related = soup.find_all("a", href=True)
            for a in related:
                href = a["href"]
                text = a.get_text(strip=True)
                if self._is_traffic_law_related(text, href):
                    full_url = urljoin(url, href)
                    if (
                        full_url not in self.visited_urls
                        and "thuvienphapluat.vn" in full_url
                    ):
                        info["related_links"].append({"url": full_url, "text": text})

        except Exception as e:
            logging.error(f"Error extracting document info: {e}")

        return info

    def scrape_page(self, url):
        """Scrape a single page and extract all relevant information"""
        if url in self.visited_urls:
            return None

        # Skip URLs that match our skip patterns (before making request!)
        skip_patterns = [
            "facebook.com/sharer",
            "twitter.com/share",
            "/iThong/",  # Penalty lookup tool pages
            "/bulletin/",
            "/page/tim-van-ban.aspx",
            "/page/tim-cong-van",
            "/search",
            "/dang-nhap",
            "/dang-ky",
        ]

        if any(pattern in url.lower() for pattern in skip_patterns):
            logging.info(f"[SKIP] Skipping filtered URL: {url}")
            self.visited_urls.add(url)
            self._save_visited_url(url)  # Mark as visited to avoid revisiting
            return None

        logging.info(f"[SCRAPING] {url}")
        self.visited_urls.add(url)
        self._save_visited_url(url)  # Save immediately to file

        response = self._make_request(url)
        if not response:
            logging.error(f"[ERROR] Failed to fetch: {url}")
            return None

        logging.info(f"[DEBUG] Response length: {len(response.text)} chars")

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract document info
        doc_info = self._extract_document_info(soup, url)

        # Extract all links
        links = self._extract_links(soup, url)

        logging.info(f"[OK] Found {len(links)} related links on {url}")

        # Add new links to queue
        for link in links:
            if link["url"] not in self.visited_urls:
                self.to_visit.append(link)

        # Add related links from document info
        for related in doc_info.get("related_links", []):
            if related["url"] not in self.visited_urls:
                self.to_visit.append(related)

        return doc_info

    def scrape_all(self, start_url):
        """Scrape starting from the given URL and follow all related links"""
        logging.info(f"[START] Starting scrape from: {start_url}")
        logging.info(
            f"[CONFIG] Rate limit: {self.LINKS_PER_BATCH} links/batch, {self.PAUSE_BETWEEN_BATCHES}s pause"
        )
        logging.info(
            f"[RESUME] Already visited: {len(self.visited_urls)} URLs, Queue: {len(self.to_visit)} URLs"
        )

        # Start with the main page (only if not already in queue and not visited)
        if not self.to_visit and start_url not in self.visited_urls:
            self.to_visit.append(
                {"url": start_url, "text": "Main page", "type": "Article"}
            )
            logging.info(f"[START] Added start URL to queue")

        processed_count = 0

        while self.to_visit:
            current = self.to_visit.popleft()
            url = current["url"]

            doc_info = self.scrape_page(url)

            if doc_info:
                doc_info["found_via"] = current.get("text", "Unknown")
                doc_info["document_type"] = current.get("type", "Unknown")
                self.scraped_data.append(doc_info)
                processed_count += 1

                # Save progress every 10 documents
                if processed_count % 10 == 0:
                    self._save_progress()
                    self._save_queue()  # Save queue to file
                    logging.info(
                        f"[PROGRESS] {processed_count} docs processed, {len(self.to_visit)} in queue"
                    )

        # Final save
        self._save_progress()
        self._save_queue()  # Save final queue state
        self._save_progress()
        self._generate_summary()

        logging.info(
            f"[COMPLETE] Scraping completed! Total documents: {len(self.scraped_data)}"
        )
        logging.info(f"[OUTPUT] Output folder: {self.output_folder}")

    def _save_progress(self):
        """Save current progress to JSON file"""
        output_file = os.path.join(self.output_folder, "scraped_data.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)

        # Also save as JSONL for easier processing
        jsonl_file = os.path.join(self.output_folder, "scraped_data.jsonl")
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for item in self.scraped_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _generate_summary(self):
        """Generate summary report"""
        summary = {
            "total_documents": len(self.scraped_data),
            "total_requests": self.request_count,
            "document_types": {},
            "all_urls": [],
        }

        for doc in self.scraped_data:
            doc_type = doc.get("document_type", "Unknown")
            summary["document_types"][doc_type] = (
                summary["document_types"].get(doc_type, 0) + 1
            )
            summary["all_urls"].append(
                {
                    "url": doc["url"],
                    "title": doc.get("title", ""),
                    "type": doc_type,
                    "number": doc.get("number", ""),
                }
            )

        # Save summary
        summary_file = os.path.join(self.output_folder, "summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Save URL list
        url_list_file = os.path.join(self.output_folder, "url_list.txt")
        with open(url_list_file, "w", encoding="utf-8") as f:
            for item in summary["all_urls"]:
                f.write(f"{item['url']}\t{item['type']}\t{item['title']}\n")

        logging.info(f"[SUMMARY] Summary saved to {summary_file}")
        logging.info(f"Document types: {summary['document_types']}")


# Global scraper instance for signal handler
scraper_instance = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global scraper_instance
    logging.info("\n[INTERRUPTED] Received interrupt signal, saving state...")
    if scraper_instance:
        scraper_instance._save_progress()
        scraper_instance._save_queue()
        logging.info(
            f"[SAVED] Progress saved. {len(scraper_instance.visited_urls)} URLs visited, {len(scraper_instance.to_visit)} in queue"
        )
        logging.info(
            f"[INFO] To resume, just run the script again - it will continue from where it stopped"
        )
    sys.exit(0)


def run_cleanup_script():
    """Run the cleanup script to remove empty/failed results"""
    try:
        logging.info("\n[CLEANUP] Running cleanup script to remove empty results...")
        result = subprocess.run(
            ["python", "clean_empty_results.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode == 0:
            logging.info("[CLEANUP] Cleanup completed successfully!")
            # Log the output
            for line in result.stdout.split("\n"):
                if line.strip():
                    logging.info(f"  {line}")
        else:
            logging.error(f"[CLEANUP] Cleanup failed with error: {result.stderr}")

    except Exception as e:
        logging.error(f"[CLEANUP] Failed to run cleanup script: {e}")


def main():
    global scraper_instance

    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # The main URL to start scraping
    start_url = "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/luat-giao-thong-2025-va-cac-nghi-dinh-thong-tu-huong-dan-moi-nhat-luat-giao-thong-2025-gom-cac-luat-939767-198964.html"

    max_retries = 99  # Maximum number of retry attempts
    retry_count = 0

    while retry_count <= max_retries:
        if retry_count == 0:
            logging.info(f"\n{'='*60}")
            logging.info("[START] Initial scraping run")
            logging.info(f"{'='*60}")
        else:
            logging.info(f"\n{'='*60}")
            logging.info(f"[RETRY] Retry attempt {retry_count}/{max_retries}")
            logging.info(f"{'='*60}")

        # Run scraper
        scraper_instance = TrafficLawScraper()
        scraper_instance.scrape_all(start_url)

        # Run cleanup script after scraping
        run_cleanup_script()

        # Check if we should retry (check if queue is not empty)
        if retry_count < max_retries:
            if scraper_instance.to_visit and len(scraper_instance.to_visit) > 0:
                logging.info(
                    f"\n[FOUND] {len(scraper_instance.to_visit)} URLs still in queue"
                )
                logging.info(f"[AUTO-RETRY] Automatically retrying in 10 seconds...")
                time.sleep(10)
                retry_count += 1
                continue
            else:
                logging.info("\n[COMPLETE] No URLs left in queue!")
                break
        else:
            logging.info(
                f"\n[MAX RETRIES] Reached maximum retry attempts ({max_retries})"
            )
            break

    logging.info(f"\n{'='*60}")
    logging.info("[FINAL] Scraping completed!")
    logging.info(f"{'='*60}")


if __name__ == "__main__":
    main()
