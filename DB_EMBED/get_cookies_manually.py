"""
Manual Cookie Extraction Script
Run this script, it will open a browser window.
You manually login to the website, then the script will save the cookies.
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

print("=" * 70)
print("MANUAL COOKIE EXTRACTION")
print("=" * 70)
print("\nInstructions:")
print("1. A browser window will open")
print("2. Navigate to thuvienphapluat.vn and login manually")
print("3. Click through any Cloudflare challenges")
print("4. Once you're logged in, press ENTER in this terminal")
print("5. The script will save your cookies")
print("=" * 70)
input("\nPress ENTER to start the browser...")

# Start undetected Chrome
print("\n[STEP] Starting Chrome browser...")
driver = uc.Chrome(version_main=None)

try:
    print("[STEP] Navigating to login page...")
    driver.get(
        "https://thuvienphapluat.vn/page/login.aspx?ReturnUrl=%2fpage%2fprofile.aspx"
    )

    print("\n" + "=" * 70)
    print("👉 PLEASE LOGIN MANUALLY IN THE BROWSER WINDOW")
    print("👉 Click through Cloudflare if it appears")
    print("👉 Enter your username and password")
    print("👉 Complete the login")
    print("=" * 70)

    input("\nPress ENTER after you have successfully logged in...")

    print("\n[STEP] Extracting cookies...")
    cookies = driver.get_cookies()
    cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    print("[STEP] Saving cookies to file...")
    with open("./cookie.txt", "w") as f:
        f.write(cookie_string)

    print("\n" + "=" * 70)
    print("✅ SUCCESS! Cookies saved to cookie.txt")
    print("=" * 70)
    print("\nYou can now run your crawling scripts!")
    print("They will use the saved cookies to bypass login.")

finally:
    print("\n[STEP] Closing browser...")
    driver.quit()
    print("[INFO] Done!")
