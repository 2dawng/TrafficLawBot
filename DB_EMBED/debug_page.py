"""Debug script to see what's on the page"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/luat-giao-thong-2025-va-cac-nghi-dinh-thong-tu-huong-dan-moi-nhat-luat-giao-thong-2025-gom-cac-luat-939767-198964.html"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

print(f"Status: {response.status_code}")
print(f"\n=== All <a> tags with href ===")

count = 0
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)[:80]
    full_url = urljoin(url, href)

    # Check if it's a document link
    if (
        "/van-ban/" in full_url
        or "/nghi-dinh/" in full_url
        or "/thong-tu/" in full_url
        or "/luat/" in full_url
    ):
        count += 1
        print(f"\n{count}. {text}")
        print(f"   URL: {full_url}")

print(f"\n\nTotal document links found: {count}")
