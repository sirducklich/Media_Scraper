import os
import streamlit as st

# --- โค้ดส่วนนี้จะบังคับให้ Streamlit ติดตั้ง Browser แค่ครั้งเดียวตอนเปิดแอป ---
@st.cache_resource
def install_playwright():
    os.system("playwright install chromium")

install_playwright()

import streamlit as st
import pandas as pd
import asyncio
from master_scraper import scrape_selenium_task, scrape_tiktok_batch # ดึงฟังก์ชันเดิมมาใช้

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Social Media Scraper", layout="wide")

st.title("📱 Social Media Analytics Scraper")
st.write("เครื่องมือดึงข้อมูลยอด View และ Engagement สำหรับทีม Analyst")

# ส่วนที่ 1: การนำเข้าข้อมูล
st.sidebar.header("Configuration")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ URL (.txt)", type=["txt"])

if uploaded_file is not None:
    # อ่านไฟล์ที่อัปโหลด
    lines = uploaded_file.readlines()
    urls = [line.decode("utf-8").strip() for line in lines if line.strip()]
    
    st.info(f"พบทั้งหมด {len(urls)} URLs พร้อมสำหรับการดึงข้อมูล")
    
    # ส่วนที่ 2: ปุ่มสั่งงาน
    if st.button("เริ่มดึงข้อมูล (Start Scraping)"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # แยกประเภท URL เหมือนเดิม
        selenium_urls = [u for u in urls if "tiktok.com" not in u]
        tiktok_urls = [u for u in urls if "tiktok.com" in u]
        
        results = []
        
        # ดึงข้อมูล (ตัวอย่างแบบ Sequential เพื่อความเสถียรบน Web App)
        with st.spinner('กำลังดึงข้อมูล... โปรดรอสักครู่'):
            # ดึง Selenium (FB/X)
            for i, url in enumerate(selenium_urls):
                status_text.text(f"กำลังดึงข้อมูลจาก FB/X: {url}")
                results.append(scrape_selenium_task(url))
                progress_bar.progress((i + 1) / len(urls))
            
            # ดึง TikTok
            if tiktok_urls:
                status_text.text("กำลังดึงข้อมูลจาก TikTok...")
                tt_results = asyncio.run(scrape_tiktok_batch(tiktok_urls))
                results.extend(tt_results)
                progress_bar.progress(1.0)

        # ส่วนที่ 3: แสดงผลและดาวน์โหลด
        st.success("ดึงข้อมูลเสร็จสิ้น!")
        df = pd.DataFrame(results)
        st.dataframe(df) # แสดงตารางบนหน้าเว็บ
        
        # ปุ่มดาวน์โหลดไฟล์ CSV
        csv = df.to_csv(index=False, encoding='utf-8-sig', sep=';').encode('utf-8-sig')
        st.download_button(
            label="💾 ดาวน์โหลดไฟล์ผลลัพธ์ (CSV)",
            data=csv,
            file_name='scraped_data.csv',
            mime='text/csv',
        )