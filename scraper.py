import requests
import json

from bs4 import BeautifulSoup
from goldfinch import validFileName as vfn
from newspaper import Article
from boilerpipe.extract import Extractor

# directory to store data
data_dir = 'data'
# page to scrape
page_url = 'http://fredgibbs.net/courses/digital-methods/schedule.html'
# filenames for local copy of scraped page and list of links
scraped_page = 'readings_page.html'
links_file = 'links_list.json'
readings_text_dir = 'readings/text'
readings_html_dir = 'readings/html'
readings_file = 'readings/readings.json'


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
        filename = vfn(reading['url'], initCap=False).decode()

        # Make a local copy of the page
        with open('%s/%s/%s' % (
                data_dir, readings_html_dir, filename), 'w') as htmlfile:
            htmlfile.write(r.text)

        # Print something to stdout.
        print('Saved page %s: %s' % (reading['id'], reading['url']))


def parse_readings():
    """
    Reads from list generated by parse_course().
    Reads each readings page from scrape_readings().
    Parses the HTML.
    Writes to JSON.
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

    # Create lists to hold readings
    reading_list = []
    pdf_list = []
    error_list = []

    for reading in readings:
        # Skip pdf files
        if '.pdf' in reading['url']:
            pdf_list.append(reading)

        else:
            # Container for parsed data
            reading_item = {}

            # Use goldfinch to make a valid filename from the URL
            filename = vfn(reading['url'], initCap=False).decode()

            # Initialize a newspaper article
            # url is  empty because we don't need newspaper to do any scraping
            # but it's a required property
            article = Article(url='')

            # Open the local version of the HTML file
            try:
                with open('%s/%s/%s' % (
                        data_dir, readings_html_dir, filename
                        ), 'r') as htmlfile:
                    # Save both the raw html and add it to the article
                    raw_html = htmlfile.read()
                    article.set_html(raw_html)
            except FileNotFoundError:
                print('Error reading saved html file')

            # Use newspaper to do the parsing
            article.parse()

            reading_item['title'] = article.title
            reading_item['authors'] = article.authors

            # Set iso string version of date if it exists.
            # It needs to be a string because we'll be exporting to JSON
            reading_item['pub_date'] = article.publish_date.isoformat() \
                if article.publish_date else None

            # Usually newspaper's extractor works best
            reading_item['n_text'] = article.text

            # But when it fails, we may want to use boilerpipe extraction as
            # a fallback
            extractor = Extractor(extractor='ArticleExtractor', html=raw_html)
            reading_item['b_text'] = extractor.getText()

            # print('Newspaper words: %s' % len(reading_item['n_text'].split()))
            # print('Boilerpipe words: %s' % len(reading_item['b_text'].split()))

            # if(reading_item['text'] == ''):
            #     extractor = Extractor(extractor='ArticleExtractor', html=raw_html)
            #     reading_item['text'] = extractor.getText()

            # Add the parsed data to our existing reading data
            reading['page'] = reading_item

            # Note failed parses
            if(reading_item['n_text'] == '' and reading_item['b_text'] == ''):
                print('Could not parse text for %s' % reading['url'])
                error_list.append(reading)
            else:
                reading_list.append(reading)

    print('Sucessfully parsed readings: %s' % len(error_list))

    print('Skipped PDF readings: %s' % len(pdf_list))

    print('Articles without parseable text: %s' % len(error_list))

    # print('Articles without authors: %s' % len([
    #     reading for reading in reading_list
    #     if reading['page']['authors'] == []]))

    # print('Articles without dates: %s' % len([
    #     reading for reading in reading_list
    #     if reading['page']['pub_date'] is None]))

    # Write to json file
    with open('%s/%s' % (data_dir, readings_file), 'w') as jsonfile:
        jsonfile.write(json.dumps(reading_list))


def generate_text_files():
    """
    Reads from list generated by parse_readings().
    Exports the text of each reading to standalone text files
    """

    with open('%s/%s' % (data_dir, readings_file), 'r') as jsonfile:
        readings = json.loads(jsonfile.read())

    for reading in readings:
        filename = vfn(reading['url'], initCap=False).decode()

        # Output a directory of text files generated by newspaper
        with open('%s/%s/%s/%s.txt' % (
                data_dir, readings_text_dir, 'newspaper_parse', filename
                ), 'w') as htmlfile:
            htmlfile.write(reading['page']['n_text'])

        # Output a directory of text files generated by boilerpipe
        with open('%s/%s/%s/%s.txt' % (
                data_dir, readings_text_dir, 'boilerpipe_parse', filename
                ), 'w') as htmlfile:
            htmlfile.write(reading['page']['b_text'])


if __name__ == '__main__':
    pass
