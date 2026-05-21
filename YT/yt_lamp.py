import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import re
import math

# --- CONFIGURATION ---
API_KEY = 'YOUR_API_KEY_HERE'  # Replace with your actual API key
INPUT_FILE = 'YT/channels_input.xlsx' # Make sure this file has columns 'Channel ID' and 'Channel Name'
OUTPUT_FILE = 'YT/youtube_report.xlsx'

def parse_duration(duration_str):
    """Converts YouTube ISO 8601 duration (e.g., PT1H2M10S) to HH:MM:SS"""
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    seconds = re.search(r'(\d+)S', duration_str)
    
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0
    
    # Format as HH:MM:SS. If you prefer MM:SS for shorter videos, you can adjust this logic.
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_channel_videos():
    # Initialize the YouTube API client
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # Read the channels from the local Excel file
    try:
        channels_df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: Please create an Excel file named {INPUT_FILE} with 'Channel ID' and 'Channel Name' columns.")
        return

    # Set date limit to 1 year ago (matching the logic in your original script)
    date_limit = datetime.now(timezone.utc) - timedelta(days=365)
    
    all_video_details = []

    for index, row in channels_df.iterrows():
        channel_id = str(row['Channel ID']).strip()
        channel_name = str(row['Channel Name']).strip()
        
        if not channel_id or not channel_name:
            continue

        print(f"Processing channel: {channel_name}...")

        # Step 1: Get the Uploads Playlist ID
        channels_response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()

        if not channels_response.get('items'):
            print(f"  -> Channel {channel_id} not found.")
            continue

        playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Step 2: Get Video IDs from the Uploads Playlist
        video_ids = []
        next_page_token = None

        while True:
            playlistitems_response = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in playlistitems_response.get('items', []):
                video_id = item['snippet']['resourceId']['videoId']
                published_at_str = item['snippet']['publishedAt']
                
                # Parse YouTube's datetime string
                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                
                if published_at >= date_limit:
                    video_ids.append(video_id)

            next_page_token = playlistitems_response.get('nextPageToken')
            # Stop if there's no next page or we've hit the 1000 video limit
            if not next_page_token or len(video_ids) >= 1000:
                break

        # Step 3: Get Detailed Information About Each Video in chunks of 50
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            
            videos_response = youtube.videos().list(
                part='snippet,statistics,contentDetails',  # Added contentDetails for Duration
                id=','.join(chunk)
            ).execute()

            for video in videos_response.get('items', []):
                title = video['snippet']['title']
                
                # Safely get stats (some videos hide likes/comments)
                stats = video.get('statistics', {})
                view_count = int(stats.get('viewCount', 0))
                like_count = int(stats.get('likeCount', 0))
                comment_count = int(stats.get('commentCount', 0))
                engagement = like_count + comment_count
                
                # Format Publish Date to MM/DD/YYYY
                pub_date_raw = datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                formatted_date = pub_date_raw.strftime('%m/%d/%Y')
                
                url = f"https://www.youtube.com/watch?v={video['id']}"
                
                # Parse duration
                raw_duration = video['contentDetails']['duration']
                formatted_duration = parse_duration(raw_duration)

                # Build row to match master file format perfectly
                video_row = {
                    'Author': channel_name,
                    'URLs': url,
                    'Heading': title,
                    'Views': view_count,
                    'Engagement': engagement,
                    'Action': comment_count,       # Blank per requirements
                    'likes': like_count,
                    'Comments': comment_count,
                    'Share': '',        # Blank per requirements
                    'Createtime': formatted_date,
                    'Duration': formatted_duration
                }
                all_video_details.append(video_row)

    # Step 4: Export to Excel
    if all_video_details:
        # Create DataFrame ensuring column order exactly matches your master file
        final_columns = [
            'Author', 'URLs', 'Heading', 'Views', 'Engagement', 
            'Action', 'likes', 'Comments', 'Share', 
            'Createtime', 'Duration'
        ]
        
        df = pd.DataFrame(all_video_details, columns=final_columns)
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"\nSuccess! Fetch complete. Data saved to {OUTPUT_FILE}")
    else:
        print("No videos found within the specified date range.")

if __name__ == "__main__":
    get_channel_videos()