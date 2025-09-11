# File: parser.py

from bs4 import BeautifulSoup
import os

def parse_html_file(html_file_path: str):
    """
    Parses an HTML file and turns it into a BeautifulSoup object.
    This is the function that main_processor.py will import.
    """
    print("--- Running Parser ---")
    
    if not os.path.exists(html_file_path):
        print(f"❌ Error: The file '{html_file_path}' was not found.")
        return None
    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Using 'lxml' is a fast and robust parser
        soup = BeautifulSoup(html_content, 'lxml')
        print("✅ Parser success: HTML ready.")
        return soup
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        return None

# This block is ONLY for testing this single file directly.
# It does not run when the main script imports from here.
if __name__ == "__main__":
    print(">>> Testing parser.py directly...")
    # To test, create a dummy html file with this name or change the name
    INPUT_FILENAME = "test_page.html" 
    if not os.path.exists(INPUT_FILENAME):
        print(f"Test file '{INPUT_FILENAME}' not found. Please create it to test.")
    else:
        soup_object = parse_html_file(INPUT_FILENAME)
        if soup_object:
            print(">>> Test successful!")
        else:
            print(">>> Test failed.")