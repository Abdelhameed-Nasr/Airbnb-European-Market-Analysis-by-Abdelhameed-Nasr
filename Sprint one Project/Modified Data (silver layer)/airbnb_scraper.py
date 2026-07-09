import pandas as pd
import time
import os
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# CONFIGURATION
LISTINGS_PER_CITY = 50  # How many VALID apartments per city (50 x 10 = 500)
MAX_LISTINGS_TO_CHECK = 20  # How many listings to check at each coordinate before giving up

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
    driver.set_page_load_timeout(20)  # Prevents freezing if a page gets stuck loading
    return driver


def extract_bedrooms_from_page(driver):
    """Try to extract the number of bedrooms from an Airbnb listing page."""
    try:
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        # Airbnb shows "X bedrooms" or "X bedroom" or "Studio"
        match = re.search(r'(\d+)\s*bedroom', page_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        # Studio = 0 bedrooms
        if re.search(r'\bstudio\b', page_text, re.IGNORECASE):
            return 0
    except:
        pass
    return None


def extract_capacity_from_page(driver):
    """Try to extract the max guest capacity from an Airbnb listing page."""
    try:
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        # Airbnb shows "X guests" 
        match = re.search(r'(\d+)\s*guest', page_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except:
        pass
    return None


def extract_room_type_from_page(driver):
    """Try to extract the room type from the listing page."""
    try:
        prop_type_el = driver.find_element(By.CSS_SELECTOR, 'h2[tabindex="-1"]')
        prop_text = prop_type_el.text.lower()
        if 'entire' in prop_text:
            return 'Entire home/apt'
        elif 'private' in prop_text:
            return 'Private room'
        elif 'shared' in prop_text:
            return 'Shared room'
    except:
        pass
    return None


def verify_listing(driver, original_row):
    """
    Check if the listing on the current page matches the original dataset row.
    Compares: room_type, bedrooms, person_capacity
    Returns: (is_match, match_details_string)
    """
    checks_passed = 0
    checks_total = 0
    details = []
    
    # CHECK 1: Room type
    scraped_room_type = extract_room_type_from_page(driver)
    original_room_type = original_row.get('room_type', None)
    if scraped_room_type and original_room_type:
        checks_total += 1
        if scraped_room_type == original_room_type:
            checks_passed += 1
            details.append(f"room_type=MATCH")
        else:
            details.append(f"room_type=MISMATCH ({scraped_room_type} vs {original_room_type})")
            # Room type mismatch is a dealbreaker
            return False, ", ".join(details)
    
    # CHECK 2: Bedrooms
    scraped_bedrooms = extract_bedrooms_from_page(driver)
    original_bedrooms = original_row.get('bedrooms', None)
    if scraped_bedrooms is not None and pd.notna(original_bedrooms):
        checks_total += 1
        original_bedrooms = int(original_bedrooms)
        if scraped_bedrooms == original_bedrooms:
            checks_passed += 1
            details.append(f"bedrooms=MATCH({scraped_bedrooms})")
        else:
            details.append(f"bedrooms=MISMATCH ({scraped_bedrooms} vs {original_bedrooms})")
            return False, ", ".join(details)
    
    # CHECK 3: Guest capacity
    scraped_capacity = extract_capacity_from_page(driver)
    original_capacity = original_row.get('person_capacity', None)
    if scraped_capacity is not None and pd.notna(original_capacity):
        checks_total += 1
        original_capacity = int(original_capacity)
        # Allow +/- 1 person tolerance (hosts sometimes update capacity)
        if abs(scraped_capacity - original_capacity) <= 1:
            checks_passed += 1
            details.append(f"capacity=MATCH({scraped_capacity}≈{original_capacity})")
        else:
            details.append(f"capacity=MISMATCH ({scraped_capacity} vs {original_capacity})")
            return False, ", ".join(details)
    
    # Need at least 2 checks to pass for a confident match
    if checks_total >= 2 and checks_passed >= 2:
        return True, ", ".join(details)
    elif checks_total == 1 and checks_passed == 1:
        # Only 1 check possible but it passed — accept with warning
        return True, ", ".join(details) + " (partial verify)"
    elif checks_total == 0:
        # Could not extract any data to compare — skip this one
        return False, "could not extract data to verify"
    
    return False, ", ".join(details)


# 1. Paths
input_path = "C:/Users/medod/Desktop/Sprint one Project/Modified Data (silver layer)/airbnb_europe_clean.csv"
output_path = "C:/Users/medod/Desktop/Sprint one Project/Modified Data (silver layer)/airbnb_scraped_reviews.csv"

# 2. Load Data
print(f"Loading data from {input_path}")
df_full = pd.read_csv(input_path)

# 3. Start browser
driver = setup_browser()

# Warm up like a real human
print("Warming up browser...")
driver.get("https://www.google.com")
time.sleep(random.uniform(3, 5))
driver.get("https://www.airbnb.com")
time.sleep(random.uniform(8, 12))

# 4. Scrape each city — only keep VERIFIED results
all_results = []

# Resume support
already_scraped_cities = set()
if os.path.exists(output_path):
    print(f"\nFound existing progress at {output_path}, loading...")
    df_existing = pd.read_csv(output_path)
    all_results = df_existing.to_dict('records')
    for city in df_full['city'].unique():
        city_count = len([r for r in all_results if r.get('city') == city])
        if city_count >= LISTINGS_PER_CITY:
            already_scraped_cities.add(city)
            print(f"  {city}: already has {city_count} verified results — SKIPPING")

for city in sorted(df_full['city'].unique()):
    if city in already_scraped_cities:
        continue
    
    airbnb_city = CITY_SEARCH_NAMES.get(city, city)
    city_data = df_full[df_full['city'] == city].copy()
    
    # Shuffle rows so we try random coordinates each run
    city_data = city_data.sample(frac=1, random_state=random.randint(1, 9999)).reset_index(drop=True)
    
    existing_city_count = len([r for r in all_results if r.get('city') == city])
    valid_count = existing_city_count
    coord_attempts = 0
    
    print(f"\n{'='*60}")
    print(f"CITY: {city.upper()} | Need {LISTINGS_PER_CITY} verified apartments (have {existing_city_count})")
    print(f"  Available coordinates to try: {len(city_data)}")
    print(f"{'='*60}")
    
    for _, row in city_data.iterrows():
        if valid_count >= LISTINGS_PER_CITY:
            break
        
        coord_attempts += 1
        lat = row['latitude']
        lng = row['longitude']
        
        # Create bounding box around this coordinate
        offset = 0.001
        search_url = (
            f"https://www.airbnb.com/s/{airbnb_city}/homes"
            f"?ne_lat={lat + offset}&ne_lng={lng + offset}"
            f"&sw_lat={lat - offset}&sw_lng={lng - offset}"
            f"&zoom=17&search_mode=regular_search"
        )
        
        print(f"\n  Coord #{coord_attempts} | Valid: {valid_count}/{LISTINGS_PER_CITY} | lat={lat:.4f}, lng={lng:.4f}")
        
        try:
            driver.get(search_url)
            time.sleep(random.uniform(3, 5))
            
            # Find ALL listing links on the search page
            listing_links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/rooms/"]')
            
            if not listing_links:
                print(f"    No listings found at this location — trying next coordinate")
                continue
            
            # Get unique listing URLs (Airbnb sometimes duplicates links)
            seen_urls = set()
            unique_urls = []
            for link in listing_links:
                url = link.get_attribute('href').split('?')[0]
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_urls.append(url)
            
            num_to_check = min(len(unique_urls), MAX_LISTINGS_TO_CHECK)
            print(f"    Found {len(unique_urls)} listings. Checking up to {num_to_check}...")
            
            # Check each listing one by one
            found_match = False
            for i, listing_url in enumerate(unique_urls[:num_to_check]):
                print(f"      Listing {i+1}/{num_to_check}...", end=" ")
                
                try:
                    driver.get(listing_url)
                    time.sleep(random.uniform(3, 5))
                    
                    # Check for Egypt redirect
                    try:
                        prop_type_el = driver.find_element(By.CSS_SELECTOR, 'h2[tabindex="-1"]')
                        prop_type = prop_type_el.text
                        bad_locations = ['egypt', 'cairo', 'giza', 'ossim', 'oasim', 'new cairo', 'hurghada', 'sharm']
                        if any(bad in prop_type.lower() for bad in bad_locations):
                            print("WRONG LOCATION (Egypt) — skipping")
                            continue
                    except:
                        prop_type = None
                    
                    if not prop_type:
                        print("No data — skipping")
                        continue
                    
                    # VERIFY: Does this listing match our original data?
                    is_match, match_details = verify_listing(driver, row)
                    
                    if not is_match:
                        print(f"MISMATCH ({match_details}) — trying next listing")
                        continue
                    
                    # MATCH FOUND! Extract the live data
                    print(f"VERIFIED MATCH! ({match_details})")
                    
                    # Extract reviews
                    num_reviews = 0
                    try:
                        review_el = driver.find_element(By.XPATH, "//span[contains(text(), 'reviews') or contains(text(), 'review')]")
                        text = review_el.text
                        num_reviews = int(''.join(filter(str.isdigit, text)))
                    except:
                        pass
                    
                    # Extract rating
                    rating = None
                    try:
                        page_text = driver.find_element(By.TAG_NAME, 'body').text
                        rating_match = re.search(r'(\d\.\d{1,2})\s*·', page_text)
                        if not rating_match:
                            rating_match = re.search(r'★\s*(\d\.\d{1,2})', page_text)
                        if not rating_match:
                            rating_match = re.search(r'(\d\.\d{1,2})\s*(?:out of|/)\s*5', page_text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                    except:
                        pass
                    
                    # Save the verified result
                    valid_count += 1
                    rating_str = f" | {rating}★" if rating else ""
                    print(f"      >> SAVED: {prop_type} | {num_reviews} reviews{rating_str}")
                    
                    result_row = row.to_dict()
                    result_row['scraped_property_type'] = prop_type
                    result_row['Reviews'] = num_reviews
                    result_row['Ratings'] = rating
                    all_results.append(result_row)
                    
                    # Save progress after every verified result
                    pd.DataFrame(all_results).to_csv(output_path, index=False)
                    
                    found_match = True
                    break  # Found a match at this coordinate, move to next coordinate
                    
                except Exception as listing_err:
                    print(f"FAILED TO LOAD ({str(listing_err)[:30]}) — skipping this listing")
                    continue
            
            if not found_match:
                print(f"    No matching apartment found at this coordinate — trying next")
                
        except Exception as e:
            print(f"    Error: {str(e)[:50]} — trying next coordinate")
            continue

    print(f"\n  >> {city.upper()} DONE: Got {valid_count} verified apartments out of {coord_attempts} coordinates tried")

driver.quit()

print(f"\n{'='*60}")
print(f"ALL DONE!")
print(f"  Total verified apartments scraped: {len(all_results)}")
print(f"  Saved to: {output_path}")
print(f"{'='*60}")
