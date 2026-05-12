import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Define the extract_numbers function
def extract_numbers(text):
    text = text.replace(",", "")  # Remove commas
    match = re.search(r"(\d+\.?\d*)([KM]?)", text, re.IGNORECASE)
    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()
        if suffix == "K":
            return int(number * 1000)
        elif suffix == "M":
            return int(number * 1000000)
        return int(number)
    return 0

# Setup Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in the background
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open and read URLs from the file
with open("Facebook/facebook_urls.txt", "r") as file:
    urls = [url.strip() for url in file.readlines()]  # Remove newlines

# Open a CSV file to write the results
with open("Facebook/facebook_output.csv", "w", newline="") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=';')
    csv_writer.writerow(["URL", "Views", "Engagement", "Reactions", "Comments", "Shares"])  # Write header
    
    for url in urls:
        if "/videos" in url or "/watch" in url:
            views = "0"
            reactions = "0"
            shares = "0"
            comments = "0"
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load
                
                # Extract Views
                try:
                    views = driver.find_element(By.XPATH, "//span[contains(@class, '_26fq')]").text
                except:
                    views = "0"
                
                # Extract reactions
                try:
                    reactions = driver.find_element(By.XPATH, "//div[contains(@class, 'x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 x1ypdohk x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1fmog5m xu25z0z x140muxe xo1y3bh x1n2onr6 x87ps6o x1lku1pv x1a2a7pz x1heor9g x78zum5 x6ikm8r x10wlt62')]").text
                except:
                    reactions = "0"
            
                # Extract comments
                try:
                    comments = driver.find_elements(By.XPATH, "//span[contains(text(), 'comment')]")
                    comments = comments[0].text
                except:
                    comments = "0"
                '''
                Extract shares
                try:
                    shares = driver.find_element(By.XPATH, "//span[contains(@class, 'xkrqix3')]").text.split()[0]
                except:
                    shares = "0"
                '''
                # Write data to CSV
                print(comments)
                print(f"✅ Extracted Vid: {url} - Views: {views}, Reactions: {reactions}, Comments: {comments}, Shares: {shares}")
                cleaned_views = extract_numbers(views)
                cleaned_reactions = extract_numbers(reactions)
                cleaned_comments = extract_numbers(comments)
                cleaned_shares = extract_numbers(shares)                                
                engagements = cleaned_reactions + cleaned_comments + cleaned_shares
                csv_writer.writerow([url, cleaned_views, engagements, cleaned_reactions, cleaned_comments, cleaned_shares])

            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error", "Error", "Error", "Error", "Error"])
            
        else: 
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load
                # Extract reactions
                try:
                    reactions = driver.find_element(By.XPATH, "//div[contains(@class, 'x9f619') and contains(text(), 'All reactions:')]/following-sibling::span").text
                except:
                    reactions = "0"

                # Extract comments
                try:
                    elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'xkrqix3')]")
                    comments = elements[0].text if len(elements) > 0 else "0"
                    shares = elements[1].text if len(elements) > 1 else "0"
                except:
                    comments, shares = "0", "0"

                # Extract shares
                #try:
                    
                    #shares = driver.find_element(By.XPATH, "//span[contains(@class, 'xkrqix3')]").text.split()[0]
                #except:
                    #shares = "0"//

                # Write data to CSV
                print(f"✅ Extracted: {url} - Reactions: {reactions}, Comments: {comments}, Shares: {shares}")
                cleaned_reactions = extract_numbers(reactions)
                cleaned_comments = extract_numbers(comments)
                cleaned_shares = extract_numbers(shares)                                
                engagements = cleaned_reactions + cleaned_comments + cleaned_shares
                csv_writer.writerow([url, 0, engagements, cleaned_reactions, cleaned_comments, cleaned_shares])


            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error", "Error", "Error", "Error", "Error"])

driver.quit()
print("✅ Data extraction completed. Check 'facebook_output.csv'.")
