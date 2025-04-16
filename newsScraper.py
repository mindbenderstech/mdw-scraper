import psycopg2
import os
import uuid
import requests
from bs4 import BeautifulSoup
import datetime

IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def fetch_robots_txt(url):
    url = url.rstrip('/') + '/robots.txt' if not url.endswith('/robots.txt') else url
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"\nrobots.txt content from {url}:\n{response.text}")
            sitemap_url = next((line.split(":", 1)[1].strip() for line in response.text.splitlines() if line.lower().startswith('sitemap:')), None)
            if sitemap_url:
                print(f"\nVisiting sitemap: {sitemap_url}")
                fetch_sitemap_urls(sitemap_url)
            else:
                print("No sitemap found.")
        else:
            print(f"Failed to fetch robots.txt: {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

def fetch_sitemap_urls(sitemap_url):
    try:
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.get_text() for loc in soup.find_all('loc')]
            lastmods = [lastmod.get_text() for lastmod in soup.find_all('lastmod')]

            if urls:
                print(f"Found URLs in sitemap {sitemap_url}:")

                # Print every URL and its corresponding lastmod date
                for i in range(len(urls)):
                    print(f"URL: {urls[i]}, Lastmod: {lastmods[i]}")

                # Pass required urls
                if len(urls) >= 2 and len(lastmods) >= 2:
                    fetch_and_extract_loc_from_xml(urls[0],lastmods[0])
                    fetch_and_extract_loc_from_xml(urls[1], lastmods[1])
                else:
                    print("Not enough URLs to pass.")
            else:
                print("No <loc> tags found.")
        else:
            print(f"Failed to fetch sitemap: {response.status_code}")
    except Exception as e:
        print(f"Error fetching sitemap {sitemap_url}: {e}")


def fetch_and_extract_loc_from_xml(xml_url,lastmod):
    try:
        response = requests.get(xml_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            loc_tags = soup.find_all('loc')
            date_and_time = [lastmod.get_text() for lastmod in soup.find_all('lastmod')]
            print(f"\nVisiting requested xml {xml_url}")

            # Process up to 2 URLs (or more if desired) from loc_tags
            for i, loc_tag in enumerate(loc_tags[:2]):  # Adjust the slice to fetch more URLs if needed
                if i < len(date_and_time):
                    print(f"\nFound article URL {i + 1}: {loc_tag.get_text()}")
                    print(f"Article Date and Time: {date_and_time[i]}")

                    converted_article_datetime = datetime.datetime.fromisoformat(date_and_time[i])
                extract_content_from_article(loc_tag.get_text(), lastmod, converted_article_datetime)

            if not loc_tags:
                print("No <loc> tags found.")
        else:
            print(f"Failed to fetch XML: {response.status_code}")
    except Exception as e:
        print(f"Error fetching XML file {xml_url}: {e}")

def extract_content_from_article(url,lastmod ,article_datetime):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = extract_and_print_content(soup, 'h1', 'abp-article-title', return_content=True)
            slug = extract_and_print_content(soup, 'h2', 'abp-article-slug', return_content=True)
            image_url = extract_image_src(soup)
            byline_author = extract_and_print_content(soup, 'div', 'abp-article-byline-author', return_content=True)
            article_detail = extract_and_print_content(soup, 'div', 'abp-story-detail', return_content=True, exclude_class=['readMore', 'twitter-tweet','abp-crick-wrap'])

            if all([title, slug, image_url, byline_author, article_detail]):
                store_article_data(url, title, slug, image_url, byline_author, article_detail, lastmod, article_datetime)
            else:
                print(f"Missing required fields for article: {url}. Skipping.")
        else:
            print(f"Failed to fetch content from {url}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")

def extract_and_print_content(soup, tag, class_name, return_content=False, exclude_class=None):
    content = soup.find_all(tag, class_=class_name)
    if content:
        result = ''
        for item in content:
            if exclude_class:
                for class_to_exclude in exclude_class:
                    for element in item.find_all(class_=class_to_exclude):
                        element.decompose()
            result += item.get_text() + " "
        result = result.strip()
        if return_content:
            return result
        print(f"\n{class_name}: {result}")
    else:
        print(f"No {class_name} found.")
        return None

def extract_image_src(soup):
    lead_image_div = soup.find('div', class_='lead-image')
    if lead_image_div:
        img_tag = lead_image_div.find('img')
        if img_tag and img_tag.get('src'):
            print(f"Image src: {img_tag['src']}")
            return img_tag['src']
    print("No image found.")
    return None

def store_article_data(news_source_url, title, slug, image_url, byline_author, article_detail, lastmod, article_datetime):
    try:
        # Get today's date in DD-MM-YY format
        today_date = datetime.datetime.today().strftime('%Y-%m-%d')
        # Define the path for the daily image folder
        daily_image_dir = os.path.join(IMAGE_DIR, today_date)

        # Check if the directory for today's date exists, if not, create it
        if not os.path.exists(daily_image_dir):
            print(f"Creating folder for today's date: {daily_image_dir}")
            os.makedirs(daily_image_dir, exist_ok=True)
        else:
            print(f"Using existing folder for today's date: {daily_image_dir}")

        with psycopg2.connect(dbname="news_db", user="postgres", password="1234", host="localhost", port="5432") as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM news_articles WHERE news_source_url = %s;", (news_source_url,))
                if cursor.fetchone():
                    print(f"Article already exists: {news_source_url}")
                else:
                    local_image_path = None
                    if image_url:
                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            # Get the image extension and file name
                            extension = os.path.splitext(image_url)[1].split("?")[0] or '.jpg'
                            filename = f"{uuid.uuid4().hex}{extension}"
                            # Define the local image path inside the date-based folder
                            local_image_path = os.path.join(daily_image_dir, filename)
                            # Save the image
                            with open(local_image_path, 'wb') as f:
                                f.write(image_response.content)
                            print(f"Image saved: {local_image_path}")
                    # Insert article data into the database, including the local image path
                    cursor.execute(""" 
                        INSERT INTO news_articles (news_source_url, title, slug, image_path, byline_author, article_detail, article_date, article_date_and_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """, (news_source_url, title, slug, local_image_path, byline_author, article_detail, lastmod, article_datetime))
                    conn.commit()
                    print("Article stored.")
    except Exception as error:
        print(f"Error storing article: {error}")

# Function to reset sequence if table is empty
def reset_sequence_if_empty():
    try:
        # Connect to PostgreSQL
        with psycopg2.connect(dbname="news_db", user="postgres", password="1234", host="localhost",
                              port="5432") as conn:
            with conn.cursor() as cursor:
                # Check if the table is empty
                cursor.execute("SELECT COUNT(*) FROM news_articles;")
                row_count = cursor.fetchone()[0]

                if row_count == 0:
                    print("Table is empty. Resetting ID sequence.")
                    # Reset the sequence to 1 if table is empty
                    cursor.execute("SELECT setval(pg_get_serial_sequence('news_articles', 'id'), 1, false);")
                    conn.commit()
                    print("ID sequence reset to 1.")
                else:
                    print("Table is not empty. No action needed.")
    except Exception as e:
        print(f"Error: {e}")

# Call the function to check and reset the sequence if necessary
reset_sequence_if_empty()

# Start process
urls = ["https://marathi.abplive.com"]
for url in urls:
    fetch_robots_txt(url)
