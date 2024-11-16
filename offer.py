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
    # Add more realistic browser behavior
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Mask webdriver presence
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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
                # Check if item has any price
                if not item.find_elements(By.CSS_SELECTOR, ".a-price"):
                    continue

                title_element = item.find_element(By.CSS_SELECTOR, "h2 a span")
                price_elements = item.find_elements(By.CSS_SELECTOR, ".a-price .a-offscreen")
                original_price_elements = item.find_elements(By.CSS_SELECTOR, 
                    ".a-text-price .a-offscreen, .a-price[data-a-strike='true'] .a-offscreen"
                )
                link_element = item.find_element(By.CSS_SELECTOR, "h2 a")
                
                if title_element and price_elements and link_element:
                    # Get full title from title attribute if available
                    title = title_element.text
                    title_attr = title_element.get_attribute('title')
                    if title_attr:
                        title = title_attr
                    try:
                        current_price = float(price_elements[0].get_attribute('innerHTML')
                            .replace('$', '').replace(',', '').strip())
                    except:
                        continue

                    original_price = current_price
                    discount = 0.0
                    
                    # Try multiple ways to find original price
                    for orig_price_elem in original_price_elements:
                        try:
                            price = float(orig_price_elem.get_attribute('innerHTML')
                                .replace('$', '').replace(',', '').strip())
                            if price > current_price:
                                original_price = price
                                discount = ((original_price - current_price) / original_price) * 100
                                break
                        except:
                            continue
                    
                    # Check for deal badge if no discount found
                    if discount == 0:
                        deal_badges = item.find_elements(By.CSS_SELECTOR, 
                            "span.a-badge-label, span.a-badge-supplementary-text"
                        )
                        for badge in deal_badges:
                            if any(word in badge.text.lower() for word in ['deal', 'save', 'off', '%']):
                                discount = 0.1  # Set a minimal discount to include the item
                                break
                    
                    link = link_element.get_attribute("href")
                    
                    if discount > 0:
                        products.append({
                            "title": title,
                            "price": current_price,
                            "original_price": original_price,
                            "discount": discount,
                            "link": link
                        })
            except Exception as e:
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Amazon: {str(e)}")
        return []

def search_walmart(query, driver):
    try:
        url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        # Updated wait and selectors
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='search-results']"))
            )
        except:
            print("Retrying Walmart load...")
            driver.refresh()
            time.sleep(3)

        # Updated item selectors
        items = driver.find_elements(By.CSS_SELECTOR, 
            "[data-testid='search-results'] [data-testid='list-view'] > div"
        )
        print(f"Debug: Found {len(items)} potential Walmart items")

        products = []
        for item in items:
            try:
                # Multiple selectors for title
                title_selectors = [
                    "span[data-automation-id='product-title']",
                    "a[data-automation-id='product-title']",
                    "a span.w_U"
                ]
                title = None
                for selector in title_selectors:
                    try:
                        title = item.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if title: break
                    except: continue

                # Multiple selectors for current price
                price_selectors = [
                    "span.w_V",
                    "span[data-automation-id='product-price']",
                    "div[data-automation-id='product-price'] span"
                ]
                current_price = None
                for selector in price_selectors:
                    try:
                        price_text = item.find_element(By.CSS_SELECTOR, selector).text
                        if '$' in price_text:
                            current_price = float(price_text.replace('$', '').replace(',', '').replace('Now', '').strip())
                            break
                    except: continue

                if not (title and current_price):
                    continue

                # Look for any indication of a deal
                original_price = current_price
                discount = 0.0

                # Check crossed out prices
                try:
                    was_selectors = [
                        "span.w_X",
                        "*[data-automation-id='strikethrough-price']",
                        "div[class*='strike-through']",
                        "span[class*='line-through']"
                    ]
                    for selector in was_selectors:
                        was_elem = item.find_element(By.CSS_SELECTOR, selector)
                        was_text = was_elem.text.strip()
                        if '$' in was_text:
                            was_price = float(was_text.replace('$', '').replace(',', '').strip())
                            if was_price > current_price:
                                original_price = was_price
                                discount = ((original_price - current_price) / original_price) * 100
                                break
                except: pass

                # Check for deal badges if no discount found
                if discount == 0:
                    badge_selectors = [
                        "span[class*='badge']",
                        "div[class*='discount']",
                        "span[class*='deal']",
                        "div[class*='save']"
                    ]
                    for selector in badge_selectors:
                        try:
                            badge = item.find_element(By.CSS_SELECTOR, selector)
                            if any(word in badge.text.lower() for word in ['deal', 'save', 'off', '%', 'reduced']):
                                discount = 0.1  # Minimal discount to include item
                                break
                        except: continue

                link = item.find_element(By.CSS_SELECTOR, "a[link-identifier='linkTest']").get_attribute("href")

                # Include items with any indication of discount
                if discount > 0 or "rollback" in title.lower() or "clearance" in title.lower():
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Walmart: {str(e)}")
        return []

