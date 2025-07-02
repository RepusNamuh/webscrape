from datetime import datetime, timedelta

class ItemCompare:
    def __init__(self, new_scrape, old_scrape):
        self.new_scrape = new_scrape
        self.old_scrape = old_scrape
        self.comparison_result = {}
        self.faulty_links = []
        self.NOTFOUND = "N/A"

    def format_date(self, date_str):
        """Convert date string to datetime object."""
        try:
            return date_str.strftime("%d/%m/%Y")
        except AttributeError:
            return date_str
        
    def _date_comparison(self, new_date, old_date):
        """Check if old_date is yesterday of new_date"""
        true_yesterday = self.format_date(new_date - timedelta(days=1))
        new_date = self.format_date(new_date)

        return (old_date == true_yesterday or old_date == new_date)

    def _date_range(self, start_date, end_date):
        start_date = self.format_date(start_date)
        end_date = self.format_date(end_date)
        
        return f"{start_date}-{end_date}"
    


    def create_new_price_entry(self, name, path, price, today_date):
        """Create entry for a new item not in old data."""
        new_range = self._date_range(today_date, today_date)

        return (name, path, price, new_range, price)

    def create_same_price_entry(self, name, path, price, old_item, today_date):
        """Create entry when price hasn't changed - extend the date range."""

        old_range = old_item["Lowest Price Dates"].split(";")
        start_date, end_date = old_range.pop().split("-")
        nextday = self._date_comparison(today_date, end_date)

        if nextday:
            latest_range = self._date_range(start_date, today_date)

        else:
            previous_range = self._date_range(start_date, end_date)
            latest_range = self._date_range(today_date, today_date)
            latest_range = f"{previous_range};{latest_range}"

        new_range = ";".join(old_range + [latest_range])

        return (name, path, price, new_range, price)

    def create_higher_price_entry(self, name, path, old_item, new_price):
        """Create entry when new price is higher - keep old lowest price."""
        old_price = old_item["price"]

        return (name, path, old_price, old_item["Lowest Price Dates"], new_price)


    def single_item_comparison(self, path, name, price, old_scrape, today_date):
        """Process a single scraped item and return the appropriate entry."""
        if name == self.NOTFOUND or price == self.NOTFOUND:
            return path
            
        curr_price = float(price.replace("$", ""))
        
        # New item - not in old data
        if path not in old_scrape:
            return self.create_new_price_entry(name, path, price, today_date)
        
        # Existing item - compare prices
        old_item = old_scrape[path]
        old_price = float(old_item["Lowest Price"].replace("$", ""))
        
        if curr_price < old_price:
            return self.create_new_price_entry(name, path, price, today_date)
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
        today_date = datetime.now()
        
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
                                  old_item["Lowest Price Dates"], 
                                  price))
                
            elif entry:
                data.append(entry)
                
        return data, faulty_links