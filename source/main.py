import requests
from bs4 import BeautifulSoup as bs
import csv
import regex as re
import concurrent.futures
import time
import schedule
import sys
import logging
from pathlib import Path

# Get the directory where the .exe is located
if getattr(sys, 'frozen', False):
    # Running as .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as .py script
    BASE_DIR = Path(__file__).parent

# File paths relative to .exe location
WEBPATH_FILE = BASE_DIR / "webpath.txt"
FREQUENCY_FILE = BASE_DIR / "frequency.txt"
RESULT_FILE = BASE_DIR / "scraperesult.csv"
FAULTY_FILE = BASE_DIR / "faultypath.txt"

with open(WEBPATH_FILE, "r") as file:
    webpath = file.readlines()

# Some global constants for scraping
# such as headers, name and price patterns, 
# and return values for not found cases
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36"}
NAMEPATTERN = re.compile(r"MuiTypography-root sc-500f213-2 .* MuiTypography-h1")
PRICEPATTERN = "sc-bbcf7fe4-3 kAMCuk"
NOTFOUND = "N/A"

# Get name and price of the product from the given URL
def scrape_single_url(path):
    path = path.strip()
    if not (path.startswith("https://") or path.startswith("http://")):
        return "Error"

    try:
        response = requests.get(path, headers=HEADERS, timeout=10)    

        if response.status_code == 200:
            soup = bs(response.content, "html.parser")
            h1_name = soup.find("h1", class_=NAMEPATTERN) # Get the product name
            price_tag = soup.find("p", class_=PRICEPATTERN) # Get the price tag

            h1_name = h1_name.text.strip() if h1_name else NOTFOUND
            price_tag = price_tag.text.strip() if price_tag else NOTFOUND
            
        else:
            h1_name = price_tag = NOTFOUND
        
    except requests.RequestException as e:
        h1_name = price_tag = NOTFOUND

    return (path, h1_name, price_tag)

# Parallel scraping 
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
            headers = next(csv_file)  # Read the header line
            data = {}
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

def process_single_item(path, name, price, old_scrape, today_date):
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
        entry = process_single_item(path, name, price, old_scrape, today_date)
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
    log_file = Path(__file__).parent / "scraper.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_scheduler():
    """Run scheduler as a background service (no console interaction)"""
    setup_logging()
    logging.info("Starting scraper scheduler service...")
    
    try:
        with open("frequency.txt", "r") as file:
            frequency = int(file.readline().strip())
            time_of_day = file.readline().strip()
    except FileNotFoundError:
        logging.info("frequency.txt not found. Creating default schedule")
        with open("frequency.txt", "w") as file:
            file.write("1\n00:00")
        frequency = 1
        time_of_day = "00:00"

    schedule.every(frequency).days.at(time_of_day).do(main)
    logging.info(f"Scheduled to run every {frequency} day(s) at {time_of_day}")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except Exception as e:
        logging.error(f"Scheduler error: {e}")
    
def main():
    setup_logging()
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
            print("There exist faulty links in the scrape result that doesn't have:\n- a name\n- or price\n- or it simply is a faulty link\n")
            print(f"All faulty links are printed out and is also in {FAULTY_FILE}\n")
            with open(FAULTY_FILE, "w") as faultypath_file:
                for link in faulty_links:
                    faultypath_file.write(link + "\n")
                    print(f"\t{link}")
    except Exception as e:
        logging.error(f"Scraping error: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) == 1 or (sys.argv[1].lower() in ['run', 'manual', 'now']):
        start = time.time()
        main()
        end = time.time()
    
        print(f"Scraping completed in {end - start:.2f} seconds.")
        print(f"Results saved to {RESULT_FILE}")

        input("Press Enter to exit...")

    else:
        try:
            run_scheduler()  # Background service mode
        except KeyboardInterrupt:
            sys.exit()