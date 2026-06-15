import requests
import json
import pandas as pd
from datetime import datetime
import time

def fetch_social_listening_data(keyword, date_after, date_before, exclude_sites=None, pages_to_scrape=15, country_code="th"):
    url = "https://google.serper.dev/search"
    
    headers = {
        'X-API-KEY': '054d81489024b2eb9cc122259feaa05f75f8c772', # <-- PASTE YOUR KEY HERE
        'Content-Type': 'application/json'
    }

    # 1. Format BOTH dates for Google's official 'tbs' parameter (MM/DD/YYYY)
    date_start_obj = datetime.strptime(date_after, "%Y-%m-%d")
    formatted_start = date_start_obj.strftime("%m/%d/%Y")
    
    date_end_obj = datetime.strptime(date_before, "%Y-%m-%d")
    formatted_end = date_end_obj.strftime("%m/%d/%Y")
    
    # 'cdr:1' = custom date range. 'cd_min' = start date, 'cd_max' = end date.
    tbs_filter = f"cdr:1,cd_min:{formatted_start},cd_max:{formatted_end}"

    # 2. Append exclusions to the search query using Google's '-site:' operator
    final_query = keyword
    if exclude_sites:
        for site in exclude_sites:
            final_query += f" -site:{site}"
            
    print(f"Constructed Query: {final_query}")

    all_data = {
        "organic": [],
        "peopleAlsoAsk": [],
        "relatedSearches": []
    }

    for current_page in range(1, pages_to_scrape + 1):
        print(f"Fetching Page {current_page}...")
        
        payload = json.dumps({
            "q": final_query, 
            "gl": country_code,
            "hl": country_code,
            "lr": f"lang_{country_code}",
            "autocorrect": True,
            "page": current_page,
            "tbs": tbs_filter 
        })

        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status() 
            data = response.json()
            
            if 'organic' not in data:
                print(f"\n[CRITICAL] API connected, but no organic results found. Raw response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                break
            
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
    
    # Process Organic Results
    if api_data and 'organic' in api_data:
        for item in api_data['organic']:
            results.append({
                "Topic_Type": "Organic Search Result",
                "Date_Extracted": datetime.now().strftime("%Y-%m-%d"),
                "Published_Date": item.get("date", "Unknown"),
                "Heading": item.get("title"),
                "URL": item.get("link"),
                "Body_Snippet": item.get("snippet"),
                "Source_Site": item.get("link").split('/')[2] if item.get("link") else "Unknown" 
            })
    
    # Process People Also Ask (Questions)
    seen_questions = set()
    for item in api_data.get("peopleAlsoAsk", []):
        question = item.get("question")
        if question not in seen_questions:
            seen_questions.add(question)
            results.append({
                "Topic_Type": "Consumer Question",
                "Date_Extracted": datetime.now().strftime("%Y-%m-%d"),
                "Published_Date": "Unknown",
                "Heading": question,
                "URL": item.get("link"),
                "Body_Snippet": item.get("snippet", ""),
                "Source_Site": "Google Q&A"
            })

    # Single, clean save block
    if results:
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n✅ Successfully saved {len(df)} total records to {filename}")
    else:
        print("\n❌ No results found to save.")

if __name__ == "__main__":
    # FIX: Removed the double quotes wrapping the string and the https://
    my_keyword = "site:https://www.facebook.com/Emsphere.at.emdistrict"
    start_date = "2026-01-01"
    end_date = "2026-06-01" 
    
    # List the domains you want to exclude (do not include "www" or "https://")
    websites_to_ignore = [
        "linkedin.com", 
        "jobsdb.com", 
        "th.indeed.com", 
        "jobthai.com"
    ]
    
    print(f"Starting analysis for '{my_keyword}' in Thailand from {start_date} to {end_date}...")
    
    raw_data = fetch_social_listening_data(
        keyword=my_keyword, 
        date_after=start_date, 
        date_before=end_date, 
        exclude_sites=websites_to_ignore, 
        pages_to_scrape=30, 
        country_code="th"
    )
    
    # FIX: Stripped slashes and colons so the OS allows the file creation
    safe_filename = my_keyword.replace('"', '').replace(':', '_').replace('/', '_').replace(' ', '_')
    save_to_csv(raw_data, f"Listening/insights_{safe_filename}.csv")