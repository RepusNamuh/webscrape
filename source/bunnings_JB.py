import sys
import regex as re
import time
import logging
from pathlib import Path
from functions.readWrite import FileManipulation
from functions.comparer import ItemCompare
from functions.parser import Parser


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
DEFAULT_WAIT_TIME = 10 # Default wait time for page load

# Some global constants for scraping
# such as headers, name and price patterns, 
# and return values for not found cases
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36"}
PATTERNS = {
    "bunnings": {"TAG_NAME": "h1", "CSS_SELECTOR": "p[data-locator='product-price']"},  # Name pattern
    "jbhifi": 
        {"TAG_NAME": "h1", 
         "CLASS_NAME": "PriceTag_actualWrapperDefault__1eb7mu915"},  # Name pattern

}

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
    manipulator = FileManipulation(WEBPATH_FILE, FAULTY_FILE, RESULT_FILE, DEFAULT_WAIT_TIME)
    webpath, waitime = manipulator.read_weburls()

    try:
        if not webpath:
            logging.warning(f"No URL found in {WEBPATH_FILE}. Please add URLs to scrape.")
            return

        # Get the result for today
        # Passing in the lists of URL,
        # Dict of patterns for name and price of scrapable websites,
        # wait time for page load, and headers for requests
        parser = Parser(webpath, PATTERNS, waitime, HEADERS)
        new_scrape = parser.paralle_scrape()

        # Read the old scrape result from CSV
        old_scrape = manipulator.read_from_csv()

        # Responsible for comparing existing item:
        # if the url (non-faulty) of the item is still in WEBPATH_FILE
        # and the item description cannot be return, 
        # the comparer will return the link that takes a long time
        # and will not change the entry regarding to this
        # Otherwise, update and create all others
        comparer = ItemCompare(new_scrape, old_scrape)
        new_data, faulty_links = comparer.create_update_entries()

        manipulator.write_to_csv(new_data)

        if faulty_links:
            manipulator.record_faulty_links(faulty_links)

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