def search_bestbuy(query, driver):
    try:
        url = f"https://www.bestbuy.com/site/searchpage.jsp?st={query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".sku-item-list"))
        )
        
        products = []
        items = driver.find_elements(By.CSS_SELECTOR, ".sku-item")
        
        for item in items:
            try:
                title_elem = item.find_element(By.CSS_SELECTOR, ".sku-title a")
                title = title_elem.get_attribute('title') or title_elem.text.strip()
                current_price = float(item.find_element(By.CSS_SELECTOR, ".priceView-customer-price span").text.replace('$', '').replace(',', ''))
                link = item.find_element(By.CSS_SELECTOR, ".sku-title a").get_attribute("href")
                
                # Get original price if available
                original_price = current_price
                discount = 0.0
                try:
                    was_price = item.find_element(By.CSS_SELECTOR, ".pricing-price__regular-price").text
                    original_price = float(was_price.replace('Was $', '').replace(',', ''))
                    if original_price > current_price:
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass
                
                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })
            except: continue
            
        return sorted(products, key=lambda x: x["discount"], reverse=True)
    except Exception as e:
        print(f"Error searching Best Buy: {str(e)}")
        return []

def search_target(query, driver):
    try:
        url = f"https://www.target.com/s?searchTerm={query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        # Updated wait and selectors
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='product-grid']"))
        )

        # Scroll to load more items
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        items = driver.find_elements(By.CSS_SELECTOR, "[data-test='product-grid'] > div")
        print(f"Debug: Found {len(items)} Target items")

        products = []
        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "[data-test='product-title']").text.strip()
                
                # Multiple price selectors
                price_selectors = [
                    "[data-test='product-price']",
                    "span[data-test='current-price']",
                    ".styles__CurrentPriceWrapper-sc"
                ]
                current_price = None
                for selector in price_selectors:
                    try:
                        price_text = item.find_element(By.CSS_SELECTOR, selector).text
                        if '$' in price_text:
                            current_price = float(price_text.replace('$', '').replace(',', '').split('-')[0].strip())
                            break
                    except: continue

                if not current_price:
                    continue

                # Check multiple indicators for deals
                original_price = current_price
                discount = 0.0

                # Check regular price
                try:
                    reg_selectors = [
                        "[data-test='product-regular-price']",
                        "span[data-test='previous-price']",
                        ".styles__ComparisonPriceWrapper-sc"
                    ]
                    for selector in reg_selectors:
                        reg_elem = item.find_element(By.CSS_SELECTOR, selector)
                        reg_text = reg_elem.text.replace('Reg', '').replace('reg.', '').strip()
                        if '$' in reg_text:
                            orig_price = float(reg_text.replace('$', '').replace(',', '').strip())
                            if orig_price > current_price:
                                original_price = orig_price
                                discount = ((original_price - current_price) / original_price) * 100
                                break
                except: pass

                # Check for deal badges
                if discount == 0:
                    try:
                        badge_selectors = [
                            "[data-test='product-badge']",
                            ".styles__BadgeWrapper-sc",
                            "span[class*='deal']"
                        ]
                        for selector in badge_selectors:
                            badge = item.find_element(By.CSS_SELECTOR, selector)
                            if any(word in badge.text.lower() for word in ['sale', 'deal', 'save', 'off', '%']):
                                discount = 0.1
                                break
                    except: pass

                link = item.find_element(By.CSS_SELECTOR, "a[data-test='product-title']").get_attribute("href")

                if discount > 0 or "clearance" in title.lower() or "sale" in title.lower():
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Target: {str(e)}")
        return []

def search_macys(query, driver):
    try:
        url = f"https://www.macys.com/shop/featured/{query.replace(' ', '-')}"
        print(f"Debug: Accessing Macy's URL - {url}")
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        # Accept cookies if present
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
        except: pass

        # Updated wait and selectors
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".productThumbnail"))
        )

        items = driver.find_elements(By.CSS_SELECTOR, ".productThumbnail")
        products = []

        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "div.productDescription").text.strip()
                
                price_text = item.find_element(By.CSS_SELECTOR, ".prices span.price").text
                current_price = float(price_text.replace('$', '').replace(',', '').strip())
                
                original_price = current_price
                discount = 0.0
                try:
                    orig_elem = item.find_element(By.CSS_SELECTOR, ".prices .original")
                    orig_price = float(orig_elem.text.replace('$', '').replace(',', '').strip())
                    if orig_price > current_price:
                        original_price = orig_price
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass

                link = item.find_element(By.CSS_SELECTOR, "a.productDescLink").get_attribute("href")

                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Error searching Macy's: {str(e)}")
        return []

def search_oldnavy(query, driver):
    try:
        url = f"https://oldnavy.gap.com/browse/search.do?searchText={query.replace(' ', '+')}"
        print(f"Debug: Accessing Old Navy URL - {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Updated selectors for product grid
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, ".product-card")

        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, ".product-card__name").text.strip()
                
                price_elem = item.find_element(By.CSS_SELECTOR, ".product-price__highlight")
                current_price = float(price_elem.text.replace('$', '').replace(',', '').strip())
                
                original_price = current_price
                discount = 0.0
                
                try:
                    orig_price_elem = item.find_element(By.CSS_SELECTOR, ".product-price__was")
                    orig_price = float(orig_price_elem.text.replace('Was $', '').replace(',', '').strip())
                    if orig_price > current_price:
                        original_price = orig_price
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass

                link = item.find_element(By.CSS_SELECTOR, ".product-card__link").get_attribute("href")

                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                print(f"Debug: Error processing Old Navy item - {str(e)}")
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Debug: Major error in Old Navy search - {str(e)}")
        return []

