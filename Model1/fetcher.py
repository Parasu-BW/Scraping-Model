# File: fetcher.py

import os
import csv
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import time

def generate_filename_from_url(url: str) -> str:
    """Creates a safe and unique filename from a URL."""
    parsed_url = urlparse(url)
    # Sanitize the path to be a valid filename component
    path_component = parsed_url.path.replace('/', '_').replace('\\', '_')
    filename = f"{parsed_url.netloc}{path_component}.html"
    # Further clean up any characters that are invalid for filenames
    return "".join(c for c in filename if c.isalnum() or c in ('_', '.', '-')).rstrip('._-')

def fetch_page_content(url: str, output_path: str):
    """
    Uses Playwright to fetch the full, JavaScript-rendered HTML of a page and save it.
    """
    print(f"\n--- Fetching: {url} ---")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Go to the page and wait for everything to load (network to be idle)
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # An extra wait can sometimes help with very slow-loading or animated sites
            time.sleep(3) # Use time.sleep instead of page.wait_for_timeout which is deprecated
            
            # This is the magic: page.content() gets the HTML *after* JS has run
            html_content = page.content()
            
            browser.close()

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ Success! Saved to '{os.path.abspath(output_path)}'")
            return True
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return False

if __name__ == "__main__":
    DEFAULT_OUTPUT_DIR = "html_files"
    
    csv_path = input("Please enter the path to the CSV file containing URLs: ")

    try:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        
        with open(csv_path, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            if 'url' not in reader.fieldnames:
                print("❌ Error: CSV must have a header column named 'url'.")
                exit()
            
            # Read all URLs, ensuring they are not empty
            urls_to_process = [row['url'] for row in reader if row.get('url')]
        
        if not urls_to_process:
            print("No URLs found in the CSV file.")
            exit()
            
        print(f"Found {len(urls_to_process)} URLs to fetch.")
        
        for url in urls_to_process:
            filename = generate_filename_from_url(url)
            output_file_path = os.path.join(DEFAULT_OUTPUT_DIR, filename)
            fetch_page_content(url, output_file_path)

    except FileNotFoundError:
        print(f"❌ Error: The file '{csv_path}' was not found.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        
    print("\n--- Fetching Complete ---")