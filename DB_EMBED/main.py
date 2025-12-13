from datetime import datetime
import gc
import os
import random
import time
import concurrent
import warnings
from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import easyocr
from tqdm import tqdm
import threading

# Suppress PyTorch warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")


class ThuvienPhapLuatCrawler:
    def __init__(self, data_path, username, password, type_craw="", use_proxy=True):
        self.data_path = data_path
        self.username = username
        self.password = password
        self.log_dir = "./logs"
        self._setup_logging(type_craw)
        self.user_agents = self._load_file("./craw_lib/user-agents-window.txt")
        self.use_proxy = use_proxy
        if use_proxy:
            # Hardcoded premium proxy: IP:PORT:USERNAME:PASSWORD
            self.proxies = ["213.239.211.254:19348:v5-3348-336261:JSXOY"]
            print(f"Using hardcoded proxy: {len(self.proxies)} proxy loaded")
        else:
            self.proxies = []
            print("Running WITHOUT proxy")
        self.qa_domains = self._load_qa_domains("./qa_domain/domains_qa.json")
        self.download_count = 0
        self.driver = None
        self.passing_capcha = False
        self.dowload_success_count = 0

        self.folder_map = {
            1: "data_tvpl",
            2: "data_duthao",
            3: "data_congvan",
            4: "data_tieuchuan",
        }

        # self.category = self._get_category()
        self.__get_cookie()

    def __load_existing_cookies(self):
        """Load cookies from file if they exist"""
        try:
            with open("./cookie.txt", "r") as f:
                cookie_string = f.read().strip()
                if cookie_string:
                    print("[INFO] ✅ Loaded existing cookies from cookie.txt")
                    return cookie_string
        except FileNotFoundError:
            print("[INFO] No existing cookie file found")
        return None

    def __set_proxy(self, proxy_file):
        with open(proxy_file, "r") as f:
            proxy_list = [line.strip() for line in f.readlines() if line.strip()]

        # idx = random.randint(1,800)
        # return proxy_list[idx: idx+1]
        print("Total proxies loaded:", len(proxy_list))
        # for i, proxy in enumerate(proxy_list):
        #     print(f"Proxy {i}: {proxy}")
        return proxy_list

    def __get_random_proxy(self, return_dict=True):
        if not self.use_proxy or len(self.proxies) == 0:
            return None if return_dict else None

        proxy = random.choice(self.proxies)

        # Parse proxy format: IP:PORT:USERNAME:PASSWORD
        proxy_parts = proxy.split(":")
        if len(proxy_parts) == 4:
            ip, port, username, password = proxy_parts
            proxy_formatted = f"{username}:{password}@{ip}:{port}"
        else:
            # Fallback for simple format IP:PORT
            proxy_formatted = proxy

        if return_dict:
            return {
                "http": f"http://{proxy_formatted}",
                "https": f"http://{proxy_formatted}",
            }
        return proxy_formatted

    def __check_status_change_proxy(self):
        while True:
            with open("./status.txt", "r") as f:
                content = f.read()

            if content == "True":
                return True

            time.sleep(1)

    def __pass_capcha(self, url):
        # Khởi tạo Chrome WebDriver
        if self.passing_capcha:
            time.sleep(18)
            return

        self.passing_capcha = True
        try:
            self.driver.get(url)

            if "ReturnUrl=" not in self.driver.current_url:
                self.passing_capcha = False

            wait = WebDriverWait(self.driver, 10)

            login_template = wait.until(
                EC.presence_of_element_located((By.ID, "block-info-3col"))
            )

            img_element = login_template.find_element(By.TAG_NAME, "img")

            random_name = str(random.randint(1, 9999))

            os.makedirs("./captcha", exist_ok=True)

            img_element.screenshot(f"./captcha/captcha_{random_name}.png")

            reader = easyocr.Reader(["en"])  # Sử dụng mô hình tiếng Anh
            result = reader.readtext(f"./captcha/captcha_{random_name}.png")
            captcha_text = ""
            for detection in result:
                captcha_text += detection[1]  # Nối các phần văn bản đọc được

            print("Văn bản đọc được từ CAPTCHA:", captcha_text)
            captcha_text = captcha_text.replace(" ", "")

            captcha_input = wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_Content_txtSecCode"))
            )
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)
        except:
            self.passing_capcha = False
            return

        # Đảm bảo chỉ nhấn một trong hai nút nếu nó có thể nhấn được
        try:
            login_button_1 = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Content_CheckButton"))
            )
            login_button_1.click()
        except:
            pass

        try:
            login_button_2 = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "ctl00_Content_cmdLogin"))
            )
            login_button_2.click()
        except:
            pass

        time.sleep(1)
        self.driver.refresh()
        self.passing_capcha = False

    def split_array(self, arr_slice, num_splits, passing=0):
        arr = arr_slice[passing:]
        if num_splits <= 0:
            raise ValueError("Number of splits must be greater than zero.")

        chunk_size = len(arr) // num_splits
        remainder = len(arr) % num_splits

        result = []
        start = 0

        for i in range(num_splits):
            extra = 1 if i < remainder else 0
            end = start + chunk_size + extra
            result.append(arr[start:end])
            start = end

        return result

    def __get_cookie(self):
        # Try to load existing cookies first
        existing_cookies = self.__load_existing_cookies()
        if existing_cookies:
            self.cookies = existing_cookies
            print("[INFO] Using existing cookies, skipping browser login")
            return

        # If no cookies exist, do the browser login
        USER_NAME = self.username
        PASSWORD = self.password

        print("[STEP] Setting up undetected Chrome driver (bypasses Cloudflare)...")
        options = uc.ChromeOptions()

        user_agent = random.choice(self.user_agents)
        print(f"[INFO] Using user_agent: {user_agent}")
        options.add_argument(f"--user-agent={user_agent}")

        PROXY = self.__get_random_proxy(return_dict=False)
        print(f"[INFO] Proxy: {PROXY}")

        if PROXY:
            # Parse proxy credentials
            proxy_parts = PROXY.split("@")
            if len(proxy_parts) == 2:
                # Format: username:password@ip:port
                auth, host_port = proxy_parts
                username, password = auth.split(":")
                host, port = host_port.split(":")

                # Create proxy extension for Chrome
                print("[STEP] Creating proxy authentication extension...")
                manifest_json = """
                {
                    "version": "1.0.0",
                    "manifest_version": 2,
                    "name": "Chrome Proxy",
                    "permissions": [
                        "proxy",
                        "tabs",
                        "unlimitedStorage",
                        "storage",
                        "<all_urls>",
                        "webRequest",
                        "webRequestBlocking"
                    ],
                    "background": {
                        "scripts": ["background.js"]
                    },
                    "minimum_chrome_version":"22.0.0"
                }
                """

                background_js = """
                var config = {
                        mode: "fixed_servers",
                        rules: {
                        singleProxy: {
                            scheme: "http",
                            host: "%s",
                            port: parseInt(%s)
                        },
                        bypassList: ["localhost"]
                        }
                    };

                chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

                function callbackFn(details) {
                    return {
                        authCredentials: {
                            username: "%s",
                            password: "%s"
                        }
                    };
                }

                chrome.webRequest.onAuthRequired.addListener(
                            callbackFn,
                            {urls: ["<all_urls>"]},
                            ['blocking']
                );
                """ % (
                    host,
                    port,
                    username,
                    password,
                )

                # Create extension directory
                import zipfile

                pluginfile = "proxy_auth_plugin.zip"

                with zipfile.ZipFile(pluginfile, "w") as zp:
                    zp.writestr("manifest.json", manifest_json)
                    zp.writestr("background.js", background_js)

                options.add_extension(pluginfile)
                print("[INFO] Proxy extension created and loaded")
            else:
                # Simple proxy without authentication
                options.add_argument(f"--proxy-server={PROXY}")

        print("[STEP] Starting undetected Chrome WebDriver...")
        self.driver = uc.Chrome(options=options, version_main=None)

        try:
            print("[STEP] Navigating to login page...")
            base_url = "https://thuvienphapluat.vn/page/profile.aspx"
            login_url = "https://thuvienphapluat.vn/page/login.aspx?ReturnUrl=%2fpage%2fprofile.aspx"
            self.driver.get(login_url)

            print("[INFO] ⏳ Waiting for Cloudflare check to complete...")
            print(
                "[INFO] 👉 If you see Cloudflare challenge, please click it manually in the browser window!"
            )
            print("[INFO] 👉 Waiting up to 60 seconds for the page to load...")

            # Wait longer for Cloudflare to pass
            time.sleep(5)  # Give initial page time to load

            # Extended wait for login form (60 seconds to allow manual Cloudflare click)
            wait = WebDriverWait(self.driver, 60)

            print("[STEP] Waiting for login form...")
            wait.until(EC.presence_of_element_located((By.ID, "UserName")))
            print("[STEP] ✅ Login form loaded successfully!")

            print("[STEP] Filling in username and password...")
            self.driver.find_element(By.ID, "UserName").send_keys(USER_NAME)
            self.driver.find_element(By.ID, "Password").send_keys(PASSWORD)
            self.driver.find_element(By.ID, "Button1").click()

            print("[STEP] Waiting for login to complete...")
            time.sleep(3)

            try:
                print("[STEP] Checking for post-login popup...")
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "/html/body/div[15]/div[3]/div/button[1]")
                    )
                ).click()
                print("[INFO] Closed post-login popup.")
            except:
                print("[INFO] No post-login popup found.")

            print("[STEP] Waiting for profile page to load...")
            # Try to navigate to profile page
            try:
                self.driver.get(base_url)
                time.sleep(3)
                print("[INFO] Profile page loaded")
            except:
                print("[INFO] Using current page for cookies")

            print("[STEP] Getting cookies...")
            cookies = self.driver.get_cookies()
            cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            self.cookies = cookie_string
            print("[STEP] Saving cookies to file...")
            with open("./cookie.txt", "w") as f:
                f.write(cookie_string)
            print("[INFO] ✅ Cookies saved successfully!")

        finally:
            print("[STEP] Closing browser...")
            # driver.quit()

    def _get_category(self):
        with open("./category.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_folder_name(self, category):
        if category == "0":
            return ""
        for cate in self.category:
            if category == cate["fields"]:
                return self.__convert_vietnamese(cate["name"])

        return ""

    def _setup_logging(self, type_craw):
        time_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        os.makedirs(self.log_dir, exist_ok=True)
        log_file = os.path.join(
            self.log_dir,
            f"craw_list_{self.__convert_vietnamese(type_craw)}_{time_str}.log",
        )
        logging.basicConfig(filename=log_file, level=logging.INFO)
        logging.info(f"Crawler started at {time_str}")

    def _load_file(self, filepath):
        with open(filepath, "r") as f:
            return [line.strip() for line in f.readlines()]

    def _load_qa_domains(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def __convert_vietnamese(self, text):
        s = text.lower()
        s = s.replace(":", "")
        s = s.replace(",", "-")

        s = re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a", s)
        s = re.sub(r"[ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]", "A", s)
        s = re.sub(r"[èéẹẻẽêềếệểễ]", "e", s)
        s = re.sub(r"[ÈÉẸẺẼÊỀẾỆỂỄ]", "E", s)
        s = re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o", s)
        s = re.sub(r"[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]", "O", s)
        s = re.sub(r"[ìíịỉĩ]", "i", s)
        s = re.sub(r"[ÌÍỊỈĨ]", "I", s)
        s = re.sub(r"[ùúụủũưừứựửữ]", "u", s)
        s = re.sub(r"[ƯỪỨỰỬỮÙÚỤỦŨ]", "U", s)
        s = re.sub(r"[ỳýỵỷỹ]", "y", s)
        s = re.sub(r"[ỲÝỴỶỸ]", "Y", s)
        s = re.sub(r"[Đ]", "D", s)
        s = re.sub(r"[đ]", "d", s)
        s = re.sub(r"\W+", " ", s)
        s = s.replace(" ", "_")
        return s

    def generate_headers(self, referer_url):
        return {
            "authority": "thuvienphapluat.vn",
            "referer": referer_url,
            "method": "GET",
            "scheme": "https",
            "accept": "*/*",
            "user-agent": random.choice(self.user_agents),
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "cookie": self.cookies,
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
        }

    def get_all_qa_by_domain(self, output_dir, max_workers=3):
        def format_url(url):
            if not url.startswith("http"):
                if url.startswith("/"):
                    url = url[1:]
                url = "https://thuvienphapluat.vn/" + url
            return url

        def get_page_urls(page_url, max_retries=10, timeout=20):
            urls = []
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(
                        page_url,
                        headers=self.generate_headers(page_url),
                        proxies=self.__get_random_proxy(),
                        timeout=timeout,
                    )

                    if response.status_code != 200:
                        retry_count += 1
                        print(
                            f"Error at page {page_url}: {response.status_code}. Retry {retry_count}/{max_retries}"
                        )
                        continue

                    if not os.path.exists("./error_html"):
                        os.makedirs("./error_html")

                    with open(
                        "./error_html/error_html.html", "w", encoding="utf-8"
                    ) as f:
                        f.write(response.text)

                    while "ReturnUrl=" in response.url:
                        self.__pass_capcha(page_url)
                        response = requests.get(
                            page_url,
                            headers=self.generate_headers(page_url),
                            proxies=self.__get_random_proxy(),
                            timeout=timeout,
                        )

                    soup = BeautifulSoup(response.text, "html.parser")
                    for article in soup.find_all("article", class_="news-card"):
                        url = article.find("a")["href"]
                        urls.append(format_url(url))

                    if len(urls) > 0:
                        break

                    retry_count += 1
                    print(f"No URLs found, retry attempt {retry_count}/{max_retries}")
                except Exception as e:
                    retry_count += 1
                    print(
                        f"Error getting page urls (attempt {retry_count}/{max_retries}): {e}"
                    )
                    if retry_count >= max_retries:
                        print(f"Failed to get page URLs after {max_retries} attempts")
                        return []
            return urls

        def collect_all_urls(domain, base_url, max_page):
            all_urls = []
            print(f"Collecting all URLs for domain {domain} from {base_url}")

            # Divide pages among workers
            pages_per_worker = (
                max_page + max_workers - 1
            ) // max_workers  # Ceiling division

            def process_page_range(start_page, end_page):
                worker_urls = []
                for page_number in range(start_page, min(end_page, max_page + 1)):
                    page_url = base_url + str(page_number)
                    print(f"Processing page {page_number} of {max_page} for {domain}")
                    urls = get_page_urls(page_url)
                    if urls:
                        worker_urls.extend(urls)
                        print(f"Found {len(urls)} URLs on page {page_number}")
                    else:
                        print(f"No URLs found on page {page_number}")
                return worker_urls

            futures = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                for i in range(max_workers):
                    start_page = i * pages_per_worker + 1
                    end_page = (i + 1) * pages_per_worker + 1
                    futures.append(
                        executor.submit(process_page_range, start_page, end_page)
                    )

                for future in concurrent.futures.as_completed(futures):
                    all_urls.extend(future.result())

            return all_urls

        def process_url(url, domain_folder):
            max_retries = 3
            retries = 0
            item = None

            while retries < max_retries:
                try:
                    response = requests.get(
                        url,
                        headers=self.generate_headers(url),
                        proxies=self.__get_random_proxy(),
                        timeout=10,
                    )

                    if response.status_code != 200:
                        retries += 1
                        print(
                            f"Error at question {url}: {response.status_code}. Retry {retries}/{max_retries}"
                        )
                        continue

                    while "ReturnUrl=" in response.url:
                        self.__pass_capcha(url)
                        response = requests.get(
                            url,
                            headers=self.generate_headers(url),
                            proxies=self.__get_random_proxy(),
                            timeout=10,
                        )

                    soup = BeautifulSoup(response.text, "html.parser")
                    item_title = None
                    if soup.find("h1", class_="h3 fw-bold title"):
                        item_title = soup.find(
                            "h1", class_="h3 fw-bold title"
                        ).text.strip()
                    elif soup.find("header", class_="title"):
                        item_title = soup.find("header", class_="title").text.strip()

                    item_content = None
                    if soup.find("strong", class_="d-block mt-3 mb-3 sapo"):
                        item_content = soup.find(
                            "strong", class_="d-block mt-3 mb-3 sapo"
                        ).text.strip()
                    elif soup.find("section", class_="introduction"):
                        item_content = soup.find(
                            "section", class_="introduction"
                        ).text.strip()

                    item_date = None
                    if soup.find("span", class_="news-time"):
                        item_date = (
                            soup.find("span", class_="news-time")
                            .text.strip()
                            .split()[-1]
                        )
                    elif soup.find("div", class_=["news-time", "grey-color"]):
                        item_date = (
                            soup.find("div", class_=["news-time", "grey-color"])
                            .text.strip()
                            .split()[-1]
                        )

                    item_answer = None
                    if soup.find("section", class_="news-content"):
                        item_answer = soup.find(
                            "section", class_="news-content"
                        ).text.strip()
                    elif soup.find("section", id="main-content"):
                        item_answer = soup.find(
                            "section", id="main-content"
                        ).text.strip()

                    if (
                        not item_title
                        or not item_content
                        or not item_date
                        or not item_answer
                    ):
                        assert False

                    item = {
                        "title": item_title,
                        "content": item_content,
                        "date": item_date,
                        "url": url,
                        "answer": item_answer,
                    }

                    break
                except Exception as e:
                    retries += 1
                    print(
                        f"Error at question {url}: {str(e)}. Retry {retries}/{max_retries}"
                    )

                    if retries >= max_retries:
                        print(
                            f"Failed to get question {url} after {max_retries} attempts"
                        )

            return item, url

        def process_domain(domain, base_url, max_page, folder_path):
            # Create domain folder if it doesn't exist
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            # File to store all collected URLs
            all_urls_file = os.path.join(folder_path, "all_urls.jsonl")

            # First phase: Collect all URLs and save them to a file
            if not os.path.exists(all_urls_file):
                print(f"Collecting URLs for domain {domain}")
                all_urls = collect_all_urls(domain, base_url, max_page)

                all_urls = list(set(all_urls))  # Remove duplicates
                with open(all_urls_file, "w", encoding="utf-8") as f:
                    for url in all_urls:
                        f.write(json.dumps({"url": url}) + "\n")

                print(f"Saved {len(all_urls)} URLs to {all_urls_file}")
            else:
                print(f"URLs file already exists at {all_urls_file}")

            # Second phase: Process each URL from the file
            processed_urls_file = os.path.join(folder_path, "processed_urls.jsonl")
            processed_urls = set()

            # Load already processed URLs if file exists
            if os.path.exists(processed_urls_file):
                with open(processed_urls_file, "r", encoding="utf-8") as f:
                    for line in f:
                        url = json.loads(line)["url"]
                        if url.startswith("https://thuvienphapluat.vn//"):
                            url = url.replace(
                                "https://thuvienphapluat.vn//",
                                "https://thuvienphapluat.vn/",
                            )
                        processed_urls.add(url)
                print(f"Found {len(processed_urls)} already processed URLs")

            # Load all URLs
            all_urls = []
            with open(all_urls_file, "r", encoding="utf-8") as f:
                for line in f:
                    url = json.loads(line)["url"]
                    if url.startswith("https://thuvienphapluat.vn//"):
                        url = url.replace(
                            "https://thuvienphapluat.vn//",
                            "https://thuvienphapluat.vn/",
                        )
                    all_urls.append(url)

            # Filter out already processed URLs
            urls_to_process = [url for url in all_urls if url not in processed_urls]
            print(
                f"Processing {len(urls_to_process)} remaining URLs for domain {domain}"
            )

            # Process URLs in parallel - using JSONL format to avoid memory issues
            questions_file = os.path.join(folder_path, "questions.jsonl")
            questions_count = 0

            # Count existing questions if file exists
            if os.path.exists(questions_file):
                with open(questions_file, "r", encoding="utf-8") as f:
                    questions_count = sum(1 for _ in f)
                print(f"Found {questions_count} existing questions in {questions_file}")
            else:
                print(f"No existing questions found, starting fresh")

            questions_file_lock = threading.Lock()
            processed_file_lock = threading.Lock()
            processed_count = 0

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = [
                    executor.submit(process_url, url, folder_path)
                    for url in urls_to_process
                ]

                for future in tqdm(
                    concurrent.futures.as_completed(futures),
                    total=len(urls_to_process),
                    desc=f"Processing {domain}",
                ):
                    item, url = future.result()

                    if item is not None:
                        # Write question directly to JSONL file (one JSON object per line)
                        with questions_file_lock:
                            with open(questions_file, "a", encoding="utf-8") as f:
                                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                            processed_count += 1

                        # Mark URL as processed
                        with processed_file_lock:
                            with open(processed_urls_file, "a", encoding="utf-8") as f:
                                f.write(json.dumps({"url": url}) + "\n")

                        # Log progress periodically
                        if processed_count % 100 == 0:
                            print(f"Processed {processed_count} questions so far")

            # Count final questions
            final_count = 0
            if os.path.exists(questions_file):
                with open(questions_file, "r", encoding="utf-8") as f:
                    final_count = sum(1 for _ in f)

            print(
                f"Completed processing domain {domain}: {final_count} questions saved to {questions_file}"
            )

            # Optionally convert JSONL to JSON format for backward compatibility
            try:
                questions_json_file = os.path.join(folder_path, "questions.json")
                print(f"Converting JSONL to JSON format for compatibility...")

                questions = []
                try:
                    with open(questions_json_file, "r", encoding="utf-8") as f:
                        questions = json.load(f)
                    print(
                        f"Loaded {len(questions)} questions from {questions_json_file}"
                    )
                except FileNotFoundError:
                    questions = []
                    print(
                        f"File {questions_json_file} not found, creating new JSON file"
                    )

                with open(questions_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            questions.append(json.loads(line))

                with open(questions_json_file, "w", encoding="utf-8") as f:
                    json.dump(questions, f, ensure_ascii=False, indent=4)
                print(f"Saved {len(questions)} questions to {questions_json_file}")
                del questions  # Free memory
                gc.collect()  # Force garbage collection to free memory

            except Exception as e:
                print(f"Warning: Failed to create JSON format file: {e}")
                print(f"Data is safely stored in JSONL format at {questions_file}")

        # Process each domain in the qa_domains list
        for item in self.qa_domains:
            domain = item["domain"]
            base_url = item["base_url"]
            max_page = item["max_page"]
            print(f"Processing domain {domain} from {base_url}")
            folder_path = os.path.join(output_dir, domain)

            process_domain(domain, base_url, max_page, folder_path)

    def get_not_yet_effective_law(
        self, st_page, en_page, max_workers=3, output_folder="all_law_not_yet_effective"
    ):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_file = f"{output_folder}/all_law_not_yet_effective_from_{st_page}_to_{en_page}.jsonl"

        current_date = datetime.now().strftime("%d/%m/%Y")
        base_url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&status=0&signer=0&sort=2&lan=1&scan=0&org=0&fields=&chlbg={current_date}&chlend=27/01/3000&page="
        print("BASE URL: ", base_url)

        def crawl_page_range(start_page, end_page):
            page_idx = start_page
            while page_idx <= end_page:
                max_retries = 20
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        print(f"Worker crawling page {page_idx}")

                        page_url = base_url + str(page_idx)
                        self.driver.get(page_url)
                        self.__check_status_change_proxy()
                        response = requests.get(
                            page_url,
                            headers=self.generate_headers(page_url),
                            proxies=self.__get_random_proxy(),
                        )

                        if response.status_code != 200:
                            retry_count += 1
                            print(
                                f"Error at page {page_idx}: {response.status_code}. Retry {retry_count}/{max_retries}"
                            )
                            continue

                        while "ReturnUrl=" in response.url:
                            self.__pass_capcha(page_url)
                            response = requests.get(
                                page_url,
                                headers=self.generate_headers(page_url),
                                proxies=self.__get_random_proxy(),
                            )

                        soup = BeautifulSoup(response.text, "html.parser")
                        p_tags = soup.find_all("p", class_="nqTitle")
                        page_urls = []

                        for p_tag in p_tags:
                            href = p_tag.find("a")["href"]

                            # Skip Facebook sharer links and other social media links
                            if (
                                "facebook.com/sharer" in href
                                or "twitter.com/share" in href
                            ):
                                continue

                            if href.startswith("https://thuvienphapluat.vn"):
                                page_urls.append(href)
                            else:
                                page_urls.append(f"https://thuvienphapluat.vn{href}")

                        if len(page_urls) == 0:
                            continue

                        # Write URLs directly to file as they're found
                        with open(output_file, "a", encoding="utf-8") as f:
                            for url in page_urls:
                                f.write(
                                    json.dumps({"url": url}, ensure_ascii=False) + "\n"
                                )

                        print(
                            f"Successfully crawled page {page_idx}: Found {len(page_urls)} URLs"
                        )
                        success = True

                    except Exception as e:
                        retry_count += 1
                        print(
                            f"Error at page {page_idx}: {str(e)}. Retry {retry_count}/{max_retries}"
                        )

                if not success:
                    print(
                        f"Failed to crawl page {page_idx} after {max_retries} attempts"
                    )

                page_idx += 1

        # Split work into chunks for multiple workers
        max_pages = en_page - st_page + 1
        chunk_size = max_pages // max_workers

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(max_workers):
                start_page = i * chunk_size + st_page + 1
                end_page = (
                    (i + 1) * chunk_size + st_page if i < max_workers - 1 else en_page
                )
                futures.append(executor.submit(crawl_page_range, start_page, end_page))

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()

        logging.info(f"Crawling completed for pages {st_page} to {en_page}")
        print(f"Crawling completed for pages {st_page} to {en_page}")

        # Count the total number of URLs in the file
        url_count = 0
        with open(output_file, "r", encoding="utf-8") as f:
            for _ in f:
                url_count += 1

        print(f"Total URLs saved: {url_count}")
        return output_file

    def get_latest_law(
        self,
        st_page,
        en_page,
        max_workers=3,
        output_folder="all_law_effective_from_01_07_2025",
    ):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_file = f"{output_folder}/all_law_from_{st_page}_to_{en_page}.jsonl"

        # base_url = "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&status=0&signer=0&sort=1&lan=1&scan=0&org=0&fields=&chlbg=02/06/1945&chlend=02/06/2035&page={page_idx}"
        base_url = "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&type=17&status=0&lan=1&org=0&signer=0&match=True&sort=1&bdate=13/07/1945&edate=14/07/2025&chlbg=01/06/2025&chlend=14/07/2035&page={page_idx}"

        def crawl_page_range(start_page, end_page):
            page_idx = start_page
            while page_idx <= end_page:
                # time.sleep(random.uniform(30, 60))
                max_retries = 20
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        print(f"Worker crawling page {page_idx}")

                        page_url = base_url.format(page_idx=page_idx)
                        self.__check_status_change_proxy()
                        response = requests.get(
                            page_url,
                            headers=self.generate_headers(page_url),
                            proxies=self.__get_random_proxy(),
                        )

                        if response.status_code != 200:
                            retry_count += 1
                            print(
                                f"Error at page {page_idx}: {response.status_code}. Retry {retry_count}/{max_retries}"
                            )
                            continue

                        while "ReturnUrl=" in response.url:
                            self.__pass_capcha(page_url)
                            response = requests.get(
                                page_url,
                                headers=self.generate_headers(page_url),
                                proxies=self.__get_random_proxy(),
                            )

                        soup = BeautifulSoup(response.text, "html.parser")
                        p_tags = soup.find_all("p", class_="nqTitle")
                        page_urls = []

                        for p_tag in p_tags:
                            href = p_tag.find("a")["href"]

                            # Skip Facebook sharer links and other social media links
                            if (
                                "facebook.com/sharer" in href
                                or "twitter.com/share" in href
                            ):
                                continue

                            if href.startswith("https://thuvienphapluat.vn"):
                                page_urls.append(href)
                            else:
                                page_urls.append(f"https://thuvienphapluat.vn{href}")

                        if len(page_urls) == 0:
                            continue

                        # Write URLs directly to file as they're found
                        with open(output_file, "a", encoding="utf-8") as f:
                            for url in page_urls:
                                f.write(
                                    json.dumps({"url": url}, ensure_ascii=False) + "\n"
                                )

                        print(
                            f"Successfully crawled page {page_idx}: Found {len(page_urls)} URLs"
                        )
                        success = True

                    except Exception as e:
                        retry_count += 1
                        print(
                            f"Error at page {page_idx}: {str(e)}. Retry {retry_count}/{max_retries}"
                        )

                if not success:
                    print(
                        f"Failed to crawl page {page_idx} after {max_retries} attempts"
                    )

                page_idx += 1

        # Split work into chunks for multiple workers
        max_pages = en_page - st_page + 1
        chunk_size = max_pages // max_workers

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(max_workers):
                start_page = i * chunk_size + st_page + 1
                end_page = (
                    (i + 1) * chunk_size + st_page if i < max_workers - 1 else en_page
                )
                futures.append(executor.submit(crawl_page_range, start_page, end_page))

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()

        logging.info(f"Crawling completed for pages {st_page} to {en_page}")
        print(f"Crawling completed for pages {st_page} to {en_page}")

        # Count the total number of URLs in the file
        url_count = 0
        with open(output_file, "r", encoding="utf-8") as f:
            for _ in f:
                url_count += 1

        print(f"Total URLs saved: {url_count}")
        return output_file

    def __get_link_by_keys(
        self, keyword, search_type, page=1, fields=0, folder_cate="", install_all=False
    ):
        if search_type == 1:
            url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={keyword}&area=2&type=0&status=0&lan=1&org=0&signer=0&match=False&sort=1&bdate=12/03/1945&edate=12/03/2025&page={page}"
        elif search_type == 2:
            url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={keyword}&area=2&type=0&status=100&lan=1&org=0&signer=0&match=False&sort=1&bdate=12/03/1945&edate=12/03/2025&page={page}"
        elif search_type == 3:
            url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={keyword}&area=2&type=3&status=0&lan=1&org=0&signer=0&match=False&sort=1&bdate=12/03/1945&edate=12/03/2025&page={page}"
        elif search_type == 4:
            url = f"https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={keyword}&area=2&type=39&status=0&lan=1&org=0&signer=0&match=False&sort=1&bdate=12/03/1945&edate=12/03/2025&page={page}"

        if install_all == False:
            url = f"https://thuvienphapluat.vn/page/searchlegal.aspx?keyword=&area=0&match=True&type=0&status=1&signer=0&sort=1&lan=1&scan=0&org=0&fields={fields}&chlbg=21/03/1945&chlend=21/03/2035&page={page}"

        if int(fields) > 0:
            url = f"{url}&fields={fields}"

        if page == 0:
            return []

        if folder_cate != "":
            # readfile folder_cate / page_{page}.json
            data = []
            try:
                with open(
                    f"{self.data_path}/{self.folder_map[search_type]}/{folder_cate}/page_{page}.json",
                    "r",
                    encoding="utf-8",
                ) as f:
                    data = json.load(f)
                if len(data) > 0:
                    return data
            except:
                pass

        retries = 3
        for attempt in range(retries):
            try:
                self.__check_status_change_proxy()
                response = requests.get(
                    url,
                    timeout=30,
                    headers=self.generate_headers(url),
                    proxies=self.__get_random_proxy(),
                )
                if response.status_code != 200:
                    logging.warning(
                        f"Failed {url} with status {response.status_code}. Attempt {attempt+1}/{retries}"
                    )
                    time.sleep(random.uniform(1, 3))
                    continue

                if "ReturnUrl=" in response.url:
                    self.__pass_capcha(url)
                    continue

                soup = BeautifulSoup(response.content, "html.parser")

                data_links = []
                links = soup.find_all("p", class_="nqTitle")
                index_data = soup.find_all("div", class_="number")

                for idx in range(len(links)):
                    link = links[idx]
                    index_text = index_data[idx].get_text().strip()
                    title = link.get_text().strip()
                    href = link.find("a")["href"]
                    data_links.append(
                        {"index": index_text, "title": title, "href": href}
                    )

                if len(data_links) == 0:
                    continue

                # time.sleep(1)
                if folder_cate != "":
                    with open(
                        f"{self.data_path}/{self.folder_map[search_type]}/{folder_cate}/page_{page}.json",
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(data_links, f, ensure_ascii=False, indent=4)
                return data_links

            except Exception as e:
                logging.warning(
                    f"Failed {url} with exception {e}. Attempt {attempt+1}/{retries}"
                )
                time.sleep(random.uniform(1, 3))
        return []

    def craw_luocdo(self, referer_url):
        try:
            idx = referer_url.split("-")[-1].split(".")[0]
            url = f"https://thuvienphapluat.vn/AjaxLoadData/LoadLuocDo.aspx?LawID={idx}&IstraiNghiem=False"

            headers = self.generate_headers(referer_url)

            self.__check_status_change_proxy()
            response = requests.get(
                url, headers=headers, timeout=30, proxies=self.__get_random_proxy()
            )
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            main_content = soup.find("div", id="cmDiagramPrint")

            main_content["class"] = ["vbLuocdo"]
            return main_content
        except Exception as e:
            logging.error(f"Errors: {e}. page={url}")
            return None

    def craw_hieu_luc(self, referer_url):
        for attempt in range(5):
            idx = referer_url.split("-")[-1].split(".")[0]
            url = f"https://thuvienphapluat.vn/AjaxLoadData/LoadLQHL.aspx?LawID={idx}"

            headers = self.generate_headers(referer_url)

            self.__check_status_change_proxy()
            response = requests.get(
                url, headers=headers, timeout=30, proxies=self.__get_random_proxy()
            )

            if response.status_code != 200:
                logging.error(
                    f"Failed to get page={url} with status {response.status_code}. Attempt {attempt+1}/5"
                )
                time.sleep(random.uniform(1, 3))
                continue

            return response.text
        return None

    def craw_noi_dung(self, referer_url):
        for attempt in range(5):
            idx = referer_url.split("-")[-1].split(".")[0]
            url = f"https://thuvienphapluat.vn/AjaxLoadData/LoadLQND.aspx?LawID={idx}"

            headers = self.generate_headers(referer_url)

            self.__check_status_change_proxy()
            response = requests.get(
                url, headers=headers, timeout=30, proxies=self.__get_random_proxy()
            )

            if response.status_code != 200:
                logging.error(
                    f"Failed to get page={url} with status {response.status_code}. Attempt {attempt+1}/5"
                )
                continue

            return response.text
        return None

    def craw_toanvan(self, url):
        try:
            self.__check_status_change_proxy()
            response = requests.get(
                url,
                timeout=30,
                headers=self.generate_headers(url),
                proxies=self.__get_random_proxy(),
            )

            if response.status_code != 200:
                return None, None

            if "ReturnUrl=" in response.url:
                self.__pass_capcha(url)
                return None, None

            soup = BeautifulSoup(response.content, "html.parser")

            try:
                scripts = soup.find_all("script", type="text/javascript")
                for script in scripts:
                    if "__urldl" in script.text:
                        match = re.search(r"__urldl = '(.+)'", script.text)
                        if match:
                            pdf_url = match.group(1)
                            break

                pdf_url = pdf_url.split("&part")[0]
                all_links = []
                all_links.append(f"{pdf_url}&part=-100")
                all_links.append(f"{pdf_url}&part=-1")
                all_links.append(f"{pdf_url}&part=0")
            except:
                idx = url.split("-")[-1].split(".")[0]
                os.makedirs("./missing_url", exist_ok=True)
                with open(f"./missing_url/{idx}.html", "w") as f:
                    f.write(str(soup))
                all_links = []

            return soup, all_links

        except Exception as e:
            logging.error(f"Error toanvan: {e}. page={url}")
            return None, None

    def craw_all_vanban(
        self,
        keyword,
        search_type,
        max_workers=5,
        fields=0,
        folder_cate="",
        total=0,
        install_all=False,
    ):
        links = []
        old_page_error = 0
        total = int(total)

        def get_links_for_page_range(worker_id, page_start, page_end, install_all):
            nonlocal old_page_error, links
            worker_links = []

            for page in range(page_start, page_end):
                # Scrape the page with the current driver
                data_links = self.__get_link_by_keys(
                    keyword, search_type, page, fields, folder_cate, install_all
                )

                if len(data_links) == 0:
                    old_page_error = old_page_error + 1
                else:
                    worker_links.extend(data_links)
                    old_page_error = 0

                print(f"Page {page}")

            # Once all pages for this worker are scraped, append the results
            links.extend(worker_links)
            # Quit the driver after processing all pages for this worker

        # Number of pages each worker should process
        pages_per_worker = round(total / 20) + 1
        pages = [i for i in range(pages_per_worker)]

        # Distribute the work across workers (assign chunks of pages to each worker)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Divide the pages into roughly equal parts for each worker
            chunk_size = len(pages) // max_workers
            for worker_id in range(max_workers):
                # Calculate the range of pages for this worker
                start_page = worker_id * chunk_size
                # Ensure the last worker handles any remaining pages
                end_page = (
                    (worker_id + 1) * chunk_size
                    if worker_id < max_workers - 1
                    else len(pages)
                )

                # Submit the task for each worker
                futures.append(
                    executor.submit(
                        get_links_for_page_range,
                        worker_id,
                        start_page,
                        end_page,
                        install_all,
                    )
                )

            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # Ensure any exception in threads is raised
                except Exception as e:
                    print(f"Error occurred: {e}")

        return links

    def download_pdf(self, pdf_url, folder_save_file):
        final_arr = []
        index = 0
        while index < len(pdf_url):
            url = pdf_url[index]
            _link = "https://thuvienphapluat.vn" + url
            headers = {
                "authority": "luatvietnam.vn",
                "method": "GET",
                "scheme": "https",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9,vi;q=0.8",
                "cookie": self.cookies,
                "priority": "u=0, i",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": random.choice(self.user_agents),
            }

            self.__check_status_change_proxy()
            response = requests.get(
                _link,
                headers=headers,
                allow_redirects=True,
                timeout=30,
                proxies=self.__get_random_proxy(),
            )

            if "ReturnUrl=" in response.url:
                self.__pass_capcha(url)
                response = requests.get(
                    _link,
                    headers=headers,
                    allow_redirects=True,
                    timeout=30,
                    proxies=self.__get_random_proxy(),
                )

            if response.status_code != 200:
                time.sleep(1)
                self.__check_status_change_proxy()
                response = requests.get(
                    _link,
                    headers=headers,
                    allow_redirects=True,
                    timeout=30,
                    proxies=self.__get_random_proxy(),
                )

            try:
                if response.status_code == 200:
                    url = response.url
                    file_name = url.split("/")[-1]
                    file_name = file_name.split("?")[0]
                    file_path = f"{folder_save_file}/{file_name}"
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    final_arr.append(
                        {
                            "original_url": _link,
                            "url": url,
                            "file_name": file_name,
                        }
                    )
                else:
                    final_arr.append(
                        {
                            "original_url": _link,
                            "url": None,
                            "file_name": None,
                            "status": response.status_code,
                        }
                    )
            except Exception as e:
                final_arr.append(
                    {
                        "original_url": _link,
                        "url": None,
                        "file_name": None,
                        "status": response.status_code,
                    }
                )
            index = index + 1
        return final_arr

    def save_files(
        self,
        toanvan,
        luocdo,
        pdf_url,
        hieu_luc,
        lq_noidung,
        main_folder,
        id_data,
        href,
        fields,
    ):
        os.makedirs(main_folder, exist_ok=True)

        soup = luocdo
        viewingDocument = soup.find("div", id="viewingDocument")

        attrs = viewingDocument.find_all("div", class_="att")
        data = {}

        try:
            data["title"] = viewingDocument.find("div", class_="tt").text
            data["title"] = data["title"].strip()
            for attr in attrs:
                key = attr.find("div", class_="hd").text
                value = attr.find("div", class_="ds").text
                key = key.strip()
                key = self.__convert_vietnamese(key)
                value = value.strip()
                data[key] = value

            data["href"] = href
            data["folder_name"] = id_data

            if data.get("ngay_hieu_luc") and data["ngay_hieu_luc"].lower() == "đã biết":
                raise Exception("Account is logged out: ", href)

            folder_cate = self._get_folder_name(str(fields))
            folder_save_file = f"{main_folder}/all_data/{folder_cate}/{id_data}"
            folder_save_pdf = f"{main_folder}/all_data/{folder_cate}/{id_data}/bin"
            folder_save_json = f"{main_folder}/json_luoc_do/{folder_cate}"

            os.makedirs(folder_save_file, exist_ok=True)
            os.makedirs(folder_save_pdf, exist_ok=True)
            os.makedirs(folder_save_json, exist_ok=True)

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(self.download_pdf, [url], folder_save_pdf)
                    for url in pdf_url
                ]
                results = [future.result() for future in as_completed(futures)]
                data["files"] = [item for sublist in results for item in sublist]

            if len(data["files"]) == 0:
                raise Exception(
                    f"Failed to download pdf | url: {href} | pdf_url: {pdf_url}"
                )

            with open(f"{folder_save_file}/ndung.html", "w", encoding="utf-8") as f:
                f.write(str(toanvan))

            with open(f"{folder_save_file}/lqhc.html", "w", encoding="utf-8") as f:
                f.write(str(hieu_luc))

            with open(f"{folder_save_file}/lqnd.html", "w", encoding="utf-8") as f:
                f.write(str(lq_noidung))

            with open(f"{folder_save_file}/luocdo.html", "w", encoding="utf-8") as f:
                f.write(str(luocdo))

            with open(f"{folder_save_json}/{id_data}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.dowload_success_count = self.dowload_success_count + 1

            return data
        except Exception as e:
            logging.error(f"Error save: {e}")
            return False

    def verify_login(self):
        url = "https://thuvienphapluat.vn/page/profile.aspx"
        headers = self.generate_headers(url)
        self.__check_status_change_proxy()
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
            proxies=self.__get_random_proxy(),
        )
        return response.url == url

    def craw_some_data(self, array_data, folder_save_file):
        errors_data = []

        for law_index in tqdm(range(len(array_data)), desc="Processing laws"):

            data_law = array_data[law_index]
            title_data = data_law["So"]

            links = self.__get_link_by_keys(title_data, 1)

            data_law["links"] = links

            _folder_save_file = f"{folder_save_file}/{data_law['path']}"

            if len(data_law["links"]) > 0:
                href = data_law["links"][0]["href"]
                for error in data_law["errors"]:
                    file_path = f"{_folder_save_file}/{data_law['ItemID']}/{error}.html"

                    if os.path.exists(file_path):
                        continue
                    else:
                        if error == "toan_van":
                            html, link_download = self.craw_toanvan(href)
                        elif error == "thuoc_tinh":
                            html, link_download = self.craw_toanvan(href)
                        elif error == "lich_su":
                            html = None
                        elif error == "vb_lien_quan":
                            html = self.craw_noi_dung(href)
                        elif error == "luoc_do":
                            html = self.craw_luocdo(href)

                        if html:
                            folder = f"{_folder_save_file}/{data_law['ItemID']}"
                            os.makedirs(folder, exist_ok=True)
                            with open(
                                f"{folder}/{error}.html", "w", encoding="utf-8"
                            ) as f:
                                f.write(str(html))
                        else:
                            errors_data.append(
                                {
                                    "name": data_law["name"],
                                    "ItemID": data_law["ItemID"],
                                    "error": error,
                                }
                            )

        os.makedirs(_folder_save_file, exist_ok=True)

        with open(f"{_folder_save_file}/error_link.json", "w", encoding="utf-8") as f:
            json.dump(errors_data, f, ensure_ascii=False, indent=4)

        with open(f"./error_link.json", "w", encoding="utf-8") as f:
            json.dump(errors_data, f, ensure_ascii=False, indent=4)

        self.driver.quit()

    def craw_all_data(
        self,
        search_type,
        max_workers=5,
        reload=True,
        keyword="",
        category=None,
        install_all=False,
    ):
        fields = category["fields"]
        total_fields = int(category["total"])
        links = []
        main_folder = f"{self.data_path}/{self.folder_map[search_type]}"
        os.makedirs(main_folder, exist_ok=True)

        folder_cate = self._get_folder_name(str(fields))
        try:
            if folder_cate != "":
                os.makedirs(f"{main_folder}/{folder_cate}", exist_ok=True)
                with open(
                    f"{main_folder}/{folder_cate}/links.json", "r", encoding="utf-8"
                ) as f:
                    links = json.load(f)
            else:
                with open(f"{main_folder}/links.json", "r", encoding="utf-8") as f:
                    links = json.load(f)
        except:
            links = []

        if len(keyword) == 0:
            if reload or len(links) == 0:
                links = self.craw_all_vanban(
                    "",
                    search_type,
                    max_workers,
                    fields=fields,
                    folder_cate=folder_cate,
                    total=total_fields,
                    install_all=install_all,
                )
        else:
            pass

        all_data_error = []

        try:
            all_json_files = os.listdir(f"{main_folder}/json_luoc_do/{folder_cate}")
            all_json_files = [file.split(".")[0] for file in all_json_files]
        except:
            all_json_files = []

        all_json_files = set(all_json_files)

        if folder_cate != "":
            with open(
                f"{main_folder}/{folder_cate}/links.json", "w", encoding="utf-8"
            ) as f:
                json.dump(links, f, ensure_ascii=False, indent=4)
        else:
            with open(f"{main_folder}/links.json", "w", encoding="utf-8") as f:
                json.dump(links, f, ensure_ascii=False, indent=4)

        def process_link(link):
            try:
                idx = link["href"].split("-")[-1].split(".")[0]

                id_data = f"{idx}"

                if id_data in all_json_files:
                    return None

                for attempt in range(3):
                    try:
                        toanvan, pdf_url = self.craw_toanvan(link["href"])
                    except Exception as e:
                        logging.error(
                            f"Error toanvan: {e} at link {link['href']}. Attempt {attempt+1}/5"
                        )
                        time.sleep(random.uniform(1, 3))
                        continue

                    if toanvan is not None and len(pdf_url) > 0:
                        break

                hieu_luc = self.craw_hieu_luc(link["href"])
                lq_noidung = self.craw_noi_dung(link["href"])

                for attempt in range(5):
                    try:
                        luocdo = self.craw_luocdo(link["href"])
                    except Exception as e:
                        logging.error(
                            f"Error luocdo: {e} at link {link['href']}. Attempt {attempt+1}/5"
                        )
                        time.sleep(random.uniform(1, 3))
                        continue

                    if luocdo is None:
                        break

                if (
                    toanvan is None
                    or luocdo is None
                    or hieu_luc is None
                    or lq_noidung is None
                ):
                    missing_data = []
                    if toanvan is None:
                        missing_data.append("toanvan")
                    if luocdo is None:
                        missing_data.append("luocdo")
                    if hieu_luc is None:
                        missing_data.append("hieu_luc")
                    if lq_noidung is None:
                        missing_data.append("lq_noidung")

                    missing_data = ", ".join(missing_data)
                    logging.error(f"Failed to get data from {link['href']}")
                    all_data_error.append(
                        {
                            "key": idx,
                            "message": f"Failed to get data: {missing_data}",
                            "href": link["href"],
                        }
                    )
                    return None

                try:
                    status = self.save_files(
                        toanvan,
                        luocdo,
                        pdf_url,
                        hieu_luc,
                        lq_noidung,
                        main_folder,
                        id_data,
                        link["href"],
                        fields,
                    )
                except Exception as e:
                    logging.error(f"Error savefile: {e} at link {link['href']}")
                    all_data_error.append(
                        {
                            "key": idx,
                            "message": "Failed to save data | e: {e}",
                            "href": link["href"],
                        }
                    )
                    return None
                if status is False:
                    all_data_error.append(
                        {
                            "key": idx,
                            "message": "Failed to save data",
                            "href": link["href"],
                        }
                    )
                    return None

                return {
                    "href": link["href"],
                    "folder": id_data,
                    "loai_van_ban": status["loai_van_ban"],
                    "linh_vuc_nganh": status["linh_vuc_nganh"],
                    "so_hieu": status["so_hieu"],
                }
            except Exception as e:
                logging.error(f"Error process link: {e} at link {link['href']}")
                all_data_error.append(
                    {
                        "key": idx,
                        "message": "Failed to get data | e: {e}",
                        "href": link["href"],
                    }
                )
                return None

        self.download_count = 0
        self.dowload_success_count = 0

        def passing_data(links_process, all_json_files):
            need_download = []

            for link_index in range(len(links_process)):
                link = links_process[link_index]
                idx = link["href"].split("-")[-1].split(".")[0]
                id_data = f"{idx}"
                if id_data not in all_json_files:
                    need_download.append(link)

            return need_download

        def dowload_selenium(links_process):

            for link_index in range(len(links_process)):
                link = links_process[link_index]
                start_time = time.time()

                process_link(link)

                if link_index % random.randint(7, 12) == 0:
                    time.sleep(random.uniform(1, 3))

                total_time = time.time() - start_time
                total_time = round(total_time, 2)
                self.download_count = self.download_count + 1
                percent = round((self.download_count / len(links)) * 100, 2)
                print(
                    f"Downloaded: {self.download_count}/{len(links)} | {percent}% | Time: {total_time}s | Done: {self.dowload_success_count} links"
                )

        max_workers = 8

        self.download_count = 0

        link_need_download = passing_data(links, all_json_files)

        if len(link_need_download) == 0:
            print("DONT NEED DOWNLOAD")
            return

        self.download_count = len(links) - len(link_need_download)
        self.dowload_success_count = self.download_count

        split_array = self.split_array(link_need_download, max_workers, passing=0)

        print("NEED DOWNLOAD: ", len(link_need_download))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(max_workers):
                executor.submit(dowload_selenium, split_array[i])

        if folder_cate != "":
            with open(
                f"{main_folder}/{folder_cate}/all_data_error.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(all_data_error, f, ensure_ascii=False, indent=4)
        else:
            with open(f"{main_folder}/all_data_error.json", "w", encoding="utf-8") as f:
                json.dump(all_data_error, f, ensure_ascii=False, indent=4)

        print("DONE")
        return all_data_error
