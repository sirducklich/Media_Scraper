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
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 1. ชี้เป้าไปที่ตำแหน่งของโปรแกรม Chromium บน Streamlit Cloud
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # 2. ชี้เป้าไปที่ตำแหน่งของ ChromeDriver บน Streamlit Cloud ตรงๆ
    service = Service("/usr/bin/chromedriver")
    
    # ลบการใช้งาน ChromeDriverManager().install() ออกไปเลย
    return webdriver.Chrome(service=service, options=chrome_options)

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING LOGIC (ENHANCED)
# ─────────────────────────────────────────────────────────────────────────────

def scrape_selenium_task(url):
    """ฟังก์ชันกลางสำหรับคัดกรอง Platform และจัดการ Selenium Driver รายตัว"""
    # แยกประเภท Platform
    if "facebook.com" in url or "fb.watch" in url:
        platform = "Facebook"
    elif "x.com" in url or "twitter.com" in url:
        platform = "Twitter"
    else:
        return None

    driver = get_driver()
    # เพิ่มความเร็วโดยการตั้งค่า Wait ที่เหมาะสม
    wait = WebDriverWait(driver, 15) 
    row = {f: 0 for f in FIELDNAMES} # Default เป็น 0 ทั้งหมดเพื่อป้องกัน Error ตอนบวกเลข
    row.update({"Platform": platform, "URL": url})

    try:
        driver.get(url)
        
        # --- LOGIC: TWITTER ---
        if platform == "Twitter":
            wait.until(EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']")))
            
            def get_tw_stat(testid):
                try:
                    return driver.find_element(By.XPATH, f"//div[@data-testid='{testid}']").text
                except: return "0"

            # ดึงค่าผ่าน Data-TestID (แม่นยำที่สุด)
            row["Views"] = extract_numbers(get_tw_stat("app_text_transition_container"))
            row["Comments"] = extract_numbers(get_tw_stat("reply"))
            row["Retweets_Shares"] = extract_numbers(get_tw_stat("retweet"))
            row["Likes"] = extract_numbers(get_tw_stat("like"))
            row["Engagement"] = row["Comments"] + row["Retweets_Shares"] + row["Likes"]

        # --- LOGIC: FACEBOOK (เสริมจากโค้ดที่คุณให้มา) ---
        elif platform == "Facebook":
            time.sleep(5) # Facebook ต้องรอให้ตัวเลข Animation วิ่งเสร็จ
            
            if "/videos" in url or "/watch" in url:
                # กรณีเป็น Video
                try:
                    v_text = driver.find_element(By.XPATH, "//span[contains(@class, '_26fq')]|//span[contains(text(), 'Views')]").text
                    row["Views"] = extract_numbers(v_text)
                except: row["Views"] = 0
                
                try:
                    # พยายามหา Reaction ใน Video
                    r_text = driver.find_element(By.XPATH, "//div[contains(@aria-label, 'reactions')]|//span[contains(@class, 'xrbp0b2')]").text
                    row["Likes"] = extract_numbers(r_text)
                except: row["Likes"] = 0
            else:
                # กรณีเป็น Post ปกติ (Photo/Link)
                try:
                    r_text = driver.find_element(By.XPATH, "//span[@class='xrbp0b2']|//div[contains(@aria-label, 'Reactions')]").text
                    row["Likes"] = extract_numbers(r_text)
                except: row["Likes"] = 0

            # ดึง Comments และ Shares (มักจะใช้ Class xkrqix3 เหมือนกัน)
            try:
                elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'xkrqix3')]|//div[contains(@data-testid, 'UFI2CommentsCount')]")
                # กรองเอาเฉพาะตัวเลข
                stat_vals = [extract_numbers(e.text) for e in elements if e.text.strip()]
                row["Comments"] = stat_vals[0] if len(stat_vals) > 0 else 0
                row["Retweets_Shares"] = stat_vals[1] if len(stat_vals) > 1 else 0
            except:
                pass

            row["Engagement"] = row["Likes"] + row["Comments"] + row["Retweets_Shares"]

        print(f"✅ {platform} Success: {url}")
        
    except Exception as e:
        print(f"❌ {platform} Error {url}: {str(e)[:100]}")
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