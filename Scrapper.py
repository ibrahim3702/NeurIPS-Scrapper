import os
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://papers.nips.cc"
OUTPUT_DIR = r"D:\scrapped-pdf"
MAX_RETRIES = 3  
TIMEOUT = 60  
PROCESS_THREADS = 20 
DOWNLOAD_THREADS = 20


os.makedirs(OUTPUT_DIR, exist_ok=True)

session = requests.Session()
retry = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retry))

def fetch_page(url):
    """Fetches and parses an HTML page, handling potential errors."""
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def get_yearly_proceedings_links():

    soup = fetch_page(BASE_URL)
    if not soup:
        return []
    return [BASE_URL + a['href'] for a in soup.select("a[href^='/paper_files/paper/']")]

def get_paper_links(year_url):

    soup = fetch_page(year_url)
    if not soup:
        return []
    paper_list = soup.find('ul', class_='paper-list')
    return [BASE_URL + a['href'] for a in paper_list.find_all('a')]

def download_pdf(pdf_url, filename):

    try:
        with session.get(pdf_url, stream=True, timeout=TIMEOUT) as response:
            response.raise_for_status()
            with open(os.path.join(OUTPUT_DIR, f"{filename}.pdf"), 'wb') as file:
                for chunk in response.iter_content(8192):
                    file.write(chunk)
            print(f"Saved PDF: {filename}.pdf")
    except requests.RequestException as e:
        print(f"Failed to download {pdf_url}: {e}")

def process_paper(paper_url, download_executor):

    try:
        print(f"Processing paper: {paper_url}")
        paper_page = session.get(paper_url, timeout=TIMEOUT)
        paper_page.raise_for_status()

        soup = BeautifulSoup(paper_page.text, "html.parser")


        title_tag = soup.select_one("h4")
        paper_title = title_tag.text.strip() if title_tag else "Untitled"
        sanitized_title = sanitize_filename(paper_title)

        pdf_link = soup.select_one("a[href$='.pdf']")  
        if pdf_link:
            pdf_url = BASE_URL + pdf_link["href"]
            print(f"Found PDF link: {pdf_url}")

            download_executor.submit(download_pdf, pdf_url, sanitized_title)
        else:
            print(f"No PDF found for {paper_url}")

    except requests.RequestException as e:
        print(f"Failed to process {paper_url}: {e}")

def sanitize_filename(filename):

    return ''.join(c if c.isalnum() or c in (' ', '-') else '_' for c in filename)

def main():

    yearly_links = get_yearly_proceedings_links()
    print(f"Found {len(yearly_links)} yearly proceedings.")


    paper_links = []
    for year_link in yearly_links:
        print(f"Fetching paper links for year: {year_link}")
        paper_links.extend(get_paper_links(year_link))

    print(f"Found {len(paper_links)} total papers.")


    with ThreadPoolExecutor(max_workers =DOWNLOAD_THREADS) as download_executor:

        with ThreadPoolExecutor(max_workers=PROCESS_THREADS) as process_executor:
            process_futures = [process_executor.submit(process_paper, link, download_executor) for link in paper_links]
            for future in as_completed(process_futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing paper link: {e}")

    print("All downloads initiated.")

if __name__ == "__main__":
    main()
