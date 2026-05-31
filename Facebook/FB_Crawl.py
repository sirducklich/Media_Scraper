import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import random
import time

# --- ฟังก์ชันจำลองการจัดกลุ่ม ---
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
    seen_captions = set() 
    
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
        
        for i in range(scroll_count):
            print(f"\n--- Scroll ครั้งที่ {i+1}/{scroll_count} ---")
            
            articles = page.locator('div[role="article"]')
            article_count = await articles.count()
            print(f"  -> ตรวจพบ {article_count} กล่องโพสต์ในหน้าจอนี้")
            
            if article_count > 0:
                for j in range(article_count):
                    try:
                        post = articles.nth(j)
                        full_text = ""
                        
                        # --- กลยุทธ์ที่ 1: ค้นหาข้อความแคปชั่นด้วยระบบสเลกเตอร์สำรอง ---
                        text_selectors = [
                            'div[data-ad-comet-preview="message"]',
                            'div[data-ad-preview="message"]',
                            'div[dir="auto"]'  # สเลกเตอร์ทั่วไปรองรับกรณีโครงสร้างเปลี่ยนหรือเป็น Reels
                        ]
                        
                        for selector in text_selectors:
                            msg_locator = post.locator(selector)
                            if await msg_locator.count() > 0:
                                if selector == 'div[dir="auto"]':
                                    # กรณีเจอหลายจุด (เช่น ชื่อเพจ, เวลา) ให้ลูปหาข้อความที่ยาวที่สุดและไม่ใช่ปุ่มคำสั่ง
                                    count = await msg_locator.count()
                                    candidates = []
                                    for idx in range(count):
                                        txt = (await msg_locator.nth(idx).inner_text()).strip()
                                        if txt and len(txt) > 10 and not any(w in txt for w in ["ถูกใจ", "แสดงความคิดเห็น", "แชร์", "เลือกซื้อเลย", "ส่งข้อความ"]):
                                            candidates.append(txt)
                                    if candidates:
                                        full_text = max(candidates, key=len)
                                else:
                                    full_text = (await msg_locator.first.inner_text()).strip()
                                
                                if len(full_text) > 10:
                                    break # ถ้าเจอข้อความที่ใช้งานได้แล้ว ให้หยุดหาในสเลกเตอร์ถัดไป
                        
                        # ตรวจสอบว่าได้ข้อความมาจริง และไม่ซ้ำเดิม
                        if full_text and full_text not in seen_captions:
                            category = categorize_post(full_text)
                            post_url = "N/A"
                            
                            # --- กลยุทธ์ที่ 2: ค้นหา URL (รองรับคำว่า /reel/) ---
                            links = post.locator('a')
                            link_count = await links.count()
                            
                            for k in range(link_count):
                                href = await links.nth(k).get_attribute("href")
                                if href:
                                    # เพิ่มการดักจับ /reel/ และ /permalink/ เข้าไปด้วย
                                    if any(keyword in href for keyword in ["/posts/", "/photos/", "/videos/", "/reel/", "fbid=", "/permalink/"]):
                                        # ล้างค่าพารามิเตอร์การติดตามออกทันทีเพื่อให้ลิงก์สะอาด
                                        clean_href = href.split('?')[0]
                                        
                                        if clean_href.startswith("/"):
                                            post_url = f"https://www.facebook.com{clean_href}"
                                        else:
                                            post_url = clean_href
                                        break # เจอลิงก์หลักของโพสต์แล้ว ให้หยุดลูป
                            
                            # บันทึกข้อมูล (ยอมให้บันทึกแม้ไม่เจอ URL เพื่อไม่ให้เสียข้อมูล Text)
                            extracted_data.append({
                                "Post_URL": post_url,
                                "Caption": full_text,
                                "Category": category,
                                "Length": len(full_text)
                            })
                            seen_captions.add(full_text)
                            print(f"  [+] ดึงสำเร็จ: {full_text[:20]}... | URL: {post_url[:40]}")
                            
                    except Exception as e:
                        print(f"  [!] เกิดข้อผิดพลาดที่กล่องลำดับที่ {j}: {e}")
                        continue
            
            # เลื่อนหน้าจอลงเพื่อโหลดโพสต์ใหม่
            await page.keyboard.press("PageDown")
            await page.keyboard.press("PageDown") 
            delay = random.uniform(3.0, 5.0)
            await asyncio.sleep(delay)

        await browser.close()        
    return extracted_data

if __name__ == "__main__":
    url = "https://www.facebook.com/Emsphere.at.emdistrict"
    raw_data = asyncio.run(scrape_dohome_fb(url, scroll_count=250))
    
    df = pd.DataFrame(raw_data)
    if not df.empty:
        df.drop_duplicates(subset=['Caption'], inplace=True)
        print(f"\nดึงข้อมูลสำเร็จทั้งหมด: {len(df)} โพสต์")
        filename = "Facebook/Crawling_fb_posts.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"บันทึกไฟล์: {filename} เรียบร้อยแล้ว")
        print("\nตัวอย่างข้อมูล:")
        print(df.head())
    else:
        print("ไม่พบข้อมูลโพสต์")