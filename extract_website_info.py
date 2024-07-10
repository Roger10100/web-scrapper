import requests
from bs4 import BeautifulSoup
import re
import tldextract
import mysql.connector
from mysql.connector import errorcode

# List of websites to scrape
websites = [
    "https://en.wikipedia.org/wiki/Web_scraping",
    "https://www.amazon.com/"
    # Add more websites as needed
]

# Database connection setup
def connect_to_db():
    try:
        conn = mysql.connector.connect(
            user='root',
            password='ojas@2025',
            host='localhost',
            database='website_info_db'
        )
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

def store_info_to_db(conn, info):
    cursor = conn.cursor()
    max_address_length = 65535  # Maximum length for TEXT type in MySQL
    max_contact_number_length = 50  # Assuming VARCHAR(50) for contact_number

    # Ensure contact_address is not too long for the column
    if info['contact_address']:
        info['contact_address'] = info['contact_address'][:max_address_length]
    # Ensure contact_number is not too long for the column and remove newlines
    if info['contact_number']:
        info['contact_number'] = info['contact_number'].replace('\n', '').strip()[:max_contact_number_length]

    add_website_info = ("INSERT INTO website_info "
                        "(url, robots_txt_url, sitemap_url, contact_email, contact_address, contact_number, language, cms, category) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
    data_website_info = (info['url'], info['robots_txt_url'], info['sitemap_url'], info['contact_email'], info['contact_address'], 
                         info['contact_number'], info['language'], info['cms'], info['category'])
    cursor.execute(add_website_info, data_website_info)
    conn.commit()
    cursor.close()

def extract_info(url):
    info = {
        "url": url,
        "robots_txt_url": None,
        "sitemap_url": None,
        "contact_email": None,
        "contact_address": None,
        "contact_number": None,
        "language": None,
        "cms": None,
        "category": None
    }

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract robots.txt URL
        parsed_url = tldextract.extract(url)
        base_url = f"https://{parsed_url.registered_domain}"
        info["robots_txt_url"] = f"{base_url}/robots.txt"
        
        # Extract language
        html_tag = soup.find('html')
        if html_tag and html_tag.has_attr('lang'):
            info["language"] = html_tag['lang']
        
        # Extract CMS
        cms_meta = soup.find('meta', attrs={'name': 'generator'})
        if cms_meta:
            info["cms"] = cms_meta['content']

        # Extract contact info (email, phone, address)
        # Search for email in mailto: links
        email_links = soup.find_all('a', href=re.compile(r'mailto:'))
        if email_links:
            info["contact_email"] = email_links[0]['href'].replace('mailto:', '')

        # Look for phone numbers in specific elements
        contact_elements = soup.find_all(['address', 'footer', 'p', 'div'])
        for element in contact_elements:
            phones = re.findall(r'\+?\d{1,2}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', element.get_text())
            if phones:
                info["contact_number"] = phones[0]
                break
        
        # Sitemap extraction from robots.txt
        robots_txt_url = info["robots_txt_url"]
        robots_response = requests.get(robots_txt_url, timeout=10)
        if robots_response.status_code == 200:
            sitemap_match = re.search(r'Sitemap:\s*(http?://[^\s]+)', robots_response.text, re.I)
            if sitemap_match:
                info["sitemap_url"] = sitemap_match.group(1)

        # Extract category based on keywords in meta tags or specific patterns (simplistic example)
        category_meta = soup.find('meta', attrs={'name': 'keywords'})
        if category_meta:
            info["category"] = category_meta['content'].split(',')[0]  # Taking the first keyword as category
        
    except Exception as e:
        print(f"Error processing {url}: {e}")

    return info

# Main function to extract info from all websites and store in DB
def main():
    conn = connect_to_db()
    if not conn:
        print("Failed to connect to the database.")
        return
    
    for site in websites:
        site_info = extract_info(site)
        store_info_to_db(conn, site_info)
        print(site_info)  # Print or save the extracted information

    conn.close()

if __name__ == "__main__":
    main()
