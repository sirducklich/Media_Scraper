from TikTokApi import TikTokApi
import asyncio
import os
import csv
import math
import random # 📌 Import เพิ่มเติมสำหรับการสุ่มดีเลย์

ms_token = os.environ.get("ms_token", None)  # Set your own ms_token

# Function to extract required TikTok video data safely
def extract_tiktok_data(data, url):
    stats = data.get('stats', {})
    
    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    play_count = safe_int(stats.get('playCount', 0))
    digg_count = safe_int(stats.get('diggCount', 0))
    comment_count = safe_int(stats.get('commentCount', 0))
    share_count = safe_int(stats.get('shareCount', 0))
    collect_count = safe_int(stats.get('collectCount', 0))
    create_time = safe_int(data.get('createTime', 0))
    
    excel_date = math.floor(create_time / 86400) + 25569 if create_time > 0 else 0

    return {
        'Author': data.get('author', {}).get('uniqueId', 'Unknown'),
        'URLs': url,
        'Heading': data.get('desc', ''),
        'Views': play_count,
        'Engagement': digg_count + comment_count + share_count + collect_count, 
        'Action': comment_count + share_count,
        'Likes': digg_count,
        'Comments': comment_count,
        'Shares': share_count,
        'Createtime': excel_date,
        'Duration': safe_int(data.get('video', {}).get('duration', 0)),
        'Bookmark': collect_count
    }

# Read URLs from text file
with open("TikTok/tiktok_urls.txt", "r") as file:
    urls = [url.strip() for url in file.readlines()]

# Function to fetch video details and save to CSV
async def fetch_and_save_tiktok_data():
    async with TikTokApi() as api:
        # 📌 แนะนำให้ลองปรับ browser เป็น 'firefox' หรือ 'webkit' หาก 'chromium' ยังโดนบล็อก
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=2, browser=os.getenv("TIKTOK_BROWSER", "chromium"))

        with open("TikTok/Tiktok_output.csv", "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=';')
            csv_writer.writerow(["Author", "URLs", "Heading", "Views", "Engagement", "Action", "Likes", "Comments", "Shares", "Createtime", "Duration", "Bookmark"])

            for url in urls:
                max_retries = 3 # 📌 จำนวนครั้งสูงสุดที่จะให้ลองดึงข้อมูลใหม่
                
                for attempt in range(max_retries):
                    try:
                        video = api.video(url=url)
                        video_info = await video.info()
                        extracted_data = extract_tiktok_data(video_info, url)

                        # Write extracted data to CSV
                        csv_writer.writerow(extracted_data.values())
                        print(f"✅ Extracted: {url} - Views: {extracted_data['Views']}, Bookmark: {extracted_data['Bookmark']}")
                        
                        # 📌 สุ่มพัก 1-3 วินาทีก่อนดึง URL ถัดไปให้ดูเหมือนคนกำลังเล่นแอป
                        await asyncio.sleep(random.uniform(1, 3)) 
                        break # ถ้าดึงสำเร็จ ให้ออกจาก Loop Retry ทันที
                        
                    except Exception as e:
                        print(f"⚠️ Attempt {attempt + 1} failed for {url}: {e}")
                        
                        if attempt < max_retries - 1:
                            # 📌 ถ้ายังดึงไม่สำเร็จและยังไม่ครบโควต้า ให้พักนานขึ้น (สุ่ม 4-8 วินาที) ก่อนลองใหม่
                            wait_time = random.uniform(4, 8)
                            print(f"⏳ Waiting {wait_time:.2f} seconds before retrying...")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"❌ Completely failed to fetch data for {url} after {max_retries} attempts.")

# Run the async function
if __name__ == "__main__":
    asyncio.run(fetch_and_save_tiktok_data())