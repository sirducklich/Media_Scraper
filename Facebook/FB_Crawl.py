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
    
    async with async_playwright() as p:
        # เปิดเบราว์เซอร์ โหลด State ที่ล็อกอินไว้แล้ว
        browser = await p.chromium.launch(headless=False) 
        context = await browser.new_context(
            storage_state="Facebook/auth.json", # ต้องมีไฟล์นี้ใน Folder เดียวกัน
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        print(f"กำลังเปิดหน้าเพจ: {page_url}")
        await page.goto(page_url)
        
        # รอให้หน้าเว็บโหลดสมบูรณ์ (รอจนกว่าช่องโพสต์แรกจะปรากฏ)
        try:
            await page.wait_for_selector('div[role="article"]', timeout=15000)
        except:
            print("รอโหลดหน้าเว็บนานเกินไป หรือเข้าสู่ระบบไม่สำเร็จ")
            await browser.close()
            return []

        print("เริ่มทำการ Scroll เพื่อโหลดโพสต์ย้อนหลัง...")
        for i in range(scroll_count):
            await page.keyboard.press("PageDown")
            await page.keyboard.press("PageDown") # กดสองครั้งเพื่อให้เลื่อนลงลึกขึ้น
            
            # หน่วงเวลาแบบสุ่ม (2-5 วินาที) เพื่อให้ดูเหมือนคนอ่านจริงๆ และป้องกันการถูกบล็อก
            delay = random.uniform(2.5, 5.0)
            print(f"Scroll ครั้งที่ {i+1}/{scroll_count} - รอ {delay:.2f} วินาที")
            await asyncio.sleep(delay)

        print("กำลังดึงข้อมูลโพสต์...")
        # ใช้ Locator ที่อิงตาม ARIA Role ซึ่งเสถียรกว่าการใช้ชื่อ Class
        posts = page.locator('div[role="article"]')
        post_count = await posts.count()
        
        for i in range(post_count):
            post_locator = posts.nth(i)
            
            try:
                # พยายามหาข้อความในโพสต์ (Facebook มักเก็บข้อความไว้ใน div ที่มี dir="auto")
                text_elements = post_locator.locator('div[data-ad-comet-preview="message"]')
                
                # รวมข้อความทั้งหมดในโพสต์นั้น
                full_text = ""
                text_count = await text_elements.count()
                for j in range(text_count):
                    text_content = await text_elements.nth(j).inner_text()
                    full_text += text_content + "\n"
                
                full_text = full_text.strip()
                
                # ข้ามโพสต์ที่ไม่มีข้อความ (อาจจะเป็นโพสต์รูปภาพล้วน หรือวิดีโอล้วน)
                if not full_text:
                    continue
                    
                # ดึง URL ของโพสต์ (ถ้ามี) โพสต์มักจะมีลิงก์เวลาซ่อนอยู่
                post_url = ""
                links = post_locator.locator('a[role="link"][tabindex="0"]')
                link_count = await links.count()
                for k in range(link_count):
                    href = await links.nth(k).get_attribute('href')
                    if href and "/posts/" in href or "/videos/" in href or "/photos/" in href:
                        post_url = href.split('?')[0] # ตัด parameter ต่อท้ายออก
                        break

                category = categorize_post(full_text)
                
                extracted_data.append({
                    "Post_URL": post_url,
                    "Caption": full_text,
                    "Category": category,
                    "Length": len(full_text)
                })
                
            except Exception as e:
                # หากดึงข้อมูลบางโพสต์พัง ให้ข้ามไปโพสต์ถัดไป
                continue
                
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