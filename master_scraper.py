import csv
import time
import re
import asyncio
import os
import requests
from concurrent.futures import ThreadPoolExecutor

# ── Selenium ──────────────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── TikTok ────────────────────────────────────────────────────────────────────
from TikTokApi import TikTokApi

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
INPUT_FILE  = "url.txt"
OUTPUT_FILE = "master_output.csv"
YOUTUBE_API_KEY = "AIzaSyBcxyU9ZXsqNQrm7M2rTxInzZb5wNY1iqY" # API Key ของคุณ

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
    # รองรับตัวเลขทศนิยมและหน่วย K, M
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
    
    # สำหรับ Streamlit Cloud
    chrome_options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

# ─────────────────────────────────────────────────────────────────────────────
# YOUTUBE API LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def extract_youtube_id(url):
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"shorts\/([0-9A-Za-z_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def scrape_youtube_api(url):
    video_id = extract_youtube_id(url)
    
    # เซ็ตค่าเริ่มต้นให้เป็น String เพื่อไม่ให้ PyArrow พังไปก่อนที่เราจะเห็น Error
    row = {
        "Platform": "YouTube", "URL": url, "Author": "", "Heading": "", "Createtime": "",
        "Views": 0, "Engagement": 0, "Likes": 0, "Comments": 0, "Retweets_Shares": 0, "Reactions": 0
    }
    
    if not video_id: 
        row["Heading"] = "ERROR: หา Video ID ไม่เจอ"
        return row

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    try:
        # ยิง API และดึงค่าเป็น JSON
        res = requests.get(api_url).json()
        
        if "items" in res and res["items"]:
            # กรณีสำเร็จ ดึงข้อมูลตามปกติ
            item = res["items"][0]
            s = item.get("statistics", {})
            snip = item.get("snippet", {})
            row.update({
                "Views": int(s.get("viewCount", 0)),
                "Likes": int(s.get("likeCount", 0)),
                "Comments": int(s.get("commentCount", 0)),
                "Author": snip.get("channelTitle", ""),
                "Heading": snip.get("title", ""),
                "Createtime": snip.get("publishedAt", "").split("T")[0],
                "Engagement": int(s.get("likeCount", 0)) + int(s.get("commentCount", 0))
            })
            print(f"✅ YouTube Success: {url}")
            
        else:
            # 🔴 กรณีล้มเหลว: ดึงข้อความ Error จาก Google มายัดใส่คอลัมน์ Heading
            error_msg = res.get("error", {}).get("message", "Unknown API Error")
            print(f"🔴 YOUTUBE RAW ERROR: {res}") # ปรินต์ทิ้งไว้ใน Logs ด้วย
            
            row["Author"] = "API_BLOCKED"
            row["Heading"] = f"GOOGLE ERROR: {error_msg}"
            
    except Exception as e: 
        row["Heading"] = f"REQUEST ERROR: {e}"
        print(f"❌ YouTube Request Error: {e}")
        
    return row

# ─────────────────────────────────────────────────────────────────────────────
# SELENIUM LOGIC (FB / TWITTER)
# ─────────────────────────────────────────────────────────────────────────────

def scrape_selenium_task(url):
    platform = "Facebook" if "facebook.com" in url or "fb.watch" in url else "Twitter"
    driver = get_driver()
    wait = WebDriverWait(driver, 15)
    row = {f: 0 for f in FIELDNAMES}
    row.update({"Platform": platform, "URL": url})

    try:
        driver.get(url)
        if platform == "Twitter":
            # ใช้การดึง Class แบบเดิมที่เสถียรสำหรับคุณ แต่เพิ่ม Logic แยก Views
            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")))
            time.sleep(2)
            elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")
            vals = [e.text for e in elements if e.text.strip()]
            
            if len(vals) >= 4:
                row["Views"] = extract_numbers(vals[0])
                row["Comments"] = extract_numbers(vals[1])
                row["Retweets_Shares"] = extract_numbers(vals[2])
                row["Likes"] = extract_numbers(vals[3])
            row["Engagement"] = row["Comments"] + row["Retweets_Shares"] + row["Likes"]
            
        elif platform == "Facebook":
            time.sleep(2) # Facebook ต้องรอให้ตัวเลข Animation วิ่งเสร็จ
            
            if "/videos" in url or "/watch" in url:
                # กรณีเป็น Video
                try:
                    v_text = driver.find_element(By.XPATH, "//span[contains(@class, '_26fq')]|//span[contains(text(), 'Views')]").text
                    row["Views"] = extract_numbers(v_text)
                except: row["Views"] = 0
                
                try:
                    # พยายามหา Reaction ใน Video
                    r_text = driver.find_element(By.XPATH, "//div[contains(@class, 'x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x1n2onr6 x87ps6o x1lku1pv x1a2a7pz x1heor9g x78zum5 x6ikm8r x10wlt62')]").text
                    row["Likes"] = extract_numbers(r_text)
                except: row["Likes"] = 0
            else:
                # กรณีเป็น Post ปกติ (Photo/Link)
                try:
                    r_text = driver.find_element(By.XPATH, "//div[contains(@class, 'x9f619') and contains(text(), 'All reactions:')]/following-sibling::span").text
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

# ─────────────────────────────────────────────────────────────────────────────
# TIKTOK LOGIC (ASYNC)
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_tiktok_batch(urls):
    results = []
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[os.environ.get("ms_token")], num_sessions=1, sleep_after=2, headless=True)
        for url in urls:
            row = {f: 0 for f in FIELDNAMES}
            row.update({"Platform": "TikTok", "URL": url})
            try:
                video = api.video(url=url)
                info = await video.info()
                s = info.get("stats", {})
                row.update({
                    "Views": s.get("playCount", 0), "Likes": s.get("diggCount", 0),
                    "Comments": s.get("commentCount", 0), "Retweets_Shares": s.get("shareCount", 0),
                    "Author": info["author"].get("uniqueId", ""), "Heading": info.get("desc", "")[:100],
                    "Engagement": s.get("diggCount", 0) + s.get("commentCount", 0) + s.get("shareCount", 0)
                })
            except Exception as e: print(f"❌ TikTok Error: {e}")
            results.append(row)
    return results

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    with open(INPUT_FILE, "r") as f:
        urls = [line.strip().split()[-1] for line in f if line.strip()]

    yt_urls = [u for u in urls if "youtube.com" in u or "youtu.be" in u]
    tt_urls = [u for u in urls if "tiktok.com" in u]
    sel_urls = [u for u in urls if u not in yt_urls and u not in tt_urls]

    final_data = []

    if yt_urls:
        with ThreadPoolExecutor(max_workers=1) as exec:
            final_data.extend(list(exec.map(scrape_youtube_api, yt_urls)))

    if sel_urls:
        with ThreadPoolExecutor(max_workers=1) as exec:
            final_data.extend(list(exec.map(scrape_selenium_task, sel_urls)))

    if tt_urls:
        final_data.extend(asyncio.run(scrape_tiktok_batch(tt_urls)))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()
        writer.writerows(final_data)
    print(f"✨ Master Report Generated!")

if __name__ == "__main__":
    main()