import logging
import csv

class FileManipulation():
    def __init__(self, webpath, faultypath, outfile, waitime):
        self.webpath = webpath
        self.faultypath = faultypath
        self.outfile = outfile
        self.waitime = waitime
        self.headers = ["Name", "Link", "Lowest Price", 
                        "Lowest Price Dates", "Today Price"]

    def read_weburls(self):
        """Read URLs from a file and return them as a list."""
        webpaths = []
        try:
            with open(self.webpath, "r") as file:
                webpaths = file.readlines()
                try:
                    self.waitime = int(webpaths[0].strip())
                    webpaths = webpaths[1:]

                except ValueError:
                    logging.warning(f"Invalid wait time in {self.webpath}. Using default wait time of {self.waitime} seconds.")

                except IndexError:
                    logging.warning(f"No URLs found in {self.webpath}")
                    webpaths = []
                
        except FileNotFoundError:
            print(f"File {self.webpath} not found. Created an empty file. Please add URLs to scrape.")
            with open(self.webpath, "w") as file:
                file.write(f"{self.waitime}\n")
        
        finally:
            return webpaths, self.waitime
        
    def read_from_csv(self):
        try:
            with open(self.outfile, "r") as csv_file:
                csv_file = csv.reader(csv_file)
                data = {}

                try:
                    next(csv_file)  # Read the header line
                except StopIteration:
                    # If the file is empty
                    return data
                
                for line in list(csv_file)[1:]:
                    if len(line) == 5:
                        data[line[1]] = {key: value for 
                                        key, value in zip(self.headers, 
                                                        line)}
            return data
    
        except FileNotFoundError:
            # Create empty CSV with headers
            with open(self.outfile, "w", newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.headers)
            return {}
        
    def write_to_csv(self, data):
        with open(self.outfile, "w") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(self.headers)
            for line in data:
                writer.writerow(line)
    
    def record_faulty_links(self, faulty_links):
        logging.warning("There exist faulty links in the scrape result that doesn't have:\n- a name\n- or price\n- or it simply is a faulty link\n")
        logging.warning(f"All faulty links are printed out and is also in {self.faultypath}\n")

        with open(self.faultypath, "w") as faultypath_file:
            for link in faulty_links:
                faultypath_file.write(link + "\n")
                print(f"\t{link}")