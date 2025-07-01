import time

class ItemCompare:
    def __init__(self, new_scrape, old_scrape):
        self.new_scrape = new_scrape
        self.old_scrape = old_scrape
        self.comparison_result = {}
        self.faulty_links = []
        self.NOTFOUND = "N/A"
    
    def create_new_item_entry(self, name, path, price, today_date):
        """Create entry for a new item not in old data."""
        return (name, path, price, today_date, today_date, price)

    def create_lower_price_entry(self, name, path, new_price, today_date):
        """Create entry when new price is lower than old price."""
        return (name, path, new_price, today_date, today_date, new_price)

    def create_same_price_entry(self, name, path, price, old_item, today_date):
        """Create entry when price hasn't changed - extend the date range."""
        return (name, path, price, 
                old_item.get("Start Date", today_date), 
                today_date, 
                price)

    def create_higher_price_entry(self, name, path, old_item, new_price):
        """Create entry when new price is higher - keep old lowest price."""
        old_price = old_item["price"]
        return (name, path, old_price, 
                old_item.get("Start Date", ""), 
                old_item.get("End Date", ""), 
                new_price)

    def single_item_comparison(self, path, name, price, old_scrape, today_date):
        """Process a single scraped item and return the appropriate entry."""
        if name == self.NOTFOUND or price == self.NOTFOUND:
            return path
            
        curr_price = float(price.replace("$", ""))
        
        # New item - not in old data
        if path not in old_scrape:
            return self.create_new_item_entry(name, path, price, today_date)
        
        # Existing item - compare prices
        old_item = old_scrape[path]
        old_price = float(old_item["Lowest Price"].replace("$", ""))
        
        if curr_price < old_price:
            return self.create_lower_price_entry(name, path, price, today_date)
        elif curr_price == old_price:
            return self.create_same_price_entry(name, path, price, old_item, today_date)
        else:
            return self.create_higher_price_entry(name, path, old_item, price)
        
    def create_update_entries(self):
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
        
        for path, name, price in self.new_scrape:
            entry = self.single_item_comparison(path, name, price, self.old_scrape, today_date)
            if entry == path:
                faulty_links.append(path)
                if path in self.old_scrape:
                    # If the path is faulty but exists in old data, keep the old entry
                    # except for the column of "Today Price"
                    old_item = self.old_scrape[path]
                    print(old_item)
                    data.append((old_item["Name"], path, old_item["Lowest Price"], 
                                  old_item["Start Date"], 
                                  old_item["End Date"], 
                                  price))
                
            elif entry:
                data.append(entry)
                
        return data, faulty_links