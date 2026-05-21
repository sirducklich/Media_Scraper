#Bot Detected Fixed Needed!
from TikTokApi import TikTokApi
import asyncio
import os
import csv
import math

ms_token = os.environ.get("ms_token", None)

# (Use the safe extract_tiktok_data function from our previous step here)
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
    
    create_time = safe_int(data.get('createTime', 0))
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

async def fetch_channel_videos(username, video_count=10):
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token], 
            num_sessions=1, 
            sleep_after=5,           # Increased sleep to let the page fully render
            headless=False,          # Forces the browser to be visible
            browser='webkit'         # Switches from Chromium to Apple's WebKit
        )

        # Create the CSV file
        filename = f"TikTok/TikTok_{username}_output.csv"
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=';')
            # Fixed headers to match the 11 dictionary keys
            csv_writer.writerow(["Author", "URLs", "Heading", "Views", "Engagement", "Action", "Likes", "Comments", "Shares", "Createtime", "Duration"])

            print(f"Scraping latest {video_count} videos from @{username}...")
            
            # Target the specific user
            user = api.user(username=username)
            
            # Loop through their recent videos
            try:
                # .videos() returns an async iterator
                async for video in user.videos(count=video_count):
                    # In v6, the raw dictionary data is stored in .as_dict
                    video_info = video.as_dict
                    
                    # Construct the URL since we aren't pulling from a txt file anymore
                    video_url = f"https://www.tiktok.com/@{username}/video/{video_info.get('id')}"
                    
                    # Pass the raw dictionary and the constructed URL to your extractor
                    extracted_data = extract_tiktok_data(video_info, video_url)
                    csv_writer.writerow(extracted_data.values())
                    
                    print(f"✅ Extracted: {video_url} - Views: {extracted_data['Views']}")
                    
            except Exception as e:
                print(f"❌ Failed to fetch channel data: {e}")

if __name__ == "__main__":
    # Just pass the username (without the @ symbol)
    target_channel = "sunjifiteater" 
    asyncio.run(fetch_channel_videos(target_channel, 10))