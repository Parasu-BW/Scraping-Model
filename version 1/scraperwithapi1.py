# # scrapwithapi_final_v6.py

# import os
# import re
# import json
# import time
# import requests
# import pandas as pd
# from datetime import datetime
# from dotenv import load_dotenv

# # -------------------------------
# # Configuration
# # -------------------------------
# load_dotenv()
# API_KEY = os.getenv("GOOGLE_API_KEY")
# if not API_KEY:
#     print("FATAL ERROR: 'GOOGLE_API_KEY' not found in .env file.")
#     raise SystemExit(1)

# API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
# URL_COLUMN_NAME = "url"
# RATE_LIMIT_SLEEP = 1.5


# # -------------------------------
# # Helper to robustly extract text from the model response
# # -------------------------------
# def extract_text_from_response(resp_json):
#     """
#     Extracts all textual content from the Gemini API response.
#     This function handles the standard response structure.
#     """
#     try:
#         # The expected path for a successful response
#         return resp_json['candidates'][0]['content']['parts'][0]['text']
#     except (KeyError, IndexError, TypeError):
#         # Fallback for unexpected structures or errors
#         print("  ⚠️ Warning: Could not find text in the standard response path. Trying a deep search.")
#         # A simple recursive search for any 'text' key
#         def find_text(obj):
#             if isinstance(obj, dict):
#                 for key, value in obj.items():
#                     if key == 'text' and isinstance(value, str):
#                         return value
#                     found = find_text(value)
#                     if found:
#                         return found
#             elif isinstance(obj, list):
#                 for item in obj:
#                     found = find_text(item)
#                     if found:
#                         return found
#             return None
        
#         found_text = find_text(resp_json)
#         if found_text:
#             return found_text
            
#         print("  ❌ Error: No 'text' field found in the entire response.")
#         print("  Raw response JSON (truncated):", json.dumps(resp_json)[:1000])
#         return ""


# # ===> UPDATED FUNCTION <===
# def extract_json_from_text(text):
#     """
#     Uses a robust regular expression to find and parse a JSON object within a string.
#     This is more reliable than splitting strings.
#     """
#     if not text or not text.strip():
#         raise ValueError("No text to parse as JSON.")

#     # Regex to find a JSON object. It looks for the first '{' and the last '}'
#     # and everything in between, spanning multiple lines.
#     json_match = re.search(r"\{.*\}", text, re.DOTALL)

#     if not json_match:
#         raise ValueError("No JSON object found in the text.")

#     try:
#         # Extract the matched string and parse it
#         json_string = json_match.group(0)
#         return json.loads(json_string)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"Could not parse extracted JSON. Error: {e}\nExtracted text: {json_string[:500]!r}")


# # -------------------------------
# # Main extraction logic
# # -------------------------------
# def extract_details_from_url(product_url):
#     print(f"▶️  Processing URL: {product_url}")

#     # ===> IMPROVED PROMPT <===
#     # This new prompt is much more detailed to get better, more consistent results.
#     prompt_text = (
#         f"Act as an expert web data extraction specialist. Your task is to scrape the product information from the following URL: {product_url}\n\n"
#         "Instructions:\n"
#         "1. Analyze the page's final, rendered HTML, as if viewed in a browser, to ensure all data is loaded.\n"
#         "2. Extract the data for the keys specified in the JSON schema below.\n"
#         "3. Extract the data directly from the page. Do not invent, infer, or guess any information.\n"
#         "4. If a specific piece of information (like 'Price' or 'Specifications') is not present on the page, you MUST use the JSON value `null` for that key.\n"
#         "5. The 'Description' should be the most detailed product description available on the page.\n"
#         "6. The 'Specifications' should be a single string, with different specs separated by a newline character (\\n).\n"
#         "7. Respond ONLY with a single, perfectly formatted JSON object. Do not include any explanatory text, comments, or markdown formatting like ```json."
#         "\n\nJSON Schema to follow:\n"
#         "{\n"
#         "  \"Product Name\": \"<The full name of the product>\",\n"
#         "  \"Price\": \"<The displayed price as a string, including currency symbol, or null if not found>\",\n"
#         "  \"Description\": \"<The detailed product description as a single string, or null if not found>\",\n"
#         "  \"Specifications\": \"<A summary of specifications as a newline-separated string, or null if not found>\"\n"
#         "}"
#     )

