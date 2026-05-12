import csv
import platform
import time
import re
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, wait

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
            # 1. ยอด View (ใช้แบบเดิมที่คุณบอกว่าทำได้ดีอยู่แล้ว)
            try:
                # แก้ไขตามวิธีเดิมที่คุณใช้แล้วได้ผลดี
                view_el = driver.find_element(By.XPATH, "//a[contains(@href, '/analytics')]//span | //div[contains(@data-testid, 'analytics')]//span")
                row["Views"] = extract_numbers(view_el.text)
            except:
                row["Views"] = 0

            # 2. ยอด Engagement (กลับไปใช้วิธี Class ที่คุณต้องการ แต่ทำให้ฉลาดขึ้น)
            try:
                # รอให้ Element ของตัวเลขปรากฏ
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")))
                time.sleep(2) # เผื่อเวลาให้ตัวเลขวิ่งนิ่งๆ
                
                elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")
                # ดึงเฉพาะ Text ที่ไม่ว่าง และแปลงเป็นตัวเลขทันที
                vals = [extract_numbers(e.text) for e in elements if e.text.strip()]

                # ปกติ X จะเรียงลำดับในกลุ่มนี้เป็น: [0]=Views, [1]=Replies, [2]=Retweets, [3]=Likes
                # แต่เนื่องจากเราแยก Views ออกไปแล้ว เราจะสนใจแค่ 3 ตัวหลัง
                # และเพื่อกันพลาด เราจะเช็คว่ามีข้อมูลพอไหม
                
                if len(vals) >= 4:
                    # ถ้ามาครบ 4 ตัว (รวม View ที่ติดมากับ Class นี้)
                    row["Comments"] = vals[1]
                    row["Retweets_Shares"] = vals[2]
                    row["Likes"] = vals[3]
                elif len(vals) == 3:
                    # ถ้ามาแค่ 3 ตัว (กรณี View ไม่ได้ใช้ Class เดียวกัน)
                    row["Comments"] = vals[0]
                    row["Retweets_Shares"] = vals[1]
                    row["Likes"] = vals[2]
                else:
                    # ถ้ามาน้อยกว่านั้น ให้ลองใช้ fallback ดึงจาก data-testid สั้นๆ
                    row["Comments"] = extract_numbers(driver.find_element(By.XPATH, "//div[@data-testid='reply']").text)
                    row["Retweets_Shares"] = extract_numbers(driver.find_element(By.XPATH, "//div[@data-testid='retweet']").text)
                    row["Likes"] = extract_numbers(driver.find_element(By.XPATH, "//div[@data-testid='like']").text)

            except Exception as e:
                print(f"⚠️ Engagement error, trying fallback: {e}")

            # 3. คำนวณผลรวม Engagement
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