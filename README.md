# Purpose
    This is a program to scrape product price from a website called bunnings warehouse

# Caution.
    This is the first time I make a window application as well as first time webscraping, therefor, use at your own discreation.

    Obviously, the program failure to run will not in any capacity affect your system.

# When using
    Every new scrape, whether schedule run or manual run will completely erase previous entry in the CSV files. So if you want to keep a particular item, it would be best if you don't delete the URL inside webpath.txt.

    Only delete it if you no longer care about the item.

# First Run
    When first runnning the program, if you want to allow the application to auto run, run the script install_service.bat as administrator

# Using the program.
    You can manualy use the program by click BunningsScraper.exe or runonce.bat
    The only pre-setup you might want to do is to go to your webpath2 for bunningsJB.exe
    and at the first line, set a numbers from 0-infinity, what ever it maybe, but
    it must be a positive integer.
    The number is responsible for settings the waiting time for a website to load.
    If your internet is slow and you set it to 2 for example, you will be unable to
    scrape the data off the website. So you can increase it until to feel comfortable
    Or, you can get faster internet.

# What is Changable in the .txt and .csv files.
You can change Whatever you want, just not the .csv files,

## frequency.txt
For frequency, the first number is the date interval you want the program to automatically run at,
while the second number is the hour in the format from 00:00 to 23:59
## faultypath.txt and webpath2.txt
You can do whatever you want with the former, while for the latter, you can change wait tolerance for
url retrieval, whatever url you want beside that (invalid url will not return results)
## scraperesult.csv
DO NOT CHANGE ANYTHING ON THIS FILE,