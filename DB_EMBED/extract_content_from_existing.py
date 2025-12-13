"""
Content Extractor for Existing URLs
Reads URLs from existing scraper's visited_urls.txt and extracts actual content

This script:
1. Loads URLs from visited_urls.txt (from current scraper)
2. Filters to main document pages only (no tabs/anchors)
3. Extracts full legal text content with Selenium + OCR CAPTCHA handling
4. Saves to new output with content included
"""

from bs4 import BeautifulSoup
import json
import logging
import time
import random
import signal
import sys
from datetime import datetime
import re
import easyocr
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import warnings
import subprocess

# Suppress warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"content_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(),
    ],
)


class ContentExtractor:
    def __init__(self, input_urls_file="visited_urls.txt"):
        self.input_urls_file = input_urls_file
        self.processed_urls = set()
        self.results = []
        self.driver = None

        # Authentication credentials
        self.username = "dawng123"
        self.password = None

        # OCR reader for CAPTCHA (lazy load)
        self.ocr_reader = None
        self.passing_captcha = False

        # Rate limiting (matching scrape_traffic_laws.py)
        self.batch_size = 3
        self.batch_pause = 20  # Increased from 8 to 20 seconds
        self.request_count = 0

        # Content quality tracking
        self.paywall_text_markers = [
            "Các nội dung của văn bản này được văn bản khác thay đổi",
            "Được hỗ trợ pháp lý sơ bộ qua Điện thoại",
            "Nhận thông báo văn bản mới qua Email",
            "Trang cá nhân",
            "gói dịch vụ",
        ]

        # Track progress
        self.processed_file = "processed_content_urls.txt"
        self._load_processed_urls()

        # Setup browser
        self._setup_browser()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        logging.info("\n[SHUTDOWN] Ctrl+C detected. Saving results...")
        self._save_results()
        if self.driver:
            self.driver.quit()
        logging.info("[SHUTDOWN] Results saved. Exiting.")
        sys.exit(0)

    def _setup_browser(self):
        """Setup undetected Chrome browser"""
        logging.info("[STEP] Setting up Chrome browser...")
        options = uc.ChromeOptions()

        # Make browser visible and keep it open
        options.add_argument("--start-maximized")

        try:
            self.driver = uc.Chrome(options=options)
            logging.info("[OK] Chrome browser ready!")
        except Exception as e:
            logging.error(f"[ERROR] Failed to setup browser: {e}")
            sys.exit(1)

    def _is_paywall_text(self, content):
        """Check if content is just paywall/registration text"""
        if not content or len(content) < 2000:
            markers_found = sum(
                1 for marker in self.paywall_text_markers if marker in content
            )
            if markers_found >= 2:
                return True
        return False

    def _handle_captcha_page(self):
        """Handle CAPTCHA page using OCR with Selenium"""
        if self.passing_captcha:
            time.sleep(18)
            return False

        self.passing_captcha = True
        try:
            # Check if we're on a CAPTCHA page
            if "ReturnUrl=" not in self.driver.current_url:
                self.passing_captcha = False
                return True

            logging.info("[CAPTCHA] Detected CAPTCHA page, attempting OCR...")

            wait = WebDriverWait(self.driver, 10)
            login_template = wait.until(
                EC.presence_of_element_located((By.ID, "block-info-3col"))
            )

            img_element = login_template.find_element(By.TAG_NAME, "img")

            random_name = str(random.randint(1, 9999))
            os.makedirs("./captcha", exist_ok=True)

            img_path = f"./captcha/captcha_{random_name}.png"
            img_element.screenshot(img_path)

            # Initialize OCR reader if needed
            if self.ocr_reader is None:
                logging.info("[OCR] Loading EasyOCR model...")
                self.ocr_reader = easyocr.Reader(["en"])

            # Read CAPTCHA text
            result = self.ocr_reader.readtext(img_path)
            captcha_text = "".join([detection[1] for detection in result]).replace(
                " ", ""
            )

            logging.info(f"[CAPTCHA] Detected text: {captcha_text}")

            # Enter CAPTCHA
            captcha_input = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_Content_txtSecCode"))
            )
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)

            # Click submit button
            try:
                login_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_Content_CheckButton"))
                )
                login_button.click()
            except:
                try:
                    login_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.ID, "ctl00_Content_cmdLogin"))
                    )
                    login_button.click()
                except:
                    pass

            time.sleep(2)
            self.driver.refresh()
            self.passing_captcha = False
            logging.info("[CAPTCHA] Successfully solved CAPTCHA")
            return True

        except Exception as e:
            logging.error(f"[CAPTCHA] Error handling CAPTCHA: {e}")
            self.passing_captcha = False
            return False

    def _load_processed_urls(self):
        """Load already processed URLs to resume"""
        try:
            with open(self.processed_file, "r", encoding="utf-8") as f:
                self.processed_urls = set(line.strip() for line in f if line.strip())
            logging.info(
                f"[OK] Loaded {len(self.processed_urls)} already processed URLs"
            )
        except FileNotFoundError:
            logging.info("[INFO] No previous progress file found")

    def _save_processed_url(self, url):
        """Save a processed URL immediately"""
        with open(self.processed_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    def _save_results(self):
        """Save results to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"traffic_laws_WITH_CONTENT_{timestamp}"

        import os

        os.makedirs(output_dir, exist_ok=True)

        # Save as JSONL
        jsonl_file = f"{output_dir}/scraped_data_with_content.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for item in self.results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # Save as JSON
        json_file = f"{output_dir}/scraped_data_with_content.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logging.info(f"[SAVE] Saved {len(self.results)} documents to {output_dir}/")

    def _is_main_document_page(self, url):
        """
        Check if URL is a main document page (not tabs, anchors, query params)
        ONLY ALLOWS: Văn bản PL (legal articles) and Văn bản (official documents)
        """
        url_lower = url.lower()

        # Skip Facebook sharer links and other social media
        if "facebook.com/sharer" in url_lower or "twitter.com/share" in url_lower:
            return False

        # Skip tab variants
        if "?tab=" in url_lower:
            return False

        # Skip anchor links (but allow # for legal articles)
        if "?anchor=" in url_lower or "#dieu_" in url_lower or "#khoan_" in url_lower:
            return False

        # Skip query parameters
        if "?rel=" in url_lower or "?q=" in url_lower or "?keyword=" in url_lower:
            return False

        # Skip tag pages
        if "/tag?" in url_lower or "/phap-luat/tag/" in url_lower:
            return False

        # Skip tool pages
        if "/iThong/" in url_lower:
            return False

        # ONLY ALLOW: Văn bản PL (legal articles) and Văn bản (official documents)
        # Văn bản PL: Legal articles from ho-tro-phap-luat
        if "/phap-luat/ho-tro-phap-luat/" in url_lower:
            return True

        # Văn bản: Official legal documents from /van-ban/
        if "/van-ban/" in url_lower:
            return True

        # SKIP ALL OTHER TYPES (Công văn, Luật, Nghị định, Thông tư, Quyết định, etc.)
        return False

    def _extract_content(self, url):
        """Extract main content text from the page using Selenium"""
        content_text = ""

        try:
            # Get page source from Selenium
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Strategy 1: PRIMARY - divContentDoc or content1 (also check for English pages)
            div_content = (
                soup.find("div", id="divContentDoc")
                or soup.find("div", class_="content1")
                or soup.find("div", id="content")
                or soup.find("div", class_="document-content")
            )
            if div_content:
                # Remove unwanted elements
                for unwanted in div_content(
                    ["script", "style", "iframe", "nav", "header", "footer", "aside"]
                ):
                    unwanted.decompose()

                # Remove ads
                for ad_class in [
                    "box-middle",
                    "ShowBMTip",
                    "TVPL_VB",
                    "list-text",
                    "mnGoiDV",
                ]:
                    for ad_elem in div_content.find_all(class_=ad_class):
                        ad_elem.decompose()

                text = div_content.get_text(separator="\n", strip=True)
                if len(text) > 1000:
                    content_text = text

            # Strategy 2: Article content
            if not content_text or len(content_text) < 500:
                article_divs = soup.find_all(
                    "div",
                    class_=[
                        "article-body",
                        "article-content",
                        "baiviet-content",
                        "content-body",
                    ],
                )
                for div in article_divs:
                    for unwanted in div(["script", "style", "iframe"]):
                        unwanted.decompose()
                    text = div.get_text(separator="\n", strip=True)
                    if len(text) > 200:
                        content_text = text
                        break

            # Strategy 3: Fallback - paragraphs
            if not content_text or len(content_text) < 500:
                paragraphs = soup.find_all("p")
                temp_content = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    skip_keywords = [
                        "đăng nhập",
                        "đăng ký",
                        "tìm kiếm",
                        "liên hệ",
                        "gói dịch vụ",
                        "tra cứu",
                        "xem trực tiếp",
                        "tải về",
                        "miễn phí",
                    ]
                    if len(text) > 50 and not any(
                        skip in text.lower() for skip in skip_keywords
                    ):
                        temp_content.append(text)

                if temp_content and len(temp_content) > 5:
                    content_text = "\n\n".join(temp_content)

            # Clean up
            content_text = content_text.strip()
            content_text = re.sub(r"\n{3,}", "\n\n", content_text)
            content_text = re.sub(r" {2,}", " ", content_text)

        except Exception as e:
            logging.error(f"[ERROR] Content extraction failed for {url}: {e}")

        return content_text

    def _navigate_to_url(self, url):
        """Navigate to URL and handle CAPTCHA if needed"""
        try:
            self.driver.get(url)
            time.sleep(2)  # Wait for page load

            # Check if CAPTCHA page
            if (
                "captcha.aspx" in self.driver.current_url.lower()
                or "ReturnUrl=" in self.driver.current_url
            ):
                logging.warning(
                    f"[CAPTCHA] CAPTCHA page detected, attempting to solve..."
                )
                if not self._handle_captcha_page():
                    return False
                # Retry original URL after CAPTCHA
                self.driver.get(url)
                time.sleep(2)

            # Check for Cloudflare BLOCK page (not just Cloudflare presence)
            page_source = self.driver.page_source.lower()
            # Only detect actual block pages, not just Cloudflare scripts
            is_blocked = (
                ("you have been blocked" in page_source)
                or ("sorry, you have been blocked" in page_source)
                or (
                    "checking your browser" in page_source
                    and "cloudflare" in page_source
                )
                or (
                    "ray id" in page_source
                    and "cloudflare" in page_source
                    and len(page_source) < 5000
                )
            )

            if is_blocked:
                logging.warning(
                    f"[CLOUDFLARE] Cloudflare BLOCK page detected, waiting 30 seconds..."
                )
                time.sleep(30)  # Wait longer for IP cooldown
                self.driver.refresh()
                time.sleep(5)
                # Check if still blocked
                page_source = self.driver.page_source.lower()
                if (
                    "you have been blocked" in page_source
                    or "sorry, you have been blocked" in page_source
                ):
                    logging.error(
                        f"[CLOUDFLARE] Still blocked - IP banned. Skipping URL."
                    )
                    return False

            return True
        except Exception as e:
            logging.error(f"[ERROR] Navigation failed for {url}: {e}")
            return False

    def _extract_document_info(self, url):
        """Extract document information WITH CONTENT using Selenium"""
        info = {
            "url": url,
            "title": "",
            "type": "",
            "number": "",
            "date": "",
            "status": "",
            "content": "",
            "content_length": 0,
            "document_type": "Unknown",
        }

        try:
            # Get page source
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Title
            title_tag = (
                soup.find("h1") or soup.find("h2", class_="nqTitle") or soup.find("h2")
            )
            if title_tag:
                info["title"] = title_tag.get_text(strip=True)

            # Document details from page text
            page_text = soup.get_text()

            number_match = re.search(r"Số:?\s*([^\n]+)", page_text)
            if number_match:
                info["number"] = number_match.group(1).strip()

            date_match = re.search(
                r"ngày\s+(\d{1,2}/\d{1,2}/\d{4})", page_text, re.IGNORECASE
            )
            if date_match:
                info["date"] = date_match.group(1)

            status_match = re.search(r"Tình trạng:?\s*([^\n]+)", page_text)
            if status_match:
                info["status"] = status_match.group(1).strip()

            # Document type from URL - Văn bản PL and Văn bản
            if "/phap-luat/ho-tro-phap-luat/" in url.lower():
                info["document_type"] = "Văn bản PL"
            elif "/van-ban/" in url.lower():
                info["document_type"] = "Văn bản"
            else:
                info["document_type"] = "Unknown"

            # Extract content
            info["content"] = self._extract_content(url)
            info["content_length"] = len(info["content"])

        except Exception as e:
            logging.error(f"[ERROR] Document extraction failed: {e}")

        return info

    def load_urls_to_process(self):
        """Load URLs from the existing scraper's visited_urls.txt"""
        urls_to_process = []

        try:
            with open(self.input_urls_file, "r", encoding="utf-8") as f:
                all_urls = [line.strip() for line in f if line.strip()]

            logging.info(
                f"[OK] Loaded {len(all_urls)} URLs from {self.input_urls_file}"
            )

            # Filter to main document pages only
            for url in all_urls:
                if url not in self.processed_urls and self._is_main_document_page(url):
                    urls_to_process.append(url)

            logging.info(
                f"[FILTER] {len(urls_to_process)} main document pages to process"
            )
            logging.info(
                f"[SKIP] {len(all_urls) - len(urls_to_process)} non-main pages (tabs, anchors, etc.)"
            )

            return urls_to_process

        except FileNotFoundError:
            logging.error(f"[ERROR] Could not find {self.input_urls_file}")
            return []

    def process_all(self):
        """Process all URLs and extract content using Selenium"""
        urls_to_process = self.load_urls_to_process()

        if not urls_to_process:
            logging.error("[ERROR] No URLs to process!")
            return

        total = len(urls_to_process)
        logging.info(f"[START] Processing {total} URLs...")
        logging.info(
            f"[INFO] Chrome browser window is open - you can watch the progress!"
        )

        paywall_count = 0
        success_count = 0

        try:
            for idx, url in enumerate(urls_to_process, 1):
                logging.info(f"[{idx}/{total}] Processing: {url}")

                # Navigate to URL
                if not self._navigate_to_url(url):
                    self._save_processed_url(url)
                    continue

                # Extract document info
                doc_info = self._extract_document_info(url)

                # Check if content is paywall text
                content = doc_info.get("content", "")
                content_len = doc_info.get("content_length", 0)

                is_paywall = self._is_paywall_text(content)

                if is_paywall:
                    paywall_count += 1
                    logging.warning(
                        f"[PAYWALL] Only paywall text detected ({content_len} chars)"
                    )
                    self._save_processed_url(url)
                    continue

                # Log content status
                if content_len > 500:
                    logging.info(f"[OK CONTENT] {content_len} chars extracted")
                    success_count += 1
                elif content_len > 0:
                    logging.warning(f"[SHORT] Only {content_len} chars extracted")
                else:
                    logging.error(f"[EMPTY] No content extracted")

                # Save result
                self.results.append(doc_info)
                self.processed_urls.add(url)
                self._save_processed_url(url)

                self.request_count += 1

                # Rate limiting
                if self.request_count % self.batch_size == 0:
                    logging.info(
                        f"[PAUSE] Rate limit: Pausing for {self.batch_pause} seconds..."
                    )
                    time.sleep(self.batch_pause)
                else:
                    time.sleep(5)  # Increased from 2.5 to 5 seconds

                # Save progress every 10 documents
                if len(self.results) % 10 == 0:
                    self._save_results()
                    logging.info(
                        f"[PROGRESS] {len(self.results)}/{total} (Success: {success_count}, Paywall: {paywall_count})"
                    )

        except Exception as e:
            logging.error(f"[ERROR] Processing failed: {e}")

        finally:
            self._save_results()

            # Statistics
            with_content = sum(
                1 for doc in self.results if doc.get("content_length", 0) > 500
            )
            short_content = sum(
                1 for doc in self.results if 0 < doc.get("content_length", 0) <= 500
            )
            no_content = sum(
                1 for doc in self.results if doc.get("content_length", 0) == 0
            )

            logging.info(f"\n[DONE] Content extraction complete!")
            logging.info(f"  Total processed: {len(self.results)}")
            logging.info(f"  With substantial content (>500 chars): {with_content}")
            logging.info(f"  With short content (1-500 chars): {short_content}")
            logging.info(f"  No content: {no_content}")

            # Close browser
            if self.driver:
                logging.info("[CLEANUP] Closing browser...")
                self.driver.quit()


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


def retry_failed_urls():
    """Retry URLs that failed in previous runs"""
    logging.info("\n[RETRY] Checking for failed URLs to retry...")

    # Remove processed URLs file to allow retrying
    if os.path.exists("processed_content_urls.txt"):
        # Read all processed URLs
        with open("processed_content_urls.txt", "r", encoding="utf-8") as f:
            processed = set(line.strip() for line in f if line.strip())

        logging.info(f"[RETRY] Found {len(processed)} previously processed URLs")

        # Count how many are in the actual results
        extractor = ContentExtractor(input_urls_file="visited_urls.txt")
        urls_to_process = extractor.load_urls_to_process()

        if urls_to_process:
            logging.info(
                f"[RETRY] {len(urls_to_process)} URLs need retry (empty/failed)"
            )

            # Ask user if they want to retry
            response = (
                input("\n[?] Do you want to retry failed URLs? (y/n): ").strip().lower()
            )

            if response == "y":
                logging.info("[RETRY] Starting retry process...")
                extractor.process_all()
                return True
            else:
                logging.info("[SKIP] Skipping retry")
                return False
        else:
            logging.info("[OK] No failed URLs to retry!")
            return False
    else:
        logging.info("[INFO] No previous run found")
        return False


if __name__ == "__main__":
    max_retries = 99  # Maximum number of retry attempts
    retry_count = 0

    while retry_count <= max_retries:
        if retry_count == 0:
            logging.info(f"\n{'='*60}")
            logging.info("[START] Initial content extraction run")
            logging.info(f"{'='*60}")
        else:
            logging.info(f"\n{'='*60}")
            logging.info(f"[RETRY] Retry attempt {retry_count}/{max_retries}")
            logging.info(f"{'='*60}")

        # Run content extraction
        extractor = ContentExtractor(input_urls_file="visited_urls.txt")
        extractor.process_all()

        # Run cleanup script after extraction
        run_cleanup_script()

        # Check if we should retry
        if retry_count < max_retries:
            # Check if there are failed URLs by comparing processed vs results
            urls_to_process = extractor.load_urls_to_process()

            if urls_to_process and len(urls_to_process) > 0:
                logging.info(f"\n[FOUND] {len(urls_to_process)} URLs need retry")

                # Auto-retry without asking
                logging.info(f"[AUTO-RETRY] Automatically retrying in 10 seconds...")
                time.sleep(10)

                # Clear processed file for retry
                if os.path.exists("processed_content_urls.txt"):
                    os.remove("processed_content_urls.txt")
                    logging.info("[RETRY] Cleared processed URLs for retry")

                retry_count += 1
                continue
            else:
                logging.info("\n[COMPLETE] No failed URLs to retry!")
                break
        else:
            logging.info(
                f"\n[MAX RETRIES] Reached maximum retry attempts ({max_retries})"
            )
            break

    logging.info(f"\n{'='*60}")
    logging.info("[FINAL] Content extraction completed!")
    logging.info(f"{'='*60}")
