import csv
import time
import re
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

# ── Selenium ──────────────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ── TikTok ────────────────────────────────────────────────────────────────────
from TikTokApi import TikTokApi

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
INPUT_FILE  = "url.txt"
OUTPUT_FILE = "master_output.csv"
FIELDNAMES = [
    "Platform", "URL", "Author", "Heading", "Views", "Engagement",
    "Likes", "Comments", "Retweets_Shares", "Reactions", "Createtime",
]

# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def extract_numbers(text: str) -> int:
    if not text or not isinstance(text, str): return 0
    text = text.replace(",", "").strip()
    match = re.search(r"(\d+\.?\d*)([KM]?)", text, re.IGNORECASE)
    if match:
        num, unit = float(match.group(1)), match.group(2).upper()
        multiplier = {"K": 1000, "M": 1000000}.get(unit, 1)
        return int(num * multiplier)
    return 0

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # เพิ่ม User-Agent เพื่อลดโอกาสโดน Block
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING LOGIC (ENHANCED)
# ─────────────────────────────────────────────────────────────────────────────

def scrape_selenium_task(url):
    """ฟังก์ชันกลางสำหรับคัดกรอง Platform และจัดการ Selenium Driver รายตัว"""
    platform = "Facebook" if "facebook.com" in url or "fb.watch" in url else "Twitter"
    driver = get_driver()
    wait = WebDriverWait(driver, 15)
    row = {f: "" for f in FIELDNAMES}
    row.update({"Platform": platform, "URL": url})

    try:
        driver.get(url)
        if platform == "Twitter":
            # ใช้ Wait แทนการ time.sleep เพื่อความเร็ว
            elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")))
            vals = [e.text for e in elements if e.text.strip()]
            row["Views"] = extract_numbers(vals[0]) if len(vals) > 0 else 0
            row["Comments"] = extract_numbers(vals[1]) if len(vals) > 1 else 0
            row["Retweets_Shares"] = extract_numbers(vals[2]) if len(vals) > 2 else 0
            row["Likes"] = extract_numbers(vals[3]) if len(vals) > 3 else 0
            row["Engagement"] = row["Comments"] + row["Retweets_Shares"] + row["Likes"]
            
        elif platform == "Facebook":
            # ปรับปรุง Logic การดึงข้อมูล FB ให้ยืดหยุ่นขึ้น
            time.sleep(3) # FB มักต้องการเวลาโหลดมากกว่าปกติ
            try:
                row["Views"] = extract_numbers(driver.find_element(By.XPATH, "//span[contains(text(), 'Views')]|//span[contains(@class, '_26fq')]").text)
            except: row["Views"] = 0
            # ... (ใส่ Logic การดึง Reaction/Comment เพิ่มเติมได้ที่นี่)
            
        print(f"✅ {platform} Success: {url}")
    except Exception as e:
        print(f"❌ {platform} Error {url}: {str(e)[:50]}")
    finally:
        driver.quit()
    return row

async def scrape_tiktok_batch(urls):
    results = []
    async with TikTokApi() as api:
        await api.create_sessions(
    ms_tokens=[os.environ.get("ms_token")], 
    num_sessions=1, 
    sleep_after=2,
    headless=True,
    override_browser_args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-zygote",
        "--single-process"
    ]
)
        for url in urls:
            row = {f: "" for f in FIELDNAMES}
            row.update({"Platform": "TikTok", "URL": url})
            try:
                video = api.video(url=url)
                info = await video.info()
                s = info.get("stats", {})
                row.update({
                    "Views": s.get("playCount", 0),
                    "Likes": s.get("diggCount", 0),
                    "Comments": s.get("commentCount", 0),
                    "Retweets_Shares": s.get("shareCount", 0),
                    "Engagement": s.get("diggCount", 0) + s.get("commentCount", 0) + s.get("shareCount", 0),
                    "Author": info["author"].get("uniqueId", ""),
                    "Heading": info.get("desc", "")[:100] # ตัดให้สั้นลงเพื่อประหยัดพื้นที่ CSV
                })
                print(f"✅ TikTok Success: {url}")
            except Exception as e:
                print(f"❌ TikTok Error {url}: {e}")
            results.append(row)
    return results

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    with open(INPUT_FILE, "r") as f:
        urls = [line.strip().split()[-1] for line in f if line.strip()] # Clean URL จาก source tags

    # แยกกลุ่ม URL
    selenium_urls = [u for u in urls if "tiktok.com" not in u]
    tiktok_urls = [u for u in urls if "tiktok.com" in u]

    final_data = []

    # 1. รัน Selenium แบบ Parallel (Multi-threading) เพื่อความเร็ว
    if selenium_urls:
        print(f"🚀 Starting Selenium Tasks ({len(selenium_urls)} URLs)...")
        with ThreadPoolExecutor(max_workers=1) as executor:
            final_data.extend(list(executor.map(scrape_selenium_task, selenium_urls)))

    # 2. รัน TikTok
    if tiktok_urls:
        print(f"🚀 Starting TikTok Tasks ({len(tiktok_urls)} URLs)...")
        final_data.extend(asyncio.run(scrape_tiktok_batch(tiktok_urls)))

    # 3. Save to CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f: # ใช้ utf-8-sig เพื่อให้ Excel อ่านภาษาไทยออก
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()
        writer.writerows(final_data)
    print(f"✨ Master Report Generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()