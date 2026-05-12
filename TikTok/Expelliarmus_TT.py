from TikTokApi import TikTokApi
import asyncio
import os
import csv

ms_token = os.environ.get("ms_token", None)  # Set your own ms_token

# Function to extract required TikTok video data
def extract_tiktok_data(data, url):
    return {
        'Author': data['author'].get('uniqueId'),
        'URLs': url,
        'Heading': data.get('desc'),
        'Views': data['stats'].get('playCount', 0),
        'Engagement': data['stats'].get('diggCount', 0) + data['stats'].get('commentCount', 0) + data['stats'].get('shareCount', 0),
        'Likes': data['stats'].get('diggCount', 0),
        'Comments': data['stats'].get('commentCount', 0),
        'Shares': data['stats'].get('shareCount', 0),
        'Createtime': data.get('createTime')
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
            csv_writer.writerow(["Author", "URLs", "Heading", "Views", "Engagement", "Likes", "Comments", "Shares", "Createtime"])  # Write header

            for url in urls:
                try:
                    video = api.video(url=url)
                    video_info = await video.info()
                    extracted_data = extract_tiktok_data(video_info, url)

                    # Write extracted data to CSV
                    csv_writer.writerow(extracted_data.values())

                    print(f"✅ Extracted: {url} - Views: {video_info['stats'].get('playCount', 0)}, Engagement: {video_info['stats'].get('diggCount', 0) + video_info['stats'].get('commentCount', 0) + video_info['stats'].get('shareCount', 0)}")
                except Exception as e:
                    print(f"❌ Failed to fetch data for {url}: {e}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(fetch_and_save_tiktok_data())
