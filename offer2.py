from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
import time
import random

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Remove headless mode for testing
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-extensions')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), 
                          options=options)

def search_amazon_products(driver, keywords, max_items=50, max_retries=3):
    products = []
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Use Amazon's search page instead of deals page
            url = f"https://www.amazon.com/s?k={keywords.replace(' ', '+')}&deals-widget=%257B%2522version%2522%253A1%252C%2522viewIndex%2522%253A0%252C%2522presetId%2522%253A%2522deals-collection-all-deals%2522%257D"
            print(f"Searching URL: {url}")
            
            # Add random delay before each request
            time.sleep(random.uniform(2, 5))
            driver.get(url)
            
            # Simulate human-like scrolling
            for _ in range(3):
                scroll_height = random.randint(100, 500)
                driver.execute_script(f"window.scrollBy(0, {scroll_height});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]'))
            )
            
            items = driver.find_elements(By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]')
            print(f"Found {len(items)} items")
            
            for item in items[:max_items]:
                try:
                    # Wait for each element
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of(item)
                    )
                    title = item.find_element(By.CSS_SELECTOR, 'h2 span').text
                    # Update price selectors to match Amazon's current structure
                    price_whole = item.find_elements(By.CSS_SELECTOR, '.a-price:not(.a-text-price) .a-price-whole')
                    price_fraction = item.find_elements(By.CSS_SELECTOR, '.a-price:not(.a-text-price) .a-price-fraction')
                    original_price_element = item.find_elements(By.CSS_SELECTOR, '.a-text-price .a-offscreen')
                    
                    if price_whole and original_price_element:
                        current_price = float(f"{price_whole[0].text}.{price_fraction[0].text if price_fraction else '00'}")
                        original_price_text = original_price_element[0].get_attribute('innerHTML')
                        list_price = float(original_price_text.replace('$', '').replace(',', ''))
                        
                        print(f"\nProduct: {title[:50]}...")
                        print(f"Current Price: ${current_price}")
                        print(f"Original Price: ${list_price}")
                        
                        if list_price > current_price:
                            discount = round((list_price - current_price) / list_price * 100, 2)
                            print(f"Discount: {discount}%")
                            
                            products.append({
                                'title': title,  # Remove discount from title
                                'current_price': current_price,
                                'original_price': list_price,
                                'url': item.find_element(By.CSS_SELECTOR, 'h2 a').get_attribute('href'),
                                'discount': discount
                            })
                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue
                    
            break  # If successful, exit retry loop
            
        except Exception as e:
            retry_count += 1
            print(f"Attempt {retry_count} failed: {str(e)}")
            if retry_count < max_retries:
                time.sleep(random.uniform(5, 10))  # Wait before retrying
            else:
                print("Max retries reached, moving to next search term")
    return products

def filter_discounted_products(products, min_discount=10):  # Changed default to match MIN_DISCOUNT_PERCENTAGE
    filtered = [p for p in products if p['discount'] >= min_discount]
    print(f"Filtering products: {len(products)} total, {len(filtered)} with {min_discount}%+ discount")
    return filtered

def save_to_csv(products, filename="discounted_products.csv"):
    df = pd.DataFrame(products)
    # Reorder columns and rename for clarity
    df = df[['title', 'current_price', 'original_price', 'discount', 'url']]  # Keep discount column
    df.columns = ['Product', 'Current Price ($)', 'Original Price ($)', 'Discount (%)', 'URL']
    df.to_csv(filename, index=False)
    print(f"Saved {len(products)} discounted products to {filename}")

if __name__ == "__main__":
    MIN_DISCOUNT_PERCENTAGE = 10
    search_categories = {
        'deals': ['clearance', 'discount', 'sale', 'deal'],
        'electronics': ['laptop deals', 'tablet sale', 'phone deals'],
        'home': ['home deals', 'kitchen sale', 'furniture deals'],
        'fashion': ['fashion deals', 'clothing sale', 'shoes clearance']
    }
    
    driver = None
    try:
        driver = setup_driver()
        driver.implicitly_wait(10)
        all_products = []
        
        for category, terms in search_categories.items():
            print(f"\nSearching in category: {category}")
            for keywords in terms:
                print(f"Searching for: {keywords}")
                time.sleep(random.uniform(3, 7))  # Add delay between searches
                products = search_amazon_products(driver, f"{keywords}")
                print(f"Found {len(products)} products before filtering")
                discounted = filter_discounted_products(products, min_discount=MIN_DISCOUNT_PERCENTAGE)
                print(f"Kept {len(discounted)} products after filtering for {MIN_DISCOUNT_PERCENTAGE}%+ discount")
                all_products.extend(discounted)
        
        if all_products:
            unique_products = {p['url']: p for p in all_products}.values()
            save_to_csv(list(unique_products), f"amazon_deals_{datetime.now().strftime('%Y%m%d')}.csv")
            print(f"\nTotal unique products found: {len(unique_products)}")
        else:
            print(f"No products with {MIN_DISCOUNT_PERCENTAGE}% or more discount found.")  # Modified to use variable
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
