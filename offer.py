import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def search_amazon(query, driver):
    try:
        url = f"https://www.amazon.com/s?k={query}"
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        # Wait for the main content to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".s-main-slot"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, ".s-result-item:not(.AdHolder)")
        
        for item in items:
            try:
                # Updated selectors
                title_element = item.find_element(By.CSS_SELECTOR, "h2 a span")
                price_element = item.find_elements(By.CSS_SELECTOR, ".a-price .a-offscreen")
                original_price_element = item.find_elements(By.CSS_SELECTOR, ".a-text-price .a-offscreen")
                link_element = item.find_element(By.CSS_SELECTOR, "h2 a")
                
                if title_element and price_element and link_element:
                    title = title_element.text
                    current_price = float(price_element[0].get_attribute('innerHTML').replace('$', '').replace(',', '').strip())
                    original_price = current_price
                    discount = 0.0
                    
                    if original_price_element:
                        try:
                            original_price = float(original_price_element[0].get_attribute('innerHTML').replace('$', '').replace(',', '').strip())
                            if original_price > current_price:
                                discount = ((original_price - current_price) / original_price) * 100
                        except: pass
                    
                    link = link_element.get_attribute("href")
                    
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })
            except Exception as e:
                print(f"Error processing Amazon item: {str(e)}")
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Amazon: {str(e)}")
        return []

def search_walmart(query, driver):
    try:
        url = f"https://www.walmart.com/search?q={query}"
        driver.get(url)
        time.sleep(random.uniform(3, 5))  # Increased delay for Walmart

        # Wait for product grid to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='list-view']"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='list-view'] > div")
        
        for item in items:
            try:
                # Updated selectors for Walmart
                title_element = WebDriverWait(item, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-automation-id='product-title']"))
                )
                price_element = item.find_element(By.CSS_SELECTOR, "[data-automation-id='product-price']")
                
                title = title_element.text
                current_price = float(price_text.replace('$', '').replace(',', '').strip())
                original_price = current_price
                discount = 0.0
                
                # Try to find original price
                try:
                    original_price_element = item.find_element(By.CSS_SELECTOR, "[data-automation-id='strikethrough-price']")
                    if original_price_element:
                        original_price = float(original_price_element.text.replace('$', '').replace(',', '').strip())
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass
                
                link = title_element.get_attribute("href")
                
                if title and current_price and link:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })
            except Exception as e:
                print(f"Error processing Walmart item: {str(e)}")
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Walmart: {str(e)}")
        return []

def save_to_csv(amazon_results, walmart_results, query):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"price_comparison_{query}_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Store', 'Title', 'Current Price', 'Original Price', 'Discount %', 'Link'])
        
        for product in amazon_results:
            writer.writerow([
                'Amazon', 
                product['title'], 
                f"${product['price']:.2f}", 
                f"${product['original_price']:.2f}", 
                f"{product['discount']:.1f}%", 
                product['link']
            ])
            
        for product in walmart_results:
            writer.writerow([
                'Walmart', 
                product['title'], 
                f"${product['price']:.2f}", 
                f"${product['original_price']:.2f}", 
                f"{product['discount']:.1f}%", 
                product['link']
            ])
    
    return filename

if __name__ == "__main__":
    query = input("Enter the product you want to search for: ")
    print("\nInitializing browser...")
    
    driver = setup_driver()
    
    try:
        print("Searching Amazon...")
        amazon_results = search_amazon(query, driver)
        print(f"Found {len(amazon_results)} results from Amazon")
        
        print("\nSearching Walmart...")
        walmart_results = search_walmart(query, driver)
        print(f"Found {len(walmart_results)} results from Walmart")
        
        if amazon_results:
            print("\nTop 5 Amazon Deals:")
            for product in amazon_results[:5]:
                print(f"Title: {product['title']}")
                print(f"Current Price: ${product['price']:.2f}")
                print(f"Original Price: ${product['original_price']:.2f}")
                print(f"Discount: {product['discount']:.1f}%")
                print(f"Link: {product['link']}\n")
                
        if walmart_results:
            print("\nTop 5 Walmart Deals:")
            for product in walmart_results[:5]:
                print(f"Title: {product['title']}")
                print(f"Current Price: ${product['price']:.2f}")
                print(f"Original Price: ${product['original_price']:.2f}")
                print(f"Discount: {product['discount']:.1f}%")
                print(f"Link: {product['link']}\n")
                
        if amazon_results or walmart_results:
            filename = save_to_csv(amazon_results, walmart_results, query)
            print(f"\nResults saved to: {filename}")
        else:
            print("\nNo results found to save.")
                
    finally:
        driver.quit()
