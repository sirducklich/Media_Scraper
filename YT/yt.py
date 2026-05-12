import csv
import requests
import re
import os

# แนะนำให้ซ่อน API Key ของคุณเป็น Environment Variable ในการใช้งานจริงเพื่อความปลอดภัยนะครับ
YOUTUBE_API_KEY = "AIzaSyBcxyU9ZXsqNQrm7M2rTxInzZb5wNY1iqY" 

FIELDNAMES = [
    "Platform", "URL", "Author", "Heading", "Views", "Engagement",
    "Likes", "Comments", "Retweets_Shares", "Reactions", "Createtime",
]

def extract_youtube_id(url):
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"shorts\/([0-9A-Za-z_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def scrape_youtube_api(url):
    video_id = extract_youtube_id(url)
    
    # เซ็ตค่าเริ่มต้นให้เป็น String เพื่อไม่ให้พังไปก่อนที่เราจะเห็น Error
    row = {
        "Platform": "YouTube", "URL": url, "Author": "", "Heading": "", "Createtime": "",
        "Views": 0, "Engagement": 0, "Likes": 0, "Comments": 0, "Retweets_Shares": 0, "Reactions": 0
    }
    
    if not video_id: 
        row["Heading"] = "ERROR: หา Video ID ไม่เจอ"
        return row

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    try:
        # ยิง API และดึงค่าเป็น JSON
        res = requests.get(api_url).json()
        
        if "items" in res and res["items"]:
            # กรณีสำเร็จ ดึงข้อมูลตามปกติ
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
            
        else:
            # 🔴 กรณีล้มเหลว: ดึงข้อความ Error จาก Google มายัดใส่คอลัมน์ Heading
            error_msg = res.get("error", {}).get("message", "Unknown API Error")
            print(f"🔴 YOUTUBE RAW ERROR: {res}") # ปรินต์ทิ้งไว้ใน Logs ด้วย
            
            row["Author"] = "API_BLOCKED"
            row["Heading"] = f"GOOGLE ERROR: {error_msg}"
            
    except Exception as e: 
        row["Heading"] = f"REQUEST ERROR: {e}"
        print(f"❌ YouTube Request Error: {e}")
        
    return row

# กำหนด Path ไฟล์
input_file = "YT/YT_urls.txt"
output_file = "YT/YT_output.csv"

# ตรวจสอบว่ามีไฟล์ให้ดึงข้อมูลจริงหรือไม่
if os.path.exists(input_file):
    
    # อ่าน URLs จาก text file และกรองบรรทัดว่างออก
    with open(input_file, "r", encoding="utf-8") as file:
        urls = [url.strip() for url in file.readlines() if url.strip()] 

    # เปิดไฟล์ CSV เพื่อเขียนผลลัพธ์
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        # ใช้ DictWriter ให้มันแมปค่าจาก Key อัตโนมัติ
        csv_writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES, delimiter=';')
        
        # เขียน Header 1 รอบ
        csv_writer.writeheader() 

        # วนลูปตาม URL แล้วเขียนข้อมูลลงทีละบรรทัด
        for url in urls:
            extracted_data = scrape_youtube_api(url)
            csv_writer.writerow(extracted_data)
            
    print(f"\n🎉 ดึงข้อมูลเสร็จสิ้น! บันทึกไฟล์เรียบร้อยที่: {output_file}")
else:
    print(f"⚠️ ไม่พบไฟล์อินพุตที่ระบุ: {input_file} กรุณาตรวจสอบตำแหน่งไฟล์อีกครั้ง")