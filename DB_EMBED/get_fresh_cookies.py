"""
Get fresh cookies from thuvienphapluat.vn using undetected Chrome
"""

import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_fresh_cookies():
    """Open Chrome, login, and save cookies"""

    USERNAME = "dawng123"
    PASSWORD = "123456"

    print("[STEP] Setting up undetected Chrome driver...")
    options = uc.ChromeOptions()

    # Use a real user agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"--user-agent={user_agent}")

    print("[STEP] Starting Chrome...")
    driver = uc.Chrome(options=options, version_main=None)

    try:
        print("[STEP] Navigating to login page...")
        login_url = "https://thuvienphapluat.vn/page/login.aspx"
        driver.get(login_url)

        print("[INFO] ⏳ Waiting for page to load...")
        time.sleep(5)

        wait = WebDriverWait(driver, 60)

        print("[STEP] Waiting for login form...")
        wait.until(EC.presence_of_element_located((By.ID, "UserName")))
        print("[STEP] ✅ Login form loaded!")

        print("[STEP] Filling in credentials...")
        driver.find_element(By.ID, "UserName").send_keys(USERNAME)
        driver.find_element(By.ID, "Password").send_keys(PASSWORD)
        driver.find_element(By.ID, "Button1").click()

        print("[STEP] ⏳ Logging in...")
        time.sleep(5)

        # Try to close popup if it appears
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[15]/div[3]/div/button[1]")
                )
            ).click()
            print("[INFO] Closed popup.")
        except:
            print("[INFO] No popup found.")

        # Wait a bit for session to be fully established
        time.sleep(3)

        # Get cookies
        print("[STEP] Getting cookies...")
        cookies = driver.get_cookies()

        # Format cookies for requests library
        cookie_string = "; ".join(
            [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
        )

        # Save to file
        with open("./cookie.txt", "w", encoding="utf-8") as f:
            f.write(cookie_string)

        print("\n" + "=" * 50)
        print("✅ SUCCESS! Cookies saved to cookie.txt")
        print("=" * 50)
        print(f"\nCookies saved ({len(cookies)} cookies):")
        print(
            cookie_string[:200] + "..." if len(cookie_string) > 200 else cookie_string
        )
        print("\n[INFO] You can now run: python scrape_traffic_laws.py")
        print("[INFO] Browser will close in 5 seconds...")
        time.sleep(5)

    except Exception as e:
        print(f"[ERROR] Failed to get cookies: {e}")
        print("[INFO] Browser will stay open for 30 seconds for manual debugging...")
        time.sleep(30)

    finally:
        driver.quit()
        print("[STEP] Browser closed.")


if __name__ == "__main__":
    get_fresh_cookies()
