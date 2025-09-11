# # File: smart_extractor.py

# import json
# import re
# import unicodedata

# # --- START: GLOBAL CURRENCY DATA ---
# ISO_CURRENCY_CODES = [
#     "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN", "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB",
#     "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY", "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP",
#     "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "FOK", "GBP", "GEL", "GGP", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL",
#     "HRK", "HTG", "HUF", "IDR", "ILS", "IMP", "INR", "IQD", "IRR", "ISK", "JEP", "JMD", "JOD", "JPY", "KES", "KGS", "KHR", "KID", "KMF",
#     "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR",
#     "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
#     "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN", "SYP",
#     "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TVD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VES", "VND", "VUV",
#     "WST", "XAF", "XCD", "XDR", "XOF", "XPF", "YER", "ZAR", "ZMW", "ZWL"
# ]
# CURRENCY_SYMBOLS = [r"\$", "€", "£", "¥", "₹", "₽", "₩", "฿", "₴", "₫", "₪", "₣", "₱", "₲", "₵", "₸", "₺"]
# CURRENCY_NAMES = ["dollar", "euro", "pound", "yen", "ruble", "rupee", "won", "baht", "peso", "franc", "lira", "shekel", "dinar", "riel", "dirham"]
# # --- END: GLOBAL CURRENCY DATA ---

# def normalize_text(text: str) -> str:
#     if not text: return text
#     try:
#         decomposed_text = unicodedata.normalize('NFKD', text)
#         return decomposed_text.encode('ascii', 'ignore').decode('utf-8')
#     except (TypeError, AttributeError): return text

# def find_product_name(soup):
#     name = None
#     if soup.h1: name = soup.h1.get_text(strip=True)
#     elif soup.title and soup.title.string: name = soup.title.string.strip()
#     return normalize_text(name)

# def find_price(soup):
#     currency_codes_pattern = '|'.join(ISO_CURRENCY_CODES)
#     currency_symbols_pattern = '|'.join(CURRENCY_SYMBOLS)
#     currency_names_pattern = '|'.join([name + 's?' for name in CURRENCY_NAMES]) + '|Rs\.?'
#     currency_pattern = f"({currency_codes_pattern}|{currency_symbols_pattern}|{currency_names_pattern})"
#     number_pattern = r"[\d,.'’]+"
#     price_regex = re.compile(f"({currency_pattern}\\s*({number_pattern}))|(({number_pattern})\\s*{currency_pattern})", re.IGNORECASE)
#     price_text = None
#     price_container = soup.find(lambda tag: any('price' in c for c in tag.get('class', [])) or 'price' in tag.get('id', ''))
#     if price_container:
#         price_node = price_container.find(string=price_regex)
#         if price_node: price_text = price_node.strip()
#     if not price_text:
#         price_node = soup.find(string=price_regex)
#         if price_node: price_text = price_node.strip()
#     if price_text:
#         number_part = re.sub(r'[^\d.]', '', price_text)
#         currency_part = re.sub(r'[\d,.\'’\s]', '', price_text).upper()
#         if currency_part in ["$", "DOLLAR"]: currency_part = "USD"
#         if currency_part in ["£", "POUND"]: currency_part = "GBP"
#         if currency_part in ["€", "EURO"]: currency_part = "EUR"
#         if currency_part in ["¥", "YEN"]: currency_part = "JPY"
#         if currency_part in ["₹", "RS", "RUPEE", "RS."]: currency_part = "INR"
#         if number_part: return normalize_text(f"{currency_part} {number_part}")
#     return None

# def find_description(soup):
#     desc_container = soup.find(['div', 'section'], id=re.compile('description', re.I)) or \
#                      soup.find(['div', 'section'], class_=re.compile('description', re.I))
#     if desc_container:
#         description_text = ' '.join(desc_container.get_text(separator=' ').split())
#         return normalize_text(description_text)
#     return None

# def smart_extract(soup):
#     print("--- Running Smart Extractor ---")
#     product_data = {"product_name": None, "price": None, "description": None, "full_page_text": None}
#     if soup and soup.body:
#         all_text = soup.body.get_text(separator=' ', strip=True)
#         product_data['full_page_text'] = normalize_text(all_text)
#     json_ld_script = soup.find("script", type="application/ld+json")
#     if json_ld_script:
#         print("✅ Found JSON-LD structured data! Using this for extraction.")
#         try:
#             data = json.loads(json_ld_script.string)
#             if '@graph' in data:
#                 for item in data['@graph']:
#                     if item.get('@type') == 'Product': data = item; break
#             product_data['product_name'] = normalize_text(data.get('name'))
#             product_data['description'] = normalize_text(data.get('description'))
#             offers = data.get('offers')
#             if isinstance(offers, list): offers = offers[0]
#             if offers and offers.get('price'):
#                 price = offers.get('price')
#                 currency = offers.get('priceCurrency')
#                 product_data['price'] = normalize_text(f"{currency} {price}")
#             print("✅ Successfully extracted and normalized from JSON-LD.")
#             return product_data
#         except Exception as e:
#             print(f"⚠️ Warning: Could not parse JSON-LD data. Error: {e}. Falling back.")
#     print("ℹ️ No JSON-LD data found. Using heuristic pattern matching...")
#     product_data['product_name'] = find_product_name(soup)
#     product_data['price'] = find_price(soup)
#     product_data['description'] = find_description(soup)
#     print("✅ Heuristic extraction and normalization finished.")
#     return product_data









# File: smart_extractor.py

import json
import re
import unicodedata

# --- START: GLOBAL CURRENCY DATA ---

# A comprehensive list of ISO 4217 currency codes.
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

