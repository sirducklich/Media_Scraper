import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import random
import time

# --- ฟังก์ชันจำลองการจัดกลุ่ม (สามารถเชื่อม API ของ Gemini/OpenAI ได้ในอนาคต) ---
def categorize_post(caption_text):
    text = str(caption_text).lower()
    if any(word in text for word in ["ลด", "โปร", "ราคาพิเศษ", "sale", "ช้อป"]):
        return "Hard Sale & Promotion"
    elif any(word in text for word in ["วิธี", "ไอเดีย", "เทคนิค", "รู้หรือไม่"]):
        return "Edutainment & Tips"
    elif any(word in text for word in ["แจก", "ร่วมสนุก", "กติกา"]):
        return "Interaction"
    else:
        return "General / Product Showcase"

async def scrape_dohome_fb(page_url, scroll_count=5):
    extracted_data = []
    seen_captions = set() # กระปุกสำหรับเช็คข้อความซ้ำ
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) 
        context = await browser.new_context(
            storage_state="Facebook/auth.json",
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        print(f"กำลังเปิดหน้าเพจ: {page_url}")
        await page.goto(page_url)
        
        try:
            await page.wait_for_selector('div[role="article"]', timeout=15000)
        except:
            print("รอโหลดหน้าเว็บนานเกินไป หรือเข้าสู่ระบบไม่สำเร็จ")
            await browser.close()
            return []

        print("เริ่มทำการดึงข้อมูลพร้อมกับ Scroll หน้าจอ...")
        
        # --- เริ่มลูป: ดึงข้อมูล -> เลื่อนจอ -> ดึงข้อมูล -> เลื่อนจอ ---
        for i in range(scroll_count):
            print(f"\n--- Scroll ครั้งที่ {i+1}/{scroll_count} ---")
            
            # 1. พยายามดึงข้อมูล ณ ตำแหน่งหน้าจอปัจจุบันก่อนเลื่อน
            messages = page.locator('div[data-ad-comet-preview="message"]')
            msg_count = await messages.count()
            
            if msg_count > 0:
                for j in range(msg_count):
                    try:
                        full_text = await messages.nth(j).inner_text()
                        full_text = full_text.strip()
                        
                        # เช็คว่าข้อความยาวเกิน 10 ตัวอักษร และ "ยังไม่เคยถูกดึงมาก่อน"
                        if len(full_text) > 10 and full_text not in seen_captions:
                            seen_captions.add(full_text) # จำไว้ว่าดึงโพสต์นี้ไปแล้ว
                            category = categorize_post(full_text)
                            
                            extracted_data.append({
                                "Post_URL": "N/A",
                                "Caption": full_text,
                                "Category": category,
                                "Length": len(full_text)
                            })
                            print(f"  [+] เจอโพสต์ใหม่: {full_text[:30]}...")
                    except:
                        continue
            
            # 2. เลื่อนหน้าจอลง (PageDown 2 ครั้ง) เพื่อโหลดโพสต์ถัดไป
            await page.keyboard.press("PageDown")
            await page.keyboard.press("PageDown") 
            
            # 3. หน่วงเวลารอให้โพสต์ใหม่โหลดขึ้นมา
            delay = random.uniform(3.0, 5.0)
            await asyncio.sleep(delay)

        await browser.close()        
    return extracted_data

# --- ส่วนของการรันสคริปต์ ---
if __name__ == "__main__":
    url = "https://www.facebook.com/DohomeOnline"
    
    # รัน Async Event Loop
    raw_data = asyncio.run(scrape_dohome_fb(url, scroll_count=20)) # เลื่อนลง 20 ครั้งเพื่อดึงโพสต์ย้อนหลังมากขึ้น
    
    # นำข้อมูลเข้าสู่ Pandas DataFrame
    df = pd.DataFrame(raw_data)
    
    if not df.empty:
        # ลบโพสต์ที่ซ้ำซ้อนออก (เผื่อ Scroll แล้วเจอโพสต์เดิม)
        df.drop_duplicates(subset=['Caption'], inplace=True)
        
        print(f"\nดึงข้อมูลสำเร็จทั้งหมด: {len(df)} โพสต์")
        
        # บันทึกเป็นไฟล์ CSV พร้อมรองรับภาษาไทย
        filename = "Facebook/Crawling_fb_posts.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"บันทึกไฟล์: {filename} เรียบร้อยแล้ว")
        
        # แสดงผล 5 บรรทัดแรก
        print("\nตัวอย่างข้อมูล:")
        print(df.head())
    else:
        print("ไม่พบข้อมูลโพสต์")