def search_hm(query, driver):
    try:
        url = f"https://www2.hm.com/en_us/search-results.html?q={query.replace(' ', '+')}"
        print(f"Debug: Accessing H&M URL - {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Updated selectors for product grid
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-results-items"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, "div.search-results-items > div.item")

        print(f"Debug: Found {len(items)} H&M items")

        for item in items:
            try:
                # Get title
                title = item.find_element(By.CSS_SELECTOR, ".item-heading a").text.strip()

                # Get current price
                price_elem = item.find_element(By.CSS_SELECTOR, ".item-price .price")
                current_price = float(price_elem.text.replace('$', '').replace(',', '').strip())

                # Check for sale price
                original_price = current_price
                discount = 0.0
                try:
                    orig_price_elem = item.find_element(By.CSS_SELECTOR, ".item-price .price-regular")
                    if orig_price_elem:
                        orig_price = float(orig_price_elem.text.replace('$', '').replace(',', '').strip())
                        if orig_price > current_price:
                            original_price = orig_price
                            discount = ((original_price - current_price) / original_price) * 100
                except: pass

                # Get link
                link = item.find_element(By.CSS_SELECTOR, ".item-heading a").get_attribute("href")

                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                print(f"Debug: Error processing H&M item - {str(e)}")
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Debug: Major error in H&M search - {str(e)}")
        return []

def search_forever21(query, driver):
    try:
        url = f"https://www.forever21.com/us/search?q={query.replace(' ', '+')}&lang=en_US"
        print(f"Debug: Accessing Forever 21 URL - {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Updated selectors for product grid
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-grid']"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='product-grid'] > div")

        print(f"Debug: Found {len(items)} Forever 21 items")

        for item in items:
            try:
                # Updated selectors for title and price
                title = item.find_element(By.CSS_SELECTOR, "[data-testid='product-title']").text.strip()
                
                price_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='product-price-sale'], [data-testid='product-price']")
                current_price = float(price_elem.text.replace('$', '').replace(',', '').strip())
                
                original_price = current_price
                discount = 0.0
                
                try:
                    orig_price_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='product-price-original']")
                    orig_price = float(orig_price_elem.text.replace('$', '').replace(',', '').strip())
                    if orig_price > current_price:
                        original_price = orig_price
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass

                link = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")

                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                print(f"Debug: Error processing Forever 21 item - {str(e)}")
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Debug: Major error in Forever 21 search - {str(e)}")
        return []

def search_zara(query, driver):
    try:
        url = f"https://www.zara.com/us/en/search?searchTerm={query.replace(' ', '+')}&section=MAN"
        print(f"Debug: Accessing Zara URL - {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Updated selectors for product grid
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results"))
        )

        products = []
        items = driver.find_elements(By.CSS_SELECTOR, ".search-results .product")

        print(f"Debug: Found {len(items)} Zara items")

        for item in items:
            try:
                # Updated selectors for title and price
                title = item.find_element(By.CSS_SELECTOR, ".product-name").text.strip()
                
                price_elem = item.find_element(By.CSS_SELECTOR, ".price-current")
                current_price = float(price_elem.text.replace('$', '').replace(',', '').strip())
                
                original_price = current_price
                discount = 0.0
                
                try:
                    orig_price_elem = item.find_element(By.CSS_SELECTOR, ".price-original")
                    orig_price = float(orig_price_elem.text.replace('$', '').replace(',', '').strip())
                    if orig_price > current_price:
                        original_price = orig_price
                        discount = ((original_price - current_price) / original_price) * 100
                except: pass

                link = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")

                if discount > 0:
                    products.append({
                        "title": title,
                        "price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "link": link
                    })

            except Exception as e:
                continue

        return sorted(products, key=lambda x: x["discount"], reverse=True)

    except Exception as e:
        print(f"Debug: Major error in Zara search - {str(e)}")
        return []

def save_to_csv(all_results, query):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"price_comparison_{query}_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Store', 'Title', 'Current Price', 'Original Price', 'Discount %', 'Link'])
        
        for store, results in all_results.items():
            for product in results:
                writer.writerow([
                    store,
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
    all_results = {}
    
    try:
        retailers = {
            'Amazon': search_amazon,
            'Walmart': search_walmart,
            'Best Buy': search_bestbuy,
            'Target': search_target,
            "Macy's": search_macys,
            'Old Navy': search_oldnavy,
            'H&M': search_hm,
            'Forever 21': search_forever21,
            'Zara': search_zara
        }
        
        for store, search_function in retailers.items():
            try:
                print(f"\nSearching {store}...")
                results = search_function(query, driver)
                if results is None:
                    results = []
                all_results[store] = results
                print(f"Found {len(results)} results from {store}")
            except Exception as e:
                print(f"Error while searching {store}: {str(e)}")
                all_results[store] = []
        
        if any(results for results in all_results.values()):
            filename = save_to_csv(all_results, query)
            print(f"\nResults saved to: {filename}")
        else:
            print("\nNo results found to save.")
                    
    finally:
        driver.quit()
