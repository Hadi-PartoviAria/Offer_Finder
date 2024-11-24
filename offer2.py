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
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import undetected_chromedriver as uc

def setup_driver():
    options = uc.ChromeOptions()
    ua = UserAgent()
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'--user-agent={ua.random}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    
    driver = uc.Chrome(options=options)
    
    # Add stealth JavaScript
    stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = {
            runtime: {}
        };
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': stealth_js
    })
    
    return driver

def get_user_discount():
    while True:
        try:
            discount = float(input("Enter minimum discount percentage (0-100): "))
            if 0 <= discount <= 100:
                return discount
            print("Please enter a value between 0 and 100")
        except ValueError:
            print("Please enter a valid number")

def detect_product_category(title):
    """Detect product category based on keywords in title."""
    title = title.lower()
    categories = {
        'laptop': ['laptop', 'notebook', 'chromebook'],
        'tablet': ['tablet', 'ipad', 'galaxy tab'],
        'phone': ['phone', 'iphone', 'smartphone', 'galaxy s', 'pixel'],
        'headphone': ['headphone', 'earphone', 'earbud', 'airpod'],
        'tv': ['tv', 'television', 'smart tv', 'oled', 'qled'],
        'camera': ['camera', 'webcam', 'security cam'],
        'gaming': ['gaming', 'xbox', 'playstation', 'nintendo', 'console'],
        'computer': ['desktop', 'pc', 'computer', 'monitor'],
        'wearable': ['watch', 'smartwatch', 'fitness tracker', 'band'],
        'clothing': ['shirt', 'pants', 'jacket', 'dress', 'shoes', 'clothing'],
        'home': ['furniture', 'chair', 'table', 'bed', 'sofa', 'mattress'],
        'kitchen': ['kitchen', 'cookware', 'appliance', 'refrigerator', 'microwave']
    }
    
    for category, keywords in categories.items():
        if any(keyword in title for keyword in keywords):
            return category
    return 'other'

