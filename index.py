import os
import time
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Websites to scrape
websites = [
    "https://www.boeing.com",
    "https://www.goldmansachs.com",
    "https://corporate.exxonmobil.com",
    "https://www.hsbc.com",
    "https://www.volkswagenag.com",
    "https://www.ibm.com",
    "https://www.unilever.com",
    "https://www.amazon.com",
    "https://www.sony.com",
    "https://www.mcdonalds.com",
]

# Headers to mimic a real browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Questions for Gemini AI
questions = [
    "What is the company's mission statement or core values?",
    "What products or services does the company offer?",
    "When was the company founded, and who were the founders?",
    "Where is the company's headquarters located?",
    "Who are the key executives or leadership team members?",
    "Has the company received any notable awards or recognitions?"
]

def fetch_page(url):
    """Fetches the webpage and removes unnecessary tags."""
    time.sleep(random.uniform(1, 3))  # Random delay to avoid rate-limiting
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "meta", "noscript"]):
                tag.decompose()
            return soup
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
    return None

def extract_internal_links(base_url):
    """Extracts internal links from the header and footer."""
    soup = fetch_page(base_url)
    if not soup:
        return []
    
    internal_links = set()
    for section in ["header", "footer"]:
        for link in soup.select(f"{section} a[href]"):
            url = link['href']
            if url.startswith('/') or base_url in url:
                full_url = url if base_url in url else base_url + url
                internal_links.add(full_url)
    
    return list(internal_links)

def filter_relevant_links_with_gemini(base_url, links):
    """Asks Gemini AI to filter relevant links and cleans the output."""
    if not links:
        return []
    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            f"Here are some internal links from {base_url}:\n\n" + "\n".join(links) +
            "\n\nWhich of these pages are most likely to contain information about the company’s mission, leadership, history, products, and awards?"
            " Return the relevant and probable links, one per line, without bullet points or extra text."
        )
        response = model.generate_content(prompt)
        
        if response and response.text:
            relevant_links = response.text.strip().split("\n")
            cleaned_links = [link.strip().lstrip("*") for link in relevant_links if link.strip()]
            return [link for link in cleaned_links if link.startswith("http")]
    
    except Exception as e:
        print("Error with Gemini API:", e)
    
    return []

def extract_text_from_url(url):
    """Extracts textual content (h1-h6 and p) from the given URL."""
    try:
        time.sleep(1)  # Avoid rate-limiting
        soup = fetch_page(url)
        if not soup:
            return ""
        
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) if h.get_text().strip()]
        paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
        return "\n".join(headings + paragraphs)
    except Exception as e:
        print(f"Error extracting text from {url}: {e}")
        return ""

# Open file to store extracted info
with open("extracted_info.txt", "w", encoding="utf-8") as file:
    file.write("=== Extracted Company Information ===\n\n")

# Process each website
for website in websites:
    print(f"\nProcessing: {website}\n" + "="*50)
    
    # Step 1: Get all internal links from header & footer
    all_internal_links = extract_internal_links(website)
    print(f"Found {len(all_internal_links)} internal links.")

    # Step 2: Let Gemini filter relevant links
    relevant_links = filter_relevant_links_with_gemini(website, all_internal_links)
    print(f"LLM selected {len(relevant_links)} relevant links.")

    # Step 3: Extract content from selected links
    combined_content = ""
    for link in relevant_links:
        print(f"Extracting content from: {link}")
        combined_content += extract_text_from_url(link) + "\n\n"

    if combined_content.strip():
        # Step 4: Ask Gemini to generate answers from all combined content
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = f"Using the extracted text:\n\n{combined_content}\n\nAnswer these questions based only on the text:\n" + "\n".join(questions)
            response = model.generate_content(prompt)
            answers = response.text if response else "No response from Gemini API"
            
            result_text = f"\n=== Extracted Information from {website} ===\n\n" + answers
            print(result_text)

            # Append extracted info to file
            with open("extracted_info.txt", "a", encoding="utf-8") as file:
                file.write(result_text + "\n\n")
        except Exception as e:
            print("Error with Gemini API:", e)
    else:
        print(f"No relevant content extracted from {website}.")