# Common currency symbols. We must escape characters that are special in regex (like $).
CURRENCY_SYMBOLS = [r"\$", "€", "£", "¥", "₹", "₽", "₩", "฿", "₴", "₫", "₪", "₣", "₱", "₲", "₵", "₸", "₺"]

# Common currency names (case-insensitive).
CURRENCY_NAMES = ["dollar", "euro", "pound", "yen", "ruble", "rupee", "won", "baht", "peso", "franc", "lira", "shekel", "dinar", "riel", "dirham"]

# --- END: GLOBAL CURRENCY DATA ---

def normalize_text(text: str) -> str:
    """
    Normalizes Unicode text by converting special characters like 'é' to 'e'.
    """
    if not text:
        return text
    try:
        decomposed_text = unicodedata.normalize('NFKD', text)
        return decomposed_text.encode('ascii', 'ignore').decode('utf-8')
    except (TypeError, AttributeError):
        return text

# --- Heuristic Search Functions ---

def find_product_name(soup):
    """Finds and normalizes the product name using common patterns."""
    name = None
    if soup.h1:
        name = soup.h1.get_text(strip=True)
    elif soup.title and soup.title.string:
        name = soup.title.string.strip()
    return normalize_text(name)

def find_price(soup):
    """
    Finds the price using a globally comprehensive list of currencies.
    This FINAL version uses a hybrid approach to be more resilient.
    """
    # 1. Build the master regex
    currency_codes_pattern = '|'.join(ISO_CURRENCY_CODES)
    currency_symbols_pattern = '|'.join(CURRENCY_SYMBOLS)
    currency_names_pattern = '|'.join([name + 's?' for name in CURRENCY_NAMES]) + '|Rs\.?'
    currency_pattern = f"({currency_codes_pattern}|{currency_symbols_pattern}|{currency_names_pattern})"
    number_pattern = r"[\d,.'’]+"
    price_regex = re.compile(f"({currency_pattern}\\s*({number_pattern}))|(({number_pattern})\\s*{currency_pattern})", re.IGNORECASE)

    price_text = None

    # STRATEGY 1: Search within a likely price container
    price_container = soup.find(lambda tag: any('price' in c for c in tag.get('class', [])) or 'price' in tag.get('id', ''))
    
    if price_container:
        # Get ALL text from the container, then search it with the regex
        container_text = price_container.get_text(separator=' ')
        match = price_regex.search(container_text)
        if match:
            price_text = match.group(0).strip() # Extract the matched price string

    # STRATEGY 2: Fallback to searching the entire body
    if not price_text and soup.body:
        body_text = soup.body.get_text(separator=' ')
        match = price_regex.search(body_text)
        if match:
            price_text = match.group(0).strip()

    # 3. If a price was found, clean and standardize it
    if price_text:
        number_part = re.sub(r'[^\d.]', '', price_text)
        currency_part = re.sub(r'[\d,.\'’\s]', '', price_text).upper()

        if currency_part in ["$", "DOLLAR"]: currency_part = "USD"
        if currency_part in ["£", "POUND"]: currency_part = "GBP"
        if currency_part in ["€", "EURO"]: currency_part = "EUR"
        if currency_part in ["¥", "YEN"]: currency_part = "JPY"
        if currency_part in ["₹", "RS", "RUPEE", "RS."]: currency_part = "INR"

        if number_part:
            return normalize_text(f"{currency_part} {number_part}")

    return None

def find_description(soup):
    """Finds and normalizes the description by looking for keyworded containers."""
    desc_container = soup.find(['div', 'section'], id=re.compile('description', re.I)) or \
                     soup.find(['div', 'section'], class_=re.compile('description', re.I))
    if desc_container:
        description_text = ' '.join(desc_container.get_text(separator=' ').split())
        return normalize_text(description_text)
    return None

# --- Main Smart Extractor Function ---

def smart_extract(soup):
    """
    Extracts structured data and the full page text for verification.
    """
    print("--- Running Smart Extractor ---")
    
    product_data = {
        "product_name": None,
        "price": None,
        "description": None,
        "full_page_text": None # The new field for verification
    }

    if soup and soup.body:
        all_text = soup.body.get_text(separator=' ', strip=True)
        product_data['full_page_text'] = normalize_text(all_text)

    # Strategy 1: Look for embedded JSON-LD structured data
    json_ld_script = soup.find("script", type="application/ld+json")
    if json_ld_script:
        print("✅ Found JSON-LD structured data! Using this for extraction.")
        try:
            data = json.loads(json_ld_script.string)
            if '@graph' in data:
                for item in data['@graph']:
                    if item.get('@type') == 'Product':
                        data = item; break
            
            product_data['product_name'] = normalize_text(data.get('name'))
            product_data['description'] = normalize_text(data.get('description'))
            
            offers = data.get('offers')
            if isinstance(offers, list): offers = offers[0]
            if offers and offers.get('price'):
                price = offers.get('price')
                currency = offers.get('priceCurrency')
                product_data['price'] = normalize_text(f"{currency} {price}")
            
            print("✅ Successfully extracted and normalized from JSON-LD.")
            return product_data
        except Exception as e:
            print(f"⚠️ Warning: Could not parse JSON-LD data. Error: {e}. Falling back.")

    # Strategy 2: Fallback to heuristic functions
    print("ℹ️ No JSON-LD data found. Using heuristic pattern matching...")
    product_data['product_name'] = find_product_name(soup)
    product_data['price'] = find_price(soup)
    product_data['description'] = find_description(soup)
    
    print("✅ Heuristic extraction and normalization finished.")
    return product_data