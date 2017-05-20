import requests
import json
# import base64
# import re
# import time

# from urllib.parse import urlparse
# from urllib.parse import quote

from bs4 import BeautifulSoup
from goldfinch import validFileName as vfn

# directory to store data
data_dir = 'data'
# page to scrape
page_url = 'http://fredgibbs.net/courses/digital-methods/schedule.html'
# filenames for local copy of scraped page and list of links
scraped_page = 'readings_page.html'
links_file = 'links_list.json'
readings_html_dir = 'readings/html'


def scrape_course(page=page_url):
    """
    Scrapes a list of readings from a page
    """

    data = {}

    r = requests.get(page)

    print('Scraping %s' % page)

    # Make a local copy of the page
    with open('%s/%s' % (data_dir, scraped_page), 'w') as htmlfile:
        htmlfile.write(r.text)


def parse_course():
    """
    Parses the list of readings
    """
    # Use the local copy of the page if it exists, otherwise, scrape
    # to get it.
    try:
        with open('%s/%s' % (data_dir, scraped_page), 'r') as htmlfile:
            soup = BeautifulSoup(htmlfile.read(), 'html.parser')
    except FileNotFoundError:
        scrape_course()
        with open('%s/%s' % (data_dir, scraped_page), 'r') as htmlfile:
            soup = BeautifulSoup(htmlfile.read(), 'html.parser')

    # Set the course info, which will apply to all readings.
    # This will be useful if we want to compare to other courses
    # The course name is in an H1 tag, while the info about the
    # course number and term is the next sibling (not in a tag)
    course_info = {}
    course_tag = soup.select_one('#syllabus h1')
    course_info['name'] = course_tag.text.strip()
    course_info['details'] = course_tag.next_sibling.strip()

    # print(course)

    # A list to hold all the links we will find
    links = []

    # Weekly readings are divinded into sections with h2 tags
    # We want to parse each section separately so we can keep track
    # of which section we're in
    sections = soup.select('#syllabus h2')

    for i, section in enumerate(sections):
        # Most of the section titles are formatted like this:
        # 13: DIGITAL LITERACIES/PEDAGOGY
        # But we will skip any that aren't
        if (':' not in section.text):
            continue
        else:
            # Split section headers in case we want to refer to them
            # by name or number
            section_parts = section.text.split(':')
            section_info = {
                'number': section_parts[0].strip(),
                'name': section_parts[1].strip()
            }
            print(section.text)

            # Because the sections are not heirerarchical, we will traverse the
            # tree through the siblings of the section headers (h2 tags).
            # We start by selecting the tag of the current section header,
            # adjusting for the fact that CSS nth selectors start at 1 instead
            # of 0. This is also why we've enumerated the sections
            current_tag = soup.select_one(
                '#syllabus h2:nth-of-type(%s)' % (i + 1))

            # Some of the sections have subsection headers. We might want to
            # use these to differentiate between links later, so we'll update
            # this variable any time we hit a new subsection, but it starts as
            # unset (for links that are directly under the section)
            subsection = ''

            # This starts the sibling tag loop. Note that the loop will
            # terminate when there we run out of siblings (which will happen
            # at the end of the #syllabus div) or when we hit the next h2 tag
            while (
                current_tag.find_next_sibling(True) and
                    current_tag.find_next_sibling(True).name != 'h2'):
                current_tag = current_tag.find_next_sibling(True)

                # Reset the subsection whenever we hit an h3 or h4 tag
                if (current_tag.name == ('h3' or 'h4')):
                    # print('change subsection')
                    subsection = current_tag.text
                    # print(subsection)

                # Find all the links and create a dictionary for each
                for a in current_tag.find_all('a'):
                    link = {}
                    link['url'] = a.get('href')
                    link['text'] = a.text
                    link['course'] = course_info
                    link['section'] = section_info
                    link['subsection'] = subsection
                    # Number the links sequentially
                    link['id'] = len(links) + 1

                    print(link['id'], link['url'])
                    links.append(link)

    # for link in links:
        # print(link['url'])
    # Print summary
    print('\n%s links found for \'%s\'' % (len(links), course_info['name']))

    # Write to json file
    with open('%s/%s' % (data_dir, links_file), 'w') as jsonfile:
        jsonfile.write(json.dumps(links))


def scrape_readings():
    """
    Reads from the list generated by parse_course().
    Grabs a copy of each page.
    Writes it to HTML file in data/readings/html.
    """
    # Use the json list of readings if it exists
    try:
        with open('%s/%s' % (data_dir, links_file), 'r') as jsonfile:
            readings = json.loads(jsonfile.read())
    # otherwise, generate it
    except FileNotFoundError:
        parse_course()
        with open('%s/%s' % (data_dir, links_file), 'r') as jsonfile:
            readings = json.loads(jsonfile.read())

    for reading in readings:
        # For each one, get the inspection detail URL.
        r = requests.get(reading['url'])

        # Use goldfinch to make a valid filename from the URL
        filename = vfn(reading['url'])

        # Make a local copy of the page
        with open('%s/%s/%s' % (
                data_dir, readings_html_dir, filename), 'w') as htmlfile:
            htmlfile.write(r.text)

        # Print something to stdout.
        print('Saved page %s: %s' % (reading['id'], reading['url']))


if __name__ == '__main__':
    scrape_readings()