#     payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
#     headers = {"Content-Type": "application/json"}
#     request_url = f"{API_URL}?key={API_KEY}"

#     try:
#         resp = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=60)
#         resp.raise_for_status()
#         resp_json = resp.json()

#         extracted_text = extract_text_from_response(resp_json)
#         if not extracted_text:
#             return None # Error message was already printed by the helper function

#         try:
#             product_details = extract_json_from_text(extracted_text)
#         except ValueError as e:
#             print(f"  ❌ Error: {e}")
#             return None

#         if not isinstance(product_details, dict):
#             print("  ❌ Error: extracted JSON is not an object.")
#             return None

#         print(f"✅ Success: Extracted '{product_details.get('Product Name', 'N/A')}'")
#         return product_details

#     except requests.exceptions.RequestException as e:
#         print(f"  ❌ Error: API request failed. Error: {e}")
#         return None

# # -------------------------------
# # Script entrypoint
# # -------------------------------
# if __name__ == "__main__":
#     while True:
#         input_csv_path = input("Please enter the path to your input CSV file: ").strip('"')
#         if os.path.exists(input_csv_path):
#             break
#         else:
#             print(f"Error: The file '{input_csv_path}' was not found. Please check the path and try again.")

#     try:
#         df_urls = pd.read_csv(input_csv_path)
#     except Exception as e:
#         print(f"FATAL ERROR: Could not read the CSV file. Error: {e}")
#         raise SystemExit(1)

#     all_products_data = []
#     try:
#         for index, row in df_urls.iterrows():
#             try:
#                 url = row[URL_COLUMN_NAME]
#             except KeyError:
#                 print(f"\nFATAL ERROR: A column named '{URL_COLUMN_NAME}' was not found in '{input_csv_path}'.")
#                 print("Please make sure the first line of your CSV file is exactly 'url'.")
#                 raise SystemExit(1)

#             if isinstance(url, str) and url.strip():
#                 details = extract_details_from_url(url)
#                 if details:
#                     details['source_url'] = url
#                     all_products_data.append(details)
#                 print(f"   ... Waiting {RATE_LIMIT_SLEEP} seconds to respect API rate limits ...")
#                 time.sleep(RATE_LIMIT_SLEEP)

#     except KeyboardInterrupt:
#         print("\nInterrupted by user. Continuing to write whatever was gathered so far...")

#     if all_products_data:
#         timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#         output_csv_file = f"product_details_{timestamp}.csv"
#         df_results = pd.DataFrame(all_products_data)
#         df_results.to_csv(output_csv_file, index=False, encoding='utf-8')
#         print("\n==============================================================================")
#         print(f"🎉 Processing Complete! 🎉")
#         print(f"Data for {len(df_results)} products has been saved to: {output_csv_file}")
#         print("==============================================================================")
#     else:
#         print("\n⚠️ Processing complete, but no data was successfully extracted.")





# scrapwithapi_final_v7.py

import os
import re
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup # <-- New library
from datetime import datetime
from dotenv import load_dotenv

# -------------------------------
# Configuration
# -------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("FATAL ERROR: 'GOOGLE_API_KEY' not found in .env file.")
    raise SystemExit(1)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