def search_amazon_products(driver, keywords, max_items=50, max_retries=3):
    products = []
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            url = f"https://www.amazon.com/s?k={keywords.replace(' ', '+')}&deals-widget=%257B%2522version%2522%253A1%252C%2522viewIndex%2522%253A0%252C%2522presetId%2522%253A%2522deals-collection-all-deals%2522%257D"
            print(f"Searching URL: {url}")
            
            time.sleep(random.uniform(2, 5))
            driver.get(url)
            
            # Simulate human-like scrolling
            for _ in range(3):
                scroll_height = random.randint(100, 500)
                driver.execute_script(f"window.scrollBy(0, {scroll_height});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Use BeautifulSoup to parse the page
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.select('div[data-component-type="s-search-result"]')
            print(f"Found {len(items)} items")
            
            for item in items[:max_items]:
                try:
                    title_elem = item.select_one('h2 span.a-text-normal')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    
                    # Get original price first
                    original_price_elem = item.select_one('.a-text-price .a-offscreen')
                    if not original_price_elem:
                        continue
                        
                    original_price_str = original_price_elem.text.replace('$', '').replace(',', '').replace('..', '.')
                    original_price = float(original_price_str)
                    
                    # Get current price
                    price_whole = item.select_one('.a-price:not(.a-text-price) .a-price-whole')
                    price_fraction = item.select_one('.a-price:not(.a-text-price) .a-price-fraction')
                    if not price_whole:
                        continue
                    
                    current_price_str = f"{price_whole.text}.{price_fraction.text if price_fraction else '00'}".replace('..', '.')
                    current_price = float(current_price_str)
                    
                    if current_price > 0 and original_price > current_price:  # Add validation
                        discount = round((original_price - current_price) / original_price * 100, 2)
                        print(f"\nProduct: {title[:50]}...")
                        print(f"Current Price: ${current_price}")
                        print(f"Original Price: ${original_price}")
                        print(f"Discount: {discount}%")
                        
                        # Get product URL
                        url_elem = item.select_one('h2 a.a-link-normal')
                        if url_elem:
                            product_url = url_elem.get('href')
                            if not product_url.startswith('http'):
                                product_url = 'https://www.amazon.com' + product_url
                            
                            product_info = {
                                'title': title,
                                'current_price': current_price,
                                'original_price': original_price,
                                'url': product_url,
                                'discount': discount,
                                'source': 'Amazon',
                                'category': detect_product_category(title)
                            }
                            products.append(product_info)
                            print(f"Added Amazon product with {discount}% discount")
                            
                except Exception as e:
                    print(f"Error processing Amazon item: {str(e)}")
                    continue
            
            # Return collected products if any were found
            if products:
                print(f"Found {len(products)} valid Amazon products")
                return products
            
            retry_count += 1
            
        except Exception as e:
            retry_count += 1
            print(f"Amazon attempt {retry_count} failed: {str(e)}")
            if retry_count < max_retries:
                time.sleep(random.uniform(5, 10))
    
    return products  # Return empty list if no products found

def search_bestbuy_products(driver, keywords, max_items=50, max_retries=3):
    products = []
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            url = f"https://www.bestbuy.com/site/searchpage.jsp?st={keywords.replace(' ', '+')}&cp=1"
            print(f"Searching Best Buy URL: {url}")
            
            driver.get(url)
            time.sleep(random.uniform(5, 8))
            
            # Try to handle cookie consent and popups
            try:
                popup_buttons = driver.find_elements(By.CSS_SELECTOR, 'button[class*="close"], .modal-close')
                for button in popup_buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(1)
            except:
                pass
            
            # Use BeautifulSoup for parsing
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.select('div.list-item, div[class*="product-item"]')
            
            if not items:
                print("No items found with primary selectors, trying alternative...")
                items = soup.select('div[class*="product"]')
            
            print(f"Found {len(items)} items on Best Buy using BeautifulSoup")
            
            for item in items[:max_items]:
                try:
                    # Extract title
                    title_elem = item.select_one('h4 a, .product-title a, a[class*="title"]')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    
                    # Extract current price
                    price_elem = item.select_one('div[class*="price"] span[aria-hidden="true"], .current-price')
                    if not price_elem:
                        continue
                    current_price = float(price_elem.get_text().replace('$', '').replace(',', '').strip())
                    
                    # Extract original price
                    original_price_elem = item.select_one('.was-price, [class*="original-price"]')
                    if original_price_elem:
                        original_price = float(original_price_elem.get_text().replace('$', '').replace('Was ', '').replace(',', '').strip())
                        
                        if original_price > current_price:
                            discount = round((original_price - current_price) / original_price * 100, 2)
                            product_url = title_elem.get('href')
                            if not product_url.startswith('http'):
                                product_url = 'https://www.bestbuy.com' + product_url
                        
                            product_info = {
                                'title': title,
                                'current_price': current_price,
                                'original_price': original_price,
                                'url': product_url,
                                'discount': discount,
                                'source': 'Best Buy',
                                'category': detect_product_category(title)
                            }
                            products.append(product_info)
                            print(f"Added Best Buy product with {discount}% discount")
                
                except Exception as e:
                    print(f"Error processing Best Buy item: {str(e)}")
                    continue
            
            break  # Break the retry loop if successful
            
        except Exception as e:
            retry_count += 1
            print(f"Best Buy attempt {retry_count} failed: {str(e)}")
            if retry_count < max_retries:
                time.sleep(random.uniform(10, 15))
    
    print(f"Found {len(products)} valid Best Buy products")
    return products

def filter_discounted_products(products, min_discount=50):  # Changed default to match MIN_DISCOUNT_PERCENTAGE
    filtered = [p for p in products if p['discount'] >= min_discount]
    print(f"Filtering products: {len(products)} total, {len(filtered)} with {min_discount}%+ discount")
    return filtered

def save_to_csv(products, filename="discounted_products.csv"):
    df = pd.DataFrame(products)
    # Reorder columns and rename for clarity
    df = df[['title', 'category', 'current_price', 'original_price', 'discount', 'url', 'source']]  # Add category
    df.columns = ['Product', 'Category', 'Current Price ($)', 'Original Price ($)', 'Discount (%)', 'URL', 'Source']
    
    # Sort by discount percentage in descending order
    df = df.sort_values(by='Discount (%)', ascending=False)
    
    df.to_csv(filename, index=False)
    print(f"Saved {len(products)} discounted products to {filename} (sorted by discount percentage)")

if __name__ == "__main__":
    MIN_DISCOUNT_PERCENTAGE = get_user_discount()
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
                
                # Search both Amazon and Best Buy
                amazon_products = search_amazon_products(driver, f"{keywords}")
                bestbuy_products = search_bestbuy_products(driver, f"{keywords}")
                
                # Filter products meeting discount threshold
                amazon_filtered = filter_discounted_products(amazon_products, min_discount=MIN_DISCOUNT_PERCENTAGE)
                bestbuy_filtered = filter_discounted_products(bestbuy_products, min_discount=MIN_DISCOUNT_PERCENTAGE)
                
                all_products.extend(amazon_filtered)
                all_products.extend(bestbuy_filtered)
                
                print(f"Category '{category}' - '{keywords}': Found {len(amazon_filtered)} Amazon and {len(bestbuy_filtered)} Best Buy products meeting {MIN_DISCOUNT_PERCENTAGE}% discount threshold")
        
        if all_products:
            unique_products = {p['url']: p for p in all_products}.values()
            save_to_csv(list(unique_products), f"deals_{datetime.now().strftime('%Y%m%d')}.csv")
            print(f"\nTotal unique products found: {len(unique_products)}")
        else:
            print(f"No products with {MIN_DISCOUNT_PERCENTAGE}% or more discount found.")  # Modified to use variable
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
