# File: main_processor.py

import os
import json
from parser import parse_html_file
from smart_extractor import smart_extract
from datetime import datetime

HTML_DIRECTORY = "html_files"

def process_all_files():
    """
    Main orchestrator that uses the SMART extractor on all HTML files.
    """
    if not os.path.exists(HTML_DIRECTORY):
        print(f"❌ Error: Directory '{HTML_DIRECTORY}' not found. Please run fetcher.py first.")
        return

    all_scraped_data = []
    
    html_files = [f for f in os.listdir(HTML_DIRECTORY) if f.endswith(".html")]
    total_files = len(html_files)
    print(f"Found {total_files} HTML files to process in '{HTML_DIRECTORY}'.")

    for i, filename in enumerate(html_files):
        print(f"\n--- Processing file {i+1}/{total_files}: {filename} ---")
        full_path = os.path.join(HTML_DIRECTORY, filename)

        # 1. Parse the file to get a soup object
        soup = parse_html_file(full_path)
        
        if soup:
            # 2. Extract data using the smart extractor
            product_data = smart_extract(soup)
            product_data['source_file'] = filename
            all_scraped_data.append(product_data)

    # 3. Generate a timestamp string and create the unique filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"scraped_product_data_{timestamp}.json"

    # 4. Save all collected data to the new, unique file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_scraped_data, f, indent=4, ensure_ascii=False)

    print(f"\n--- ✅ All Done! ---")
    print(f"Successfully processed {len(all_scraped_data)} files.")
    print(f"All data saved to '{os.path.abspath(output_file)}'")

if __name__ == "__main__":
    process_all_files()