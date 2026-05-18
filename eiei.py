import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import random

# ฟังก์ชันจำลองการให้ AI ช่วยจัดกลุ่มโพสต์ (Auto-Categorization)
def categorize_post_with_ai(caption_text):
    """
    ในสถานการณ์จริง ตรงนี้จะเป็นการยิง API ไปหา Gemini หรือ OpenAI
    พร้อม Prompt: "อ่านข้อความนี้แล้วจัดกลุ่ม 1 ใน 5 หมวด: Hard Sale, Review, Tips, Engagement, CSR"
    """
    text = caption_text.lower()
    if "ลดราคา" in text or "โปรโมชั่น" in text or "ราคาพิเศษ" in text:
        return "Hard Sale & Promotion"
    elif "เทคนิค" in text or "วิธี" in text or "ไอเดีย" in text:
        return "Edutainment & Tips"
    elif "ร่วมสนุก" in text or "แจก" in text:
        return "Interaction"
    else:
        return "Product Showcase"

async def scrape_facebook_page(page_url, scroll_count=5):
    data_list = []
    
    async with async_playwright() as p:
        # เปิดเบราว์เซอร์ (ตั้ง headless=False เพื่อดูการทำงานจริง)
        browser = await p.chromium.launch(headless=False) 
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        await page.goto(page_url)
        await page.wait_for_timeout(3000) # รอหน้าเพจโหลด
        
        # จำลองการเลื่อนหน้าจอลงเพื่อโหลดโพสต์
        for _ in range(scroll_count):
            await page.keyboard.press("PageDown")
            # ใส่ Delay แบบสุ่มเพื่อป้องกัน Facebook แบน
            await page.wait_for_timeout(random.randint(2000, 4000)) 
            
        # สมมติฐานว่าเราหา Class หรือ Selector ของโพสต์เจอ (ซึ่งในชีวิตจริงต้อง Inspect หน้าเว็บ FB)
        # นี่คือโค้ดจำลองการดึงข้อความจากโพสต์
        post_elements = await page.query_selector_all('.xdj266r.x11i5rnm.xat24cr') # ตัวอย่าง Class สมมติ
        
        for post in post_elements:
            try:
                caption = await post.inner_text()
                category = categorize_post_with_ai(caption) # ส่งไปให้ AI จัดกลุ่ม
                
                data_list.append({
                    "Caption": caption[:100] + "...", # ตัดมาเฉพาะ 100 ตัวอักษรแรก
                    "Category": category,
                    "Length": len(caption)
                })
            except:
                continue
                
        await browser.close()
        
    return data_list

# การเรียกใช้งาน
raw_data = asyncio.run(scrape_facebook_page("https://www.facebook.com/DohomeOnline"))
df = pd.DataFrame(raw_data)
df.to_csv("dohome_content_analysis.csv", index=False)
print(df.head())