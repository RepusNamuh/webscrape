import requests
from bs4 import BeautifulSoup as bs
import csv
import regex as re
import concurrent.futures
import time
import sys
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Get the directory where the .exe is located
if getattr(sys, 'frozen', False):
    # Running as .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as .py script
    BASE_DIR = Path(__file__).parent

# File paths relative to .exe location
WEBPATH_FILE = BASE_DIR / "webpath2.txt"
FREQUENCY_FILE = BASE_DIR / "frequency.txt"
RESULT_FILE = BASE_DIR / "scraperesult.csv"
FAULTY_FILE = BASE_DIR / "faultypath.txt"

try:
    with open(WEBPATH_FILE, "r") as file:
        webpath = file.readlines()
except FileNotFoundError:
    print(f"File {WEBPATH_FILE} not found. Created an empty file. Please add URLs to scrape." ) 
    with open(WEBPATH_FILE, "w") as file:
        file.write("")

    webpath = []

# Some global constants for scraping
# such as headers, name and price patterns, 
# and return values for not found cases
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36"}
PATTERNS = {
    "bunnings": [
        re.compile(r"MuiTypography-root sc-500f213-2 .* MuiTypography-h1"), 
        "sc-bbcf7fe4-3 kAMCuk"
    ],
    "jbhifi": [
        re.compile(r"_12mtftw9"),  # Name pattern
        "PriceTag_actualWrapperDefault__1eb7mu915"  # Updated price pattern
    ]
}
NOTFOUND = "N/A"

# Function to get the website name from the URL
def get_website_name(url):
    """Extract website name from URL using regex."""
    pattern = r'https?://(?:www\.)?([^.]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else NOTFOUND

def scrape_with_selenium(url, patterns):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')  # Added for better performance
    options.add_argument('--disable-extensions')  # Disable extensions
    options.add_argument('--disable-images')  # Don't load images
    options.add_argument('--enable-unsafe-swiftshader')  # Add SwiftShader support
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)  # Set page load timeout
    NAMEPATTERN, PRICEPATTERN = patterns
    
    try:
        driver.get(url)
        
        # Use explicit wait with timeout
        wait = WebDriverWait(driver, 20)  # 5 second timeout
        
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
            name_text = NOTFOUND
            
        return (name_text, price_text)
        
    except Exception as e:
        return (NOTFOUND, NOTFOUND)
    finally:
        driver.quit()

def scrape_requests(url, patterns):
    
    NAMEPATTERN, PRICEPATTERN = patterns
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)    

        if response.status_code == 200:
            soup = bs(response.content, "html.parser")
            name = soup.find("h1", class_=NAMEPATTERN) # Get the product name
            price = soup.find("p", class_=PRICEPATTERN) # Get the price tag

            name = name.text.strip() if name else NOTFOUND
            price = price.text.strip() if price else NOTFOUND
            
        else:
            name = price = NOTFOUND
        
    except requests.RequestException as e:
        name = price = NOTFOUND

    return (name, price)

def scrape_single_url(url):
    url = url.strip()
    website_name = get_website_name(url)
    patterns = PATTERNS.get(website_name, (NOTFOUND, NOTFOUND))

    try:
        name, price = scrape_requests(url, patterns)
        if name == NOTFOUND or price == NOTFOUND:
            name, price = scrape_with_selenium(url, patterns)
        
        return (url, name, price)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return (url, NOTFOUND, NOTFOUND)

def paralle_scrape(webpath, max_workers=5):

    # I don't really understand how parallel process works
    # so this is just a copy past from the internet
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(scrape_single_url, webpath))

    return results

def read_from_csv(file):
    try:
        with open(file, "r") as csv_file:
            csv_file = csv.reader(csv_file)
            data = {}

            try:
                headers = next(csv_file)  # Read the header line
            except StopIteration:
                # If the file is empty, create headers
                headers = ["Name", "Link", "Lowest Price", "Start Date", "End Date", "Today Price"]
                return headers, data
            
            for line in list(csv_file)[1:]:
                if len(line) == 6:
                    data[line[0]] = {key: value for 
                                    key, value in zip(headers[1:], 
                                                    line[1:])}
        return headers, data
    
    except FileNotFoundError:
        # Create empty CSV with headers
        headers = ["Name", "Link", "Lowest Price", "Start Date", "End Date", "Today Price"]
        with open(file, "w", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)
        return headers, {}

