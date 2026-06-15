import csv
import time
import re
import asyncio
import os
import json  
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
YOUTUBE_API_KEY = "AIzaSyBcxyU9ZXsqNQrm7M2rTxInzZb5wNY1iqY"

FIELDNAMES = [
    "Platform", "URL", "Author", "Heading", "Views", "Engagement",
    "Likes", "Comments", "Shares_Reposts", "Bookmarks", "Createtime",
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
    
    # 🌟 1. บังคับขนาดหน้าจอให้กว้างเป็น Desktop เพื่อให้ XPath ไม่เพี้ยน
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 🌟 2. บังคับให้หน้าเว็บเป็นภาษาอังกฤษเสมอ ป้องกันข้อความภาษาไทยเปลี่ยน
    chrome_options.add_argument("--lang=en-US")
    
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER LOGIC
# ─────────────────────────────────────────────────────────────────────────────

# ── YouTube API ──
def extract_youtube_id(url):
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"shorts\/([0-9A-Za-z_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def scrape_youtube_api(url):
    video_id = extract_youtube_id(url)
    row = {f: 0 for f in FIELDNAMES}
    row.update({"Platform": "YouTube", "URL": url, "Author": "", "Heading": "", "Createtime": ""})
    if not video_id: return row

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    try:
        res = requests.get(api_url).json()
        if "items" in res and res["items"]:
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
    except Exception as e: 
        print(f"❌ YouTube Error: {e}")
    return row

# ── Facebook / X (Selenium) ──
def scrape_selenium_task(url):
    platform = "Facebook" if "facebook.com" in url or "fb.watch" in url else "Twitter"
    driver = get_driver()
    wait = WebDriverWait(driver, 7) # เพิ่มเวลาเผื่อโหลด
    row = {f: 0 for f in FIELDNAMES}
    row.update({"Platform": platform, "URL": url, "Author": "", "Heading": "", "Createtime": ""})

    try:
        if platform == "Twitter":
                    # ตรวจสอบไฟล์คุกกี้ auth.json
                    if os.path.exists("auth.json"):
                        try:
                            driver.get("https://x.com")
                            time.sleep(1)
                            
                            with open("auth.json", "r", encoding="utf-8") as f:
                                cookies = json.load(f)
                                for cookie in cookies:
                                    selenium_cookie = {
                                        "name": cookie["name"],
                                        "value": cookie["value"],
                                        "domain": cookie["domain"],
                                        "path": cookie.get("path", "/"),
                                        "secure": cookie.get("secure", True)
                                    }
                                    if "expirationDate" in cookie and cookie["expirationDate"] is not None:
                                        selenium_cookie["expiry"] = int(cookie["expirationDate"])
                                    
                                    driver.add_cookie(selenium_cookie)
                            
                            print(f"🔑 โหลด Twitter Cookies สำเร็จสำหรับ: {url}")
                        except Exception as ce:
                            print(f"⚠️ ไม่สามารถใส่คุกกี้ Twitter ได้: {ce}")
                    
                    # เปิดลิงก์เป้าหมายจริง
                    driver.get(url)
                    
                    try:
                        # 🌟 รันสิทธิ์ด้วย Class หลักของคุณเหมือนเดิม เพื่อแก้ปัญหาบราวเซอร์จอขาว/Timeout
                        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")))
                        time.sleep(2)
                    except Exception as wait_e:
                        print(f"⚠️ Twitter Timeout (แต่จะพยายามดึงข้อมูลต่อ): {url}")

                    # ─────────────────────────────────────────────────────────────────
                    # 🌟 ท่าเจาะจง: ล็อกเป้าดึงทีละช่อง ถ้าไม่เจอให้ Pass (ข้าม) โดยไม่สลับช่อง
                    # ─────────────────────────────────────────────────────────────────
                    
                    # 1. ยอด Views (ดึงจากลิงก์ Analytics)
                    try: 
                        v_el = driver.find_element(By.XPATH, "//a[contains(@href, '/analytics')]")
                        row["Views"] = extract_numbers(v_el.text)
                    except: pass

                    # 2. ยอด Comments (เจาะจงจากป้าย reply)
                    try: 
                        c_el = driver.find_element(By.XPATH, "//*[@data-testid='reply']")
                        row["Comments"] = extract_numbers(c_el.text)
                    except: pass

                    # 3. ยอด Retweets / Shares (เจาะจงจากป้าย retweet)
                    try: 
                        rt_el = driver.find_element(By.XPATH, "//*[@data-testid='retweet']")
                        row["Shares_Reposts"] = extract_numbers(rt_el.text)
                    except: pass

                    # 4. ยอด Likes (เจาะจงจากป้าย like)
                    try: 
                        l_el = driver.find_element(By.XPATH, "//*[@data-testid='like']")
                        row["Likes"] = extract_numbers(l_el.text)
                    except: pass

                    # 5. ยอด Bookmarks (เจาะจงจากป้าย bookmark)
                    try: 
                        b_el = driver.find_element(By.XPATH, "//*[@data-testid='bookmark']")
                        row["Bookmarks"] = extract_numbers(b_el.text)
                    except: pass

                    # คำนวณยอดรวม Engagement 
                    row["Engagement"] = row["Comments"] + row["Shares_Reposts"] + row["Likes"] + row["Bookmarks"]
            
        elif platform == "Facebook":
            driver.get(url)
            time.sleep(2) # เพิ่มเวลาโหลดเผื่อเน็ตช้า
            if "/videos" in url or "/watch" in url:
                try:
                    v_text = driver.find_element(By.XPATH, "//span[contains(@class, '_26fq')]|//span[contains(text(), 'Views')]").text
                    row["Views"] = extract_numbers(v_text)
                except: row["Views"] = 0
                try:
                    r_text = driver.find_element(By.XPATH, "//div[contains(@class, 'x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x1n2onr6 x87ps6o x1lku1pv x1a2a7pz x1heor9g x78zum5 x6ikm8r x10wlt62')]").text
                    row["Likes"] = extract_numbers(r_text)
                except: row["Likes"] = 0
                
                try:
                    elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'xkrqix3')]|//div[contains(@data-testid, 'UFI2CommentsCount')]")
                    for e in elements:
                        txt = e.text.lower()
                        if "comments" in txt:
                            row["Comments"] = extract_numbers(txt)
                        elif "share" in txt:
                            row["Shares_Reposts"] = extract_numbers(txt) # 🌟 อัปเดตตัวแปรตาม FIELDNAMES
                except: pass
                
            else:
                try:
                    r_text = driver.find_element(By.XPATH, "//div[contains(@class, 'x9f619') and contains(text(), 'All reactions:')]/following-sibling::span").text
                    row["Likes"] = extract_numbers(r_text)
                except: 
                    try:
                        r_text = driver.find_element(By.XPATH, "//span[@class='xrbpy55 x10wh9bi x1wd73v9 x1n2onr6 x1ja2u2z']").text
                        row["Likes"] = extract_numbers(r_text)
                    except: row["Likes"] = 0

                try:
                    elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'xkrqix3')]|//div[contains(@data-testid, 'UFI2CommentsCount')]|//span[contains(@class, 'x193iq5w')]")
                    for e in elements:
                        txt = e.text.lower()
                        if "comments" in txt:
                            row["Comments"] = extract_numbers(txt)
                        elif "share" in txt:
                            row["Shares_Reposts"] = extract_numbers(txt) # 🌟 อัปเดตตัวแปรตาม FIELDNAMES
                except Exception as ex:
                    print(f"⚠️ FB Stats Extract Sub-Error: {ex}")

            row["Engagement"] = row["Likes"] + row["Comments"] + row["Shares_Reposts"]

        print(f"✅ {platform} Success: {url}")
    except Exception as e:
        print(f"❌ {platform} Error {url}: {str(e)[:100]}")
    finally:
        driver.quit()
    return row

