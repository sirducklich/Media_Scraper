from TikTokApi import TikTokApi
import asyncio
import os
import csv
import math

ms_token = os.environ.get("ms_token", None)  # Set your own ms_token

# Function to extract required TikTok video data safely
def extract_tiktok_data(data, url):
    stats = data.get('stats', {})
    
    # Helper to force any string/missing value into a clean integer
    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    play_count = safe_int(stats.get('playCount', 0))
    digg_count = safe_int(stats.get('diggCount', 0))
    comment_count = safe_int(stats.get('commentCount', 0))
    share_count = safe_int(stats.get('shareCount', 0))
    
    create_time = safe_int(data.get('createTime', 0))
    
    # Calculate Excel date (skip if create_time is missing to avoid weird 1970 dates)
    excel_date = math.floor(create_time / 86400) + 25569 if create_time > 0 else 0

    return {
        'Author': data.get('author', {}).get('uniqueId', 'Unknown'),
        'URLs': url,
        'Heading': data.get('desc', ''),
        'Views': play_count,
        'Engagement': digg_count + comment_count + share_count,
        'Action': comment_count + share_count,
        'Likes': digg_count,
        'Comments': comment_count,
        'Shares': share_count,
        'Createtime': excel_date,
        'Duration': safe_int(data.get('video', {}).get('duration', 0))
    }

# Read URLs from text file
with open("TikTok/tiktok_urls.txt", "r") as file:
    urls = [url.strip() for url in file.readlines()]  # Remove newlines

# Function to fetch video details and save to CSV
async def fetch_and_save_tiktok_data():
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=2, browser=os.getenv("TIKTOK_BROWSER", "chromium"))

        # Open CSV file to write results
        with open("TikTok/Tiktok_output.csv", "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=';')
            csv_writer.writerow(["Author", "URLs", "Heading", "Views", "Engagement", "Action", "Likes", "Comments", "Shares", "Createtime", "Duration"])  # Write header

            for url in urls:
                try:
                    video = api.video(url=url)
                    video_info = await video.info()
                    extracted_data = extract_tiktok_data(video_info, url)

                    # Write extracted data to CSV
                    csv_writer.writerow(extracted_data.values())

                    print(f"✅ Extracted: {url} - Views: {extracted_data['Views']}, Engagement: {extracted_data['Engagement']}")
                except Exception as e:
                    print(f"❌ Failed to fetch data for {url}: {e}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(fetch_and_save_tiktok_data())
