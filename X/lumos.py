import csv
import time
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# Your Twitter credentials
load_dotenv()

# Log into Twitter
def twitter_login():
    driver.get("https://twitter.com/login")
    time.sleep(2)  # Wait for the login page to load

    # Enter username/handle
    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "text"))
    )
    username_field.send_keys(USERNAME)
    username_field.send_keys(Keys.RETURN)
    time.sleep(2)  # Wait for the password field to load

    # Enter password
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "password"))
    )
    password_field.send_keys(PASSWORD)
    password_field.send_keys(Keys.RETURN)
    time.sleep(5)  # Wait for login to complete

# Perform the login
#twitter_login()

# Open and read URLs from the file
with open("X/Twitter_urls.txt", "r") as file:
    urls = [url.strip() for url in file.readlines()]  # Remove newlines

# Open a CSV file to write the results
with open("X/Twitter_output.csv", "w", newline="") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=';')
    csv_writer.writerow(["URL", "Views", "Engagement", "Comments", "Retweet", "Likes"])  # Write header
    
    for url in urls:
        if "/status" in url:
            try:
                driver.get(url)
                time.sleep(2)  # Wait for elements to load
                views = 0
                engagements = 0
                comments = 0
                retweets = 0
                likes = 0
                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'css-175oi2r r-xoduu5 r-1udh08x')]")

                # Extract numbers in order (Views, Comments, Retweets, Likes)
                extracted_values = [elem.text for elem in elements if elem.text.strip()]
                # Ensure we have at least 4 values, otherwise assign "0"
                views = extracted_values[0] if len(extracted_values) > 0 else "0"
                comments = extracted_values[1] if len(extracted_values) > 1 else "0"
                retweets = extracted_values[2] if len(extracted_values) > 2 else "0"
                likes = extracted_values[3] if len(extracted_values) > 3 else "0"

                # Write data to CSV
                print(f"✅ Extracted: {url} - Views: {views}, Comments: {comments}, Retweets: {retweets}, Likes: {likes}")
                cleaned_views = extract_numbers(views)
                cleaned_comments = extract_numbers(comments)
                cleaned_retweets = extract_numbers(retweets)
                cleaned_likes = extract_numbers(likes)
                engagements = cleaned_comments + cleaned_retweets + cleaned_likes
                csv_writer.writerow([url, cleaned_views, engagements, cleaned_comments, cleaned_retweets, cleaned_likes])

            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error", "Error", "Error", "Error", "Error"])

driver.quit()
print("✅ Data extraction completed. Check 'X/Twitter_output.csv'.")