# ── TikTok Async (ปรับปรุงแล้ว: เพิ่มระบบ Retry และ Delay) ──
async def scrape_tiktok_batch(urls):
    import random # ต้อง import ใน scope นี้หรือ import ไว้บนสุดของไฟล์
    results = []
    async with TikTokApi() as api:
        # ปรับ headless เป็น True ตามเดิมของคุณ แต่เน้นเรื่อง session
        await api.create_sessions(ms_tokens=[os.environ.get("ms_token")], num_sessions=1, sleep_after=2, headless=True)
        
        for url in urls:
            row = {f: 0 for f in FIELDNAMES}
            row.update({"Platform": "TikTok", "URL": url, "Author": "", "Heading": "", "Createtime": ""})
            
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    video = api.video(url=url)
                    info = await video.info()
                    s = info.get("stats", {})
                    
                    # 📌 ป้องกัน Error กรณีค่าเป็น String หรือไม่มีค่า
                    def safe_int(val):
                        try: return int(val)
                        except: return 0

                    likes = safe_int(s.get("diggCount", 0))
                    comments = safe_int(s.get("commentCount", 0))
                    shares = safe_int(s.get("shareCount", 0))
                    bookmarks = safe_int(s.get("collectCount", 0))
                    
                    row.update({
                        "Views": safe_int(s.get("playCount", 0)), 
                        "Likes": likes,
                        "Comments": comments, 
                        "Shares_Reposts": shares,
                        "Bookmarks": bookmarks,
                        "Author": info.get("author", {}).get("uniqueId", ""), 
                        "Heading": info.get("desc", "")[:100],
                        "Engagement": likes + comments + shares + bookmarks
                    })
                    print(f"✅ TikTok Success: {url}")
                    success = True
                    break # ออกจากลูป retry
                    
                except Exception as e:
                    print(f"⚠️ TikTok Attempt {attempt + 1} failed for {url}: {e}")
                    if attempt < max_retries - 1:
                        wait = random.uniform(3, 6)
                        await asyncio.sleep(wait)
                    else:
                        print(f"❌ TikTok Final Error after {max_retries} attempts: {url}")
            
            results.append(row)
    return results

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION (รันแบบจัดระเบียบตารางและเซฟลง CSV)
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("===================================================")
    echo_title = "🚀 STARTING SOCIAL MEDIA SCRAPER ENGINE"
    print(echo_title)
    print("===================================================\n")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ ไม่พบไฟล์อินพุต! กรุณาสร้างไฟล์ '{INPUT_FILE}' และใส่ URL ก่อนใช้งาน")
        input("\nกด Enter เพื่อปิดโปรแกรม...")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip().split()[-1] for line in f if line.strip()]

    if not urls:
        print("⚠️ ไม่พบ URLs ในไฟล์ url.txt")
        input("\nกด Enter เพื่อปิดโปรแกรม...")
        return

    print(f"📋 พบ URLs ทั้งหมดในระบบ: {len(urls)} ลิงก์")

    yt_urls = [u for u in urls if "youtube.com" in u or "youtu.be" in u]
    tt_urls = [u for u in urls if "tiktok.com" in u]
    sel_urls = [u for u in urls if u not in yt_urls and u not in tt_urls]

    final_data = []

    # 1. รันฝั่ง YouTube
    if yt_urls:
        print(f"\n🎬 กำลังดึงข้อมูล YouTube ({len(yt_urls)} ลิงก์)...")
        with ThreadPoolExecutor(max_workers=1) as exec:
            final_data.extend(list(exec.map(scrape_youtube_api, yt_urls)))

    # 2. รันฝั่ง Facebook / X
    if sel_urls:
        print(f"\n🌐 กำลังดึงข้อมูล Facebook / X ({len(sel_urls)} ลิงก์)...")
        with ThreadPoolExecutor(max_workers=1) as exec:
            final_data.extend(list(exec.map(scrape_selenium_task, sel_urls)))

    # 3. รันฝั่ง TikTok
    if tt_urls:
        print(f"\n🎵 กำลังดึงข้อมูล TikTok ({len(tt_urls)} ลิงก์)...")
        final_data.extend(asyncio.run(scrape_tiktok_batch(tt_urls)))

    # จัดการเซฟข้อมูลออกเป็นไฟล์ CSV
    print(f"\n💾 กำลังบันทึกข้อมูลลงไฟล์ {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()
        writer.writerows(final_data)
        
    print("\n🎉 [SUCCESS] ดึงข้อมูลสถิติเสร็จสมบูรณ์เรียบร้อยแล้ว!")
    input("\nกด Enter เพื่อปิดโปรแกรม...")

if __name__ == "__main__":
    main()