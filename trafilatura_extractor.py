# trafilatura_extractor.py

import trafilatura
import requests
from bs4 import BeautifulSoup
import re

def extract_clean_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            clean_text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if clean_text and len(clean_text.strip()) > 50:
                return clean_wikipedia(clean_text)

        # Fallback to BeautifulSoup if Trafilatura fails
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            fallback_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            if fallback_text:
                return clean_wikipedia(fallback_text)
            else:
                return "No readable paragraph text found."
        else:
            return f"Error: Failed to fetch page (status code: {response.status_code})"

    except Exception as e:
        return f"Error: {str(e)}"

def clean_wikipedia(text):
    # Remove footnote references like [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)

    # Remove edit-like sections
    text = re.sub(r'\[edit\]', '', text)

    # Strip extra whitespace
    return text.strip()
