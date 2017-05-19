import requests
import json
import time

from bs4 import BeautifulSoup

page = 'http://fredgibbs.net/courses/digital-methods/schedule.html'


def scrape_readings(page=page):
    """
    Scrapes a list of readings from a page
    """
    data = {}

    r = requests.get(page)

    soup = BeautifulSoup(r.content, 'html.parser')

    print(soup)

if __name__ == "__main__":
    scrape_readings()
