import asyncio
from playwright.async_api import async_playwright

async def save_login_state():
    async with async_playwright() as p:
        # เปิดเบราว์เซอร์แบบให้เห็นหน้าจอ (headless=False)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # ไปที่หน้า Login ของ Facebook
        await page.goto('https://www.facebook.com/')
        
        print("กรุณาล็อกอินผ่านหน้าต่างเบราว์เซอร์ที่เปิดขึ้นมา...")
        print("เมื่อล็อกอินเสร็จแล้ว และเข้าสู่หน้า Feed สำเร็จ ให้กลับมาพิมพ์ 'y' แล้วกด Enter ใน Terminal")
        
        # รอให้เราล็อกอินด้วยตัวเองจนเสร็จ
        input("พิมพ์ 'y' แล้วกด Enter เมื่อล็อกอินเสร็จ: ")

        # บันทึก Cookies และ Local Storage ทั้งหมดลงไฟล์ auth.json
        await context.storage_state(path="Facebook/auth.json")
        print("บันทึก Cookie ลงไฟล์ auth.json สำเร็จ!")
        
        await browser.close()

# เรียกใช้งานฟังก์ชัน
asyncio.run(save_login_state())