def create_new_item_entry(name, path, price, today_date):
    """Create entry for a new item not in old data."""
    return (name, path, price, today_date, today_date, price)

def create_lower_price_entry(name, path, new_price, today_date):
    """Create entry when new price is lower than old price."""
    return (name, path, new_price, today_date, today_date, new_price)

def create_same_price_entry(name, path, price, old_item, today_date):
    """Create entry when price hasn't changed - extend the date range."""
    return (name, path, price, 
            old_item.get("Start Date", today_date), 
            today_date, 
            price)

def create_higher_price_entry(name, path, old_item, new_price):
    """Create entry when new price is higher - keep old lowest price."""
    old_price = old_item["price"]
    return (name, path, old_price, 
            old_item.get("Start Date", ""), 
            old_item.get("End Date", ""), 
            new_price)

def single_item_comparison(path, name, price, old_scrape, today_date):
    """Process a single scraped item and return the appropriate entry."""
    if name == NOTFOUND or price == NOTFOUND:
        return path
        
    curr_price = float(price.replace("$", ""))
    
    # New item - not in old data
    if name not in old_scrape:
        return create_new_item_entry(name, path, price, today_date)
    
    # Existing item - compare prices
    old_item = old_scrape[name]
    old_price = float(old_item["Lowest Price"].replace("$", ""))
    
    if curr_price < old_price:
        return create_lower_price_entry(name, path, price, today_date)
    elif curr_price == old_price:
        return create_same_price_entry(name, path, price, old_item, today_date)
    else:
        return create_higher_price_entry(name, path, old_item, price)

def compareScrape_new_old(new_scrape, old_scrape):
    """Compare new scrape results with old data and create updated entries.
    
    Args:
        new_scrape: List of (path, name, price) tuples from current scrape
        old_scrape: Dictionary of existing item data
        
    Returns:
        List of processed entries ready for CSV writing
    """
    data = []
    faulty_links = []
    today_date = time.strftime("%d-%m-%Y")
    
    for path, name, price in new_scrape:
        entry = single_item_comparison(path, name, price, old_scrape, today_date)
        if entry == path:
            faulty_links.append(path)
              # Only add valid entries
        elif entry:
            data.append(entry)
            
    return data, faulty_links

def write_to_csv(file, headers, data):
    with open(file, "w") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        for line in data:
            writer.writerow(line)
        
# Setup logging for background execution
def setup_logging():
    log_file = BASE_DIR / "scraper.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
def main():
    try:
        if not webpath:
            logging.warning(f"No URL found in {WEBPATH_FILE}. Please add URLs to scrape.")
            return

        # Get the result for today
        scrape_result = paralle_scrape(webpath, max_workers=5)

        # Read the old scrape result from CSV
        headers, data = read_from_csv(RESULT_FILE)

        new_data, faulty_links = compareScrape_new_old(scrape_result, data)

        write_to_csv(RESULT_FILE, headers, new_data)

        if faulty_links:
            logging.warning("There exist faulty links in the scrape result that doesn't have:\n- a name\n- or price\n- or it simply is a faulty link\n")
            logging.warning(f"All faulty links are printed out and is also in {FAULTY_FILE}\n")
            with open(FAULTY_FILE, "w") as faultypath_file:
                for link in faulty_links:
                    faultypath_file.write(link + "\n")
                    print(f"\t{link}")
    except Exception as e:
        logging.error(f"Scraping error: {e}")
        raise e

if __name__ == "__main__":
    setup_logging()
    if len(sys.argv) == 1 or (sys.argv[1].lower() in ['run', 'manual', 'now']):
        start = time.time()
        main()
        end = time.time()
    
        print(f"Scraping completed in {end - start:.2f} seconds.")
        print(f"Results saved to {RESULT_FILE}")

        input("Press Enter to exit...")

    else:
        # Service mode - just run once and exit
        start = time.time()
        logging.info("Starting scheduled task")
        main()
        end = time.time()
        logging.info(f"Task completed in {end - start:.2f} seconds")