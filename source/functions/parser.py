import requests, regex as re
from bs4 import BeautifulSoup as bs
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging

class Parser:
    def __init__(self, urls, PATTERNS, wait_time, HEADERS):
        self.urls = urls
        self.PATTERNS = PATTERNS
        self.wait_time = wait_time
        self.HEADERS = HEADERS
        self.max_workers = 5
        self.NOTFOUND = "N/A"
    
    def get_website_name(self, url):
        """Extract website name from URL using regex."""
        pattern = r'https?://(?:www\.)?([^.]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else self.NOTFOUND
    
    def _scrape_with_selenium(self, url, patterns):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')  # Added for better performance
        options.add_argument('--disable-extensions')  # Disable extensions
        options.add_argument('--disable-images')  # Don't load images
        options.add_argument('--enable-unsafe-swiftshader')  # Add SwiftShader support
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.wait_time)  # Set page load timeout
        NAMEPATTERN, PRICEPATTERN = patterns

        
        try:
            driver.get(url)
            
            # Use explicit wait with timeout
            wait = WebDriverWait(driver, self.wait_time)  
            
            # Wait for price element with explicit condition
            price_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, PRICEPATTERN))
            )
            price_text = "".join(price_element.text.split())
            
            # Get product name with explicit wait
            try:
                name_element = wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, 'h1'))
                )
                name_text = name_element.text
            except:
                name_text = self.NOTFOUND
                
            return (name_text, price_text)
            
        except Exception as e:
            logging.warning(f"Loading time out for {url} at {self.wait_time} seconds.")
            return (self.NOTFOUND, self.NOTFOUND)
        finally:
            driver.quit()

    def _scrape_requests(self, url, patterns):
        
        NAMEPATTERN, PRICEPATTERN = patterns
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)    

            if response.status_code == 200:
                soup = bs(response.content, "html.parser")
                name = soup.find("h1", class_=NAMEPATTERN) # Get the product name
                price = soup.find("p", class_=PRICEPATTERN) # Get the price tag

                name = name.text.strip() if name else self.NOTFOUND
                price = price.text.strip() if price else self.NOTFOUND
                
            else:
                name = price = self.NOTFOUND
            
        except requests.RequestException as e:
            name = price = self.NOTFOUND

        return (name, price)

    def scrape_single_url(self, url):
        url = url.strip()
        website_name = self.get_website_name(url)
        patterns = self.PATTERNS.get(website_name, (self.NOTFOUND, self.NOTFOUND))

        try:
            name, price = self._scrape_requests(url, patterns)
            if name == self.NOTFOUND or price == self.NOTFOUND:
                name, price = self._scrape_with_selenium(url, patterns)
            
            return (url, name, price)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return (url, self.NOTFOUND, self.NOTFOUND)

    def paralle_scrape(self):

        # I don't really understand how parallel process works
        # so this is just a copy past from the internet
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.scrape_single_url, self.urls))

        return results 