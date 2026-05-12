import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# This program is for Droidsans / MXphone / Flashfly / Siamphone / Techmoblog / iMod / Specphone / TechXcite
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
with open("Website/website_url.txt", "r") as file:
    urls = file.readlines()

# Open a CSV file to write the results
with open("Website/website_output.csv", "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=';')
    csv_writer.writerow(["urls", "view"])  # Write header
    
    for url in urls:
        url = url.strip()  # Remove any extra whitespace or newline
        url = url.strip('"')  # Remove quotes if they are present

        if "droidsans.com" in url or "mxphone.com" in url:
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'post-stats')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]
                if extracted_values:
                    views = extracted_values[0]  # Get the first view value
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found
                
                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])

                print(f"✅ Extracted: {url} - Views: {cleaned_views}")
                    
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])
                
        elif "flashfly.net" in url: #Still WIP T T
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'jeg_Views_count')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]

                # Debugging print
                print(f"🔍 Extracted values for {url}: {extracted_values} - {len(elements)} - {elements}")
                print(driver.page_source)
                # Check if values are found
                if len(extracted_values) > 1:
                    views = extracted_values[1]  # Get the second value if it exists
                elif len(extracted_values) == 1:
                    views = extracted_values[0]  # Use the first value if only one exists
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found

                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])

            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])
                
        elif "siamphone.com" in url:
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'viewBadges')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]
                
                # Check if values are actually found
                if extracted_values:
                    views = extracted_values[0]  # Get the first view value
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found

                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])
                print(f"✅ Extracted: {url} - Views: {cleaned_views}")
                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])
                
        elif "techmoblog.com" in url:
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                element = driver.find_element(By.XPATH, "//div[contains(@class, 'box-social hidden-xs')]")

                # Extract all <span> elements inside the div
                spans = element.find_elements(By.TAG_NAME, "span")
                extracted_values = [span.text.strip() for span in spans if span.text.strip()]  # Fixed this line

                # Ensure at least one value exists
                if extracted_values:
                    views = extracted_values[1]  # Assuming the first <span> contains views
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value

                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))
                csv_writer.writerow([url, cleaned_views])

                # Debugging: Print extracted values
                print(f"✅ Extracted: {url} - Views: {cleaned_views}")
                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])

                
        elif "iphonemod.net" in url: 
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'entry-views')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]
                
                # Check if values are actually found
                if extracted_values:
                    views = extracted_values[0]  # Get the first view value
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found
                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])
                print(f"✅ Extracted: {url} - Views: {cleaned_views}")

                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])

        elif "specphone.com" in url:
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'meta-item views')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]
                # Check if values are actually found
                if extracted_values:
                    views = extracted_values[0]  # Get the first view value
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found
                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])
                print(f"✅ Extracted: {url} - Views: {cleaned_views}")

                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])

        elif "techxcite.com" in url: #Still Wip
            views = 0
            try:
                driver.get(url)
                time.sleep(1)  # Wait for elements to load

                # Find all elements with the matching class name
                elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'count-views')]")

                # Extract numbers in order (Views)
                extracted_values = [elem.text.strip() for elem in elements if elem.text.strip()]
                # Check if values are actually found
                if extracted_values:
                    views = extracted_values[0]  # Get the first view value
                else:
                    print(f"❌ No views found for {url}")
                    views = "0"  # Default value if no views found
                # Ensure it's a string before passing to extract_numbers()
                cleaned_views = extract_numbers(str(views))  
                csv_writer.writerow([url, cleaned_views])
                print(f"✅ Extracted: {url} - Views: {cleaned_views}")
                
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                csv_writer.writerow([url, "Error"])
                                                    
driver.quit()
print("✅ Data extraction completed. Check 'website_output.csv'.")
