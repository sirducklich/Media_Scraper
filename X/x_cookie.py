import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def save_x_cookies():
    # 1. สร้างโฟลเดอร์ชื่อ X ถ้ายังไม่มีในระบบ
    folder_name = "X"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"📁 สร้างโฟลเดอร์ '{folder_name}' เรียบร้อยแล้ว")

    # 2. ตั้งค่า Selenium (ห้ามใส่ --headless เพื่อให้เราสามารถพิมพ์ล็อกอินได้)
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1200,800")
    
    print("🤖 กำลังเปิด Chrome...")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # 3. เปิดหน้าล็อกอินของ X
        driver.get("https://x.com/i/flow/login")
        
        print("\n" + "="*50)
        print("📌 [คำแนะนำ] กรุณาทำการเข้าสู่ระบบ (Login) บนหน้าต่าง Chrome ที่เปิดขึ้นมาให้เสร็จสมบูรณ์")
        print("เมื่อเข้าสู่หน้าแรก (Home Feed) ของ X เรียบร้อยแล้ว")
        print("ให้กลับมาที่หน้า Terminal นี้แล้วกด [Enter] เพื่อบันทึก Cookie")
        print("="*50 + "\n")
        
        # รอให้ผู้ใช้กด Enter หลังจากล็อกอินเสร็จ
        input("👉 หลังจากล็อกอินสำเร็จแล้ว กด [Enter] ตรงนี้เพื่อบันทึก Cookie... ")

        # 4. ดึง Cookie จากเบราว์เซอร์
        cookies = driver.get_cookies()
        
        # 5. บันทึกข้อมูลลงไฟล์ JSON ในโฟลเดอร์ X
        file_path = os.path.join(folder_name, "X/x_cookies.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=4, ensure_ascii=False)
            
        print(f"\n✅ บันทึก Cookie สำเร็จเรียบร้อย!")
        print(f"💾 ไฟล์ถูกจัดเก็บอยู่ที่: {file_path}")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
    finally:
        # ปิดเบราว์เซอร์
        driver.quit()

if __name__ == "__main__":
    save_x_cookies()