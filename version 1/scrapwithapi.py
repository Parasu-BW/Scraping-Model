
import os
import re
import json
import time
import requests
import pandas as pd
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

# Keep the same endpoint you used; if your project uses a different version change here
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
URL_COLUMN_NAME = "url"
RATE_LIMIT_SLEEP = 1.5


# -------------------------------
# Helpers to robustly extract text / JSON from the model response
# -------------------------------

def _join_nonempty(strings):
    return "\n\n".join([s for s in strings if s and str(s).strip()])


def extract_text_from_response(resp_json):
    """Attempt to extract textual output from many possible shapes of the Generative API response.
    Returns a single string (possibly empty) with the model's textual output.
    """
    pieces = []

    # 1) candidates is commonly a list
    candidates = resp_json.get("candidates") if isinstance(resp_json, dict) else None
    if candidates and isinstance(candidates, list):
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            # content may be a dict with 'parts' (list) or 'text'
            content = cand.get("content") or cand.get("message") or cand.get("output") or cand
            if isinstance(content, dict):
                parts = content.get("parts") or content.get("text")
                if isinstance(parts, list):
                    for p in parts:
                        if isinstance(p, str):
                            pieces.append(p)
                        elif isinstance(p, dict) and "text" in p:
                            pieces.append(p.get("text"))
                elif isinstance(parts, str):
                    pieces.append(parts)
            elif isinstance(content, str):
                pieces.append(content)

    # 2) outputs / output (other possible response shapes)
    if not pieces:
        for key in ("output", "outputs", "response", "message", "result"):
            val = resp_json.get(key) if isinstance(resp_json, dict) else None
            if not val:
                continue
            if isinstance(val, str):
                pieces.append(val)
            elif isinstance(val, dict):
                parts = val.get("parts") or val.get("content") or val.get("text")
                if isinstance(parts, list):
                    for p in parts:
                        if isinstance(p, str):
                            pieces.append(p)
                        elif isinstance(p, dict) and "text" in p:
                            pieces.append(p.get("text"))
                elif isinstance(parts, str):
                    pieces.append(parts)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        pieces.append(item)
                    elif isinstance(item, dict):
                        p = item.get("content") or item.get("parts") or item.get("text")
                        if isinstance(p, list):
                            for q in p:
                                pieces.append(q if isinstance(q, str) else q.get("text", ""))
                        elif isinstance(p, str):
                            pieces.append(p)

    # 3) fallback: try top-level keys that might contain text
    if not pieces and isinstance(resp_json, dict):
        for k in ("text", "answer", "output_text"):
            if k in resp_json and isinstance(resp_json[k], str):
                pieces.append(resp_json[k])

    return _join_nonempty(pieces)



def extract_json_from_text(text):
    """Try several heuristics to extract JSON from the model's text output.
    Returns a Python object (dict/list) on success, or raises a ValueError on failure.
    """
    if not text or not text.strip():
        raise ValueError("No text to parse as JSON.")

    # 1) fenced code block with ```json
    if "```json" in text:
        try:
            after = text.split("```json", 1)[1]
            candidate = after.rsplit("```", 1)[0].strip()
            return json.loads(candidate)
        except Exception:
            # fallthrough to other heuristics
            pass

    # 2) find the first {...} or [...] block and try to load it
    # Try to be conservative: find first '{' and matching '}', or first '[' and matching ']' (last occurrence)
    braces_start = text.find("{")
    braces_end = text.rfind("}")
    if braces_start != -1 and braces_end != -1 and braces_end > braces_start:
        candidate = text[braces_start:braces_end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    bracks_start = text.find("[")
    bracks_end = text.rfind("]")
    if bracks_start != -1 and bracks_end != -1 and bracks_end > bracks_start:
        candidate = text[bracks_start:bracks_end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3) finally try json.loads on the whole text
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from model text. Error: {e}\nModel text (truncated): {text[:1000]!r}")


# -------------------------------
# Main extraction logic
# -------------------------------

def extract_details_from_url(product_url):
    print(f"▶️  Processing URL: {product_url}")

    prompt_text = (
        f"Please perform web scraping on the following URL and extract detailed product information: {product_url}. "
        "Extract the following keys: 'Product Name', 'Price', 'Description', and 'Specifications'. "
        "Return the result as a single, clean JSON object with no other text, comments, or explanations."
    )

    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    headers = {"Content-Type": "application/json"}
    request_url = f"{API_URL}?key={API_KEY}"

    try:
        resp = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        resp_json = resp.json()

        # Robustly extract textual output from whatever shape the model returned
        extracted_text = extract_text_from_response(resp_json)
        if not extracted_text:
            print("  ❌ Error: model response did not contain any recognizable text output.")
            print("  Raw response JSON (truncated):", json.dumps(resp_json)[:2000])
            return None

        # Try to pull JSON out of the text
        try:
            product_details = extract_json_from_text(extracted_text)
        except ValueError as e:
            print("  ❌ Error: Could not parse JSON from model text.")
            print("  Error details:", e)
            print("  Full model text (truncated):", extracted_text[:2000])
            return None

        # Ensure we have a dict (or wrap list into a dict)
        if isinstance(product_details, list):
            # if the model returned a list of objects, wrap them under 'items'
            product_details = {"items": product_details}
        elif not isinstance(product_details, dict):
            print("  ❌ Error: extracted JSON is not an object or array.")
            return None

        print(f"✅ Success: Extracted '{product_details.get('Product Name', product_details.get('title', 'N/A'))}'")
        return product_details

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error: API request failed. Error: {e}")
        return None


# -------------------------------
# Script entrypoint
# -------------------------------

if __name__ == "__main__":
    # ask for CSV path (compatible with your original flow)
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
                print("Please make sure the first line of your CSV file is exactly 'url'.")
                raise SystemExit(1)

            if isinstance(url, str) and url.strip():
                details = extract_details_from_url(url)
                if details:
                    details['source_url'] = url
                    all_products_data.append(details)
                print(f"   ... Waiting {RATE_LIMIT_SLEEP} seconds to respect API rate limits ...")
                time.sleep(RATE_LIMIT_SLEEP)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Continuing to write whatever was gathered so far...")

    if all_products_data:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_csv_file = f"product_details_{timestamp}.csv"
        df_results = pd.DataFrame(all_products_data)
        df_results.to_csv(output_csv_file, index=False, encoding='utf-8')
        print("\n==============================================================================")
        print(f"🎉 Processing Complete! 🎉")
        print(f"Data for {len(df_results)} products has been saved to: {output_csv_file}")
        print("==============================================================================")
    else:
        print("\n⚠️ Processing complete, but no data was successfully extracted.")

