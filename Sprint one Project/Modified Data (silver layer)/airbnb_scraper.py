import pandas as pd
import time
import os
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# CONFIGURATION

LISTINGS_PER_CITY = 5  # How many apartments to scrape per city

# Map our dataset city names to Airbnb search-friendly names
CITY_SEARCH_NAMES = {
    "amsterdam": "Amsterdam--Netherlands",
    "athens": "Athens--Greece",
    "barcelona": "Barcelona--Spain",
    "berlin": "Berlin--Germany",
    "budapest": "Budapest--Hungary",
    "lisbon": "Lisbon--Portugal",
    "london": "London--United-Kingdom",
    "paris": "Paris--France",
    "rome": "Rome--Italy",
    "vienna": "Vienna--Austria",
}

def setup_browser():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-geolocation") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    
    prefs = {"profile.default_content_setting_values.geolocation": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# 1. Paths
input_path = "C:/Users/medod/Desktop/Sprint one Project/Modified Data (silver layer)/airbnb_europe_clean.csv"
output_path = "C:/Users/medod/Desktop/Sprint one Project/Modified Data (silver layer)/airbnb_scraped_reviews.csv"

# 2. Load Data
print(f"Loading data from {input_path}")
df_full = pd.read_csv(input_path)

# 3. Pick 10 RANDOM apartments per city (using their real lat/lng)
print(f"\nSelecting {LISTINGS_PER_CITY} random apartments per city...")
sampled_rows = []
for city in sorted(df_full['city'].unique()):
    city_data = df_full[df_full['city'] == city]
    n = min(LISTINGS_PER_CITY, len(city_data))
    sample = city_data.sample(n=n, random_state=42)
    sampled_rows.append(sample)
    print(f"  {city:15s}: selected {n} apartments (out of {len(city_data)})")

df = pd.concat(sampled_rows).reset_index(drop=True)
df['scraped_property_type'] = None
df['scraped_reviews'] = None
df['scraped_rating'] = None

print(f"\nTotal apartments to scrape: {len(df)}")

# 4. Resume support: if output exists, load it
if os.path.exists(output_path):
    print(f"\nFound existing progress at {output_path}, loading...")
    df_existing = pd.read_csv(output_path)
    # Only resume if it has the same structure
    if 'scraped_property_type' in df_existing.columns and len(df_existing) == len(df):
        df = df_existing
        already_done = df['scraped_property_type'].notna().sum()
        print(f"  Resuming from {already_done} already scraped rows")

# 5. Start browser
driver = setup_browser()



scraped_count = 0
failed_count = 0
skipped_count = 0

for index, row in df.iterrows():
    # Skip rows already scraped successfully
    if pd.notna(row['scraped_property_type']) and str(row['scraped_property_type']) != 'Not Found':
        skipped_count += 1
        continue
    
    lat = row['latitude']
    lng = row['longitude']
    city = row['city']
    
    # Get the Airbnb-friendly city name
    airbnb_city = CITY_SEARCH_NAMES.get(city, city)
    
    # Create TINY bounding box around the EXACT lat/lng from your data
    # 0.001 = ~100 meters, so it searches right where your data says
    offset = 0.001
    ne_lat = lat + offset
    ne_lng = lng + offset
    sw_lat = lat - offset
    sw_lng = lng - offset
    
    search_url = (
        f"https://www.airbnb.com/s/{airbnb_city}/homes"
        f"?ne_lat={ne_lat}&ne_lng={ne_lng}"
        f"&sw_lat={sw_lat}&sw_lng={sw_lng}"
        f"&zoom=17&search_mode=regular_search"
    )
    
    print(f"[{index + 1}/{len(df)}] {city} | lat={lat:.4f}, lng={lng:.4f}...", end=" ")
    driver.get(search_url)
    
    # delay (3-5 seconds)
    time.sleep(random.uniform(3, 5))
    
    try:
        # Find the first listing link
        first_listing = driver.find_element(By.CSS_SELECTOR, 'a[href^="/rooms/"]')
        listing_url = first_listing.get_attribute('href').split('?')[0]
        
        # Visit the listing page
        driver.get(listing_url)
        time.sleep(random.uniform(3, 5))
        
        #EXTRACT PROPERTY TYPE 
        prop_type = None
        try:
            prop_type_el = driver.find_element(By.CSS_SELECTOR, 'h2[tabindex="-1"]')
            prop_type = prop_type_el.text
            
            # VALIDATION: Check if result is actually in the right country
            bad_locations = ['egypt', 'cairo', 'giza', 'ossim', 'oasim', 'new cairo', 'hurghada', 'sharm']
            if any(bad in prop_type.lower() for bad in bad_locations):
                print(f"WRONG LOCATION (got Egypt) - skipping")
                df.at[index, 'scraped_property_type'] = 'Not Found'
                df.at[index, 'scraped_reviews'] = 0
                df.at[index, 'scraped_rating'] = None
                failed_count += 1
                df.to_csv(output_path, index=False)
                continue
                
            df.at[index, 'scraped_property_type'] = prop_type
        except:
            pass
        
        #EXTRACT NUMBER OF REVIEWS
        try:
            review_el = driver.find_element(By.XPATH, "//span[contains(text(), 'reviews') or contains(text(), 'review')]")
            text = review_el.text
            num_only = int(''.join(filter(str.isdigit, text)))
            df.at[index, 'scraped_reviews'] = num_only
        except:
            pass
            
        #EXTRACT RATING
        try:
            # Often near the reviews or in an element containing 'out of 5' or just the star
            import re
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            rating_match = re.search(r'(\d\.\d{1,2})\s*·', page_text)
            if not rating_match:
                rating_match = re.search(r'★\s*(\d\.\d{1,2})', page_text)
            if not rating_match:
                rating_match = re.search(r'(\d\.\d{1,2})\s*(?:out of|/)\s*5', page_text)
            if rating_match:
                df.at[index, 'scraped_rating'] = float(rating_match.group(1))
        except:
            pass
        
        if prop_type:
            rating_str = f" | {df.at[index, 'scraped_rating']}★" if pd.notna(df.at[index, 'scraped_rating']) else ""
            print(f"OK -> {prop_type} | {df.at[index, 'scraped_reviews']} reviews{rating_str}")
            scraped_count += 1
        else:
            print("No property type found")
            df.at[index, 'scraped_property_type'] = 'Not Found'
            df.at[index, 'scraped_reviews'] = 0
            df.at[index, 'scraped_rating'] = None
            failed_count += 1
            
    except Exception as e:
        print("No listings found at these coordinates")
        df.at[index, 'scraped_property_type'] = 'Not Found'
        df.at[index, 'scraped_reviews'] = 0
        df.at[index, 'scraped_rating'] = None
        failed_count += 1

    # Save after EVERY row
    df.to_csv(output_path, index=False)

driver.quit()

