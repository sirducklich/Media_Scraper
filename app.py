import os
import sys
import subprocess
import streamlit as st
from master_scraper import scrape_selenium_task, scrape_tiktok_batch, scrape_youtube_api

# --- บังคับดาวน์โหลด Browser และรอจนกว่าจะเสร็จ ---
@st.cache_resource
def install_playwright():
    try:
        # ใช้ subprocess เพื่อบังคับให้ระบบรอจนกว่าจะติดตั้งเสร็จ
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("Playwright Chromium installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install playwright: {e}")

install_playwright()

import streamlit as st
import pandas as pd
import asyncio
from master_scraper import scrape_selenium_task, scrape_tiktok_batch # ดึงฟังก์ชันเดิมมาใช้

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Social Media Scraper", layout="wide")

st.title("📱 Social Media Analytics Scraper")
st.write("เครื่องมือดึงข้อมูลยอด View และ Engagement สำหรับทีม Analyst (ขณะนี้รองรับ Facebook, X/Twitter และ TikTok)")

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
        
# คัดแยก URL ให้ถูกต้องทั้ง 3 แพลตฟอร์ม
        yt_urls = [u for u in urls if "youtube.com" in u or "youtu.be" in u]
        tt_urls = [u for u in urls if "tiktok.com" in u]
        sel_urls = [u for u in urls if u not in yt_urls and u not in tt_urls]

        results = []

        # 1. ดึงข้อมูล YouTube
        if yt_urls:
            with st.spinner("กำลังดึงข้อมูลจาก YouTube..."):
                for url in yt_urls:
                    results.append(scrape_youtube_api(url))

        # 2. ดึงข้อมูล Facebook / X (Selenium)
        if sel_urls:
            with st.spinner("กำลังดึงข้อมูลจาก Facebook / X..."):
                for url in sel_urls:
                    results.append(scrape_selenium_task(url))

        # 3. ดึงข้อมูล TikTok
        if tt_urls:
            with st.spinner("กำลังดึงข้อมูลจาก TikTok..."):
                # TikTok เป็น Async ต้องรันแบบรวบยอด
                tt_results = asyncio.run(scrape_tiktok_batch(tt_urls))
                results.extend(tt_results)

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