URL_COLUMN_NAME = "url"
RATE_LIMIT_SLEEP = 1.5
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# -------------------------------
# Helper Functions
# -------------------------------
def extract_text_from_response(resp_json):
    try:
        return resp_json['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        print("  ⚠️ Warning: Could not find text in the standard response path.")
        return ""

def extract_json_from_text(text):
    if not text or not text.strip():
        raise ValueError("No text to parse as JSON.")
    
    # This regex is the most reliable way to find a JSON object within a larger string
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    
    if not json_match:
        raise ValueError("No JSON object found in the text.")

    try:
        json_string = json_match.group(0)
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse extracted JSON. Error: {e}\nExtracted text: {json_string[:500]!r}")

# -------------------------------
# Main Extraction Logic
# -------------------------------
def extract_details_from_url(product_url):
    print(f"▶️  Processing URL: {product_url}")

    # ===> THE NEW, HIGHLY-CONSTRAINED, "SURGICAL" PROMPT <===
    # This is the most critical change. It forces the model to be an expert.
    prompt_text = (
        "You are an automated, silent, data parsing robot. Your only function is to extract structured data from a provided webpage URL.\n\n"
        "RULES:\n"
        "1. You MUST extract the data according to the provided JSON schema. Do not add, remove, or change keys.\n"
        "2. If you cannot find a specific piece of information on the page, you MUST use the JSON value `null` for its key. Do not make up information.\n"
        "3. Your response MUST be ONLY the JSON object. Do not include any other text, explanations, or markdown like ```json.\n\n"
        "EXAMPLE:\n"
        "URL: `https://example.com/product/widget-pro`\n"
        "EXPECTED OUTPUT:\n"
        "{\n"
        "  \"Product Name\": \"Widget Pro\",\n"
        "  \"SKU\": \"WID-PRO-123\",\n"
        "  \"Price\": \"$49.99\",\n"
        "  \"Image URL\": \"https://example.com/images/widget-pro.jpg\",\n"
        "  \"Description\": \"The Widget Pro is the best widget on the market.\",\n"
        "  \"Specifications\": \"Color: Blue\\nWeight: 200g\\nMaterial: Steel\"\n"
        "}\n\n"
        "--- END OF EXAMPLE ---\n\n"
        "Now, process the following URL and provide the JSON output.\n\n"
        f"URL: {product_url}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        # Add safety settings to reduce the model's tendency to refuse requests
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }
    headers = {"Content-Type": "application/json"}
    request_url = f"{API_URL}?key={API_KEY}"

    try:
        resp = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=90)
        resp.raise_for_status()
        resp_json = resp.json()

        extracted_text = extract_text_from_response(resp_json)
        if not extracted_text:
            return None

        try:
            product_details = extract_json_from_text(extracted_text)
        except ValueError as e:
            print(f"  ❌ Error: {e}")
            return None

        if not isinstance(product_details, dict):
            print("  ❌ Error: extracted JSON is not an object.")
            return None

        print(f"✅ Success: Extracted '{product_details.get('Product Name', 'N/A')}'")
        return product_details

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: API request failed. Error: {e}")
        return None

# -------------------------------
# Script Entrypoint
# -------------------------------
if __name__ == "__main__":
    while True:
        input_csv_path = input("Please enter the path to your input CSV file: ").strip('"')
        if os.path.exists(input_csv_path):
            break
        else:
            print(f"Error: The file '{input_csv_path}' was not found. Please check the path and try again.")

    try:
        df_urls = pd.read_csv(input_csv_path)
    except Exception as e:
        print(f"FATAL ERROR: Could not read the CSV file. Error: {e}")
        raise SystemExit(1)

    all_products_data = []
    try:
        for index, row in df_urls.iterrows():
            try:
                url = row[URL_COLUMN_NAME]
            except KeyError:
                print(f"\nFATAL ERROR: A column named '{URL_COLUMN_NAME}' was not found in '{input_csv_path}'.")
                raise SystemExit(1)

            if isinstance(url, str) and url.strip():
                details = extract_details_from_url(url)
                if details:
                    details['source_url'] = url
                    all_products_data.append(details)
                print(f"   ... Waiting {RATE_LIMIT_SLEEP} seconds to respect API rate limits ...")
                time.sleep(RATE_LIMIT_SLEEP)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Writing gathered data...")

    if all_products_data:
        timestamp = datetime.now().strftime("%Y-m-%d_%H-%M-%S")
        output_csv_file = f"product_details_{timestamp}.csv"
        df_results = pd.DataFrame(all_products_data)
        df_results.to_csv(output_csv_file, index=False, encoding='utf-8')
        print("\n==============================================================================")
        print(f"🎉 Processing Complete! 🎉")
        print(f"Data for {len(df_results)} products has been saved to: {output_csv_file}")
        print("==============================================================================")
    else:
        print("\n⚠️ Processing complete, but no data was successfully extracted.")