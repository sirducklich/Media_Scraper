import requests
import json
import pandas as pd
from datetime import datetime
import time

def fetch_social_listening_data(keyword, date_after, pages_to_scrape=15, country_code="th"):
    url = "https://google.serper.dev/search"
    
    headers = {
        'X-API-KEY': '054d81489024b2eb9cc122259feaa05f75f8c772', # <-- PASTE YOUR KEY HERE
        'Content-Type': 'application/json'
    }

    # 1. Format the date for Google's official 'tbs' parameter (MM/DD/YYYY)
    date_obj = datetime.strptime(date_after, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%m/%d/%Y")
    
    # 'cdr:1' = custom date range. 'cd_min' = the start date.
    tbs_filter = f"cdr:1,cd_min:{formatted_date}"

    all_data = {
        "organic": [],
        "peopleAlsoAsk": [],
        "relatedSearches": []
    }

    for current_page in range(1, pages_to_scrape + 1):
        print(f"Fetching Page {current_page}...")
        
        # 2. Use the clean keyword and the official 'tbs' parameter
        payload = json.dumps({
            "q": keyword, 
            "gl": "th",
            "hl": "th",
            "lr": "lang_th",
            "autocorrect": True,
            "page": current_page,
            "tbs": tbs_filter 
        })

        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status() 
            data = response.json()
            
            # --- 3. THE DEBUG BLOCK ---
            # If 'organic' is missing, print the raw API response to see the hidden error
            if 'organic' not in data:
                print(f"\n[CRITICAL] API connected, but no organic results found. Raw response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                break
            # ---------------------------
            
            if len(data['organic']) > 0:
                all_data["organic"].extend(data['organic'])
            else:
                print("No more organic results available on this page.")
                break 
                
            if 'peopleAlsoAsk' in data:
                all_data["peopleAlsoAsk"].extend(data['peopleAlsoAsk'])
                
            if 'relatedSearches' in data:
                all_data["relatedSearches"].extend(data['relatedSearches'])

        except Exception as e:
            print(f"API Error on page {current_page}: {e}")
            break
            
        time.sleep(1) # Keeps the API happy
        
    return all_data

def save_to_csv(api_data, filename="market_insights.csv"):
    results = []
    
    if api_data and 'organic' in api_data:
        for item in api_data['organic']:
            results.append({
                "Date_Extracted": datetime.now().strftime("%Y-%m-%d"),
                "Published_Date": item.get("date", "Unknown"), # <-- ADD THIS LINE
                "Heading": item.get("title"),
                "URL": item.get("link"),
                "Body_Snippet": item.get("snippet"),
                "Source_Site": item.get("link").split('/')[2] if item.get("link") else "Unknown" 
            })
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Successfully saved {len(df)} records to {filename}")
    else:
        print("No results found to save.")
        
    seen_questions = set()
    for item in api_data.get("peopleAlsoAsk", []):
        question = item.get("question")
        if question not in seen_questions:
            seen_questions.add(question)
            results.append({
                "Topic_Type": "Consumer Question",
                "Date_Extracted": datetime.now().strftime("%Y-%m-%d"),
                "Heading": question,
                "URL": item.get("link"),
                "Body_Snippet": item.get("snippet"),
                "Source_Site": "Google Q&A"
            })

    if results:
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n✅ Successfully saved {len(df)} records to {filename}")
    else:
        print("\n❌ No results found to save.")

if __name__ == "__main__":
    my_keyword = '"WE Fitness Society" (site:facebook.com OR site:wefitnesssociety.com OR site:x.com OR site:instagram.com OR site:tiktok.com)'
    start_date = "2026-01-01" 
    
    print(f"Starting analysis for '{my_keyword}' in Thailand since {start_date}...")
    
    raw_data = fetch_social_listening_data(my_keyword, start_date, pages_to_scrape=10, country_code="th")
    
    save_to_csv(raw_data, f"Listening/insights_{my_keyword}.csv")