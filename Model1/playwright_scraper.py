import os
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- START: GLOBAL CURRENCY DATA (We still need this for our regex) ---
ISO_CURRENCY_CODES = [
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN", "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB",
    "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY", "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP",
    "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "FOK", "GBP", "GEL", "GGP", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL",
    "HRK", "HTG", "HUF", "IDR", "ILS", "IMP", "INR", "IQD", "IRR", "ISK", "JEP", "JMD", "JOD", "JPY", "KES", "KGS", "KHR", "KID", "KMF",
    "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR",
    "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN", "SYP",
    "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TVD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VES", "VND", "VUV",
    "WST", "XAF", "XCD", "XDR", "XOF", "XPF", "YER", "ZAR", "ZMW", "ZWL"
]
CURRENCY_SYMBOLS = [r"\$", "€", "£", "¥", "₹", "₽", "₩", "฿", "₴", "₫", "₪", "₣", "₱", "₲", "₵", "₸", "₺"]
CURRENCY_NAMES = ["dollar", "euro", "pound", "yen", "ruble", "rupee", "won", "baht", "peso", "franc", "lira", "shekel", "dinar", "riel", "dirham"]
# --- END: GLOBAL CURRENCY DATA ---

def fetch_and_extract(page, url: str):
    """
    Navigates to a URL and extracts product data using Playwright locators.
    """
    print(f"\n--- Processing URL: {url} ---")
    product_data = {"product_name": None, "price": None, "description": None}
    
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except Exception as e:
        print(f"❌ Failed to navigate to page: {e}")
        return product_data

    # --- EXTRACTION LOGIC USING PLAYWRIGHT ---

    # Strategy 1: Look for JSON-LD structured data (still the best method)
    json_ld_locator = page.locator('script[type="application/ld+json"]')
    if json_ld_locator.count() > 0:
        print("✅ Found JSON-LD data. Attempting extraction...")
        try:
            # Get the content of all found scripts and try to parse them
            for i in range(json_ld_locator.count()):
                json_text = json_ld_locator.nth(i).inner_text()
                data = json.loads(json_text)
                
                if '@graph' in data:
                    for item in data['@graph']:
                        if item.get('@type') == 'Product':
                            data = item; break
                
                if data.get('@type') == 'Product':
                    product_data['product_name'] = data.get('name')
                    product_data['description'] = data.get('description')
                    offers = data.get('offers')
                    if isinstance(offers, list): offers = offers[0]
                    if offers and offers.get('price'):
                        product_data['price'] = f"{offers.get('priceCurrency')} {offers.get('price')}"
                    print("✅ Successfully extracted from JSON-LD.")
                    return product_data # We found the data, no need to continue
        except Exception as e:
            print(f"⚠️ Could not parse JSON-LD: {e}. Falling back to heuristics.")

    # Strategy 2: Heuristic extraction using Playwright locators if JSON-LD fails
    print("ℹ️ No valid JSON-LD found. Using heuristic extraction...")
    
    # Extract Name (look for h1, fallback to title)
    name_locator = page.locator('h1').first
    if name_locator.count() > 0:
        product_data['product_name'] = name_locator.inner_text()
    else:
        product_data['product_name'] = page.title()

    # Extract Price (using the global regex on the body text)
    body_text = page.locator('body').inner_text()
    
    currency_codes_pattern = '|'.join(ISO_CURRENCY_CODES)
    currency_symbols_pattern = '|'.join(CURRENCY_SYMBOLS)
    currency_names_pattern = '|'.join([name + 's?' for name in CURRENCY_NAMES]) + '|Rs\.?'
    currency_pattern = f"({currency_codes_pattern}|{currency_symbols_pattern}|{currency_names_pattern})"
    number_pattern = r"[\d,.'’]+"
    price_regex = re.compile(f"({currency_pattern}\\s*({number_pattern}))|(({number_pattern})\\s*{currency_pattern})", re.IGNORECASE)
    
    match = price_regex.search(body_text)
    if match:
        product_data['price'] = match.group(0).strip()
    
    # Extract Description
    desc_locator = page.locator('div[class*="description"], #description').first
    if desc_locator.count() > 0:
        product_data['description'] = desc_locator.inner_text()

    return product_data

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    csv_path = input("Please enter the path to the CSV file containing URLs: ")

    try:
        with open(csv_path, 'r') as f:
            urls = [line.strip() for line in f.readlines()][1:] # Read all lines, skip header
    except FileNotFoundError:
        print(f"❌ Error: The file '{csv_path}' was not found.")
        exit()

    all_scraped_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Use headless=True for faster execution
        page = browser.new_page()
        
        for url in urls:
            if url: # Ensure the line is not empty
                data = fetch_and_extract(page, url)
                data['source_url'] = url
                all_scraped_data.append(data)
        
        browser.close()

    # Save the final results to a timestamped JSON file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"playwright_scraped_data_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_scraped_data, f, indent=4, ensure_ascii=False)

    print(f"\n--- ✅ Scraping Complete ---")
    print(f"All data saved to '{os.path.abspath(output_file)}'")