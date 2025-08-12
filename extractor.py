import pandas as pd
from bs4 import BeautifulSoup
from rendered_fetcher import get_rendered_html  # JS-rendered fetcher


def extract_by_tags(url, tags, class_filter="", id_filter="", skip_empty=True, skip_duplicates=True, skip_hidden=True, depth="deep"):
    try:
        html = get_rendered_html(url)
        if not html:
            return "Error: Failed to fetch page with JS rendering."

        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen_texts = set()

        for tag in tags:
            elements = soup.find_all(tag, recursive=(depth == "deep"))

            for element in elements:
                # Filter by class
                if class_filter and class_filter not in element.get("class", []):
                    continue

                # Filter by ID
                if id_filter and element.get("id") != id_filter:
                    continue

                # Skip hidden elements
                if skip_hidden:
                    style = element.get("style", "")
                    if "display:none" in style.replace(" ", "").lower():
                        continue

                # Special handling for <img> tags
                if tag == "img":
                    src = element.get("src")
                    alt = element.get("alt", "")
                    if not src:
                        continue
                    key = f"{src}|{alt}"
                    if skip_duplicates and key in seen_texts:
                        continue
                    seen_texts.add(key)
                    results.append(f"<img>: src={src}, alt={alt}")

                # Special handling for <a> tags
                elif tag == "a":
                    href = element.get("href")
                    link_text = element.get_text(strip=True)
                    if skip_empty and not link_text:
                        continue
                    key = f"{href}|{link_text}"
                    if skip_duplicates and key in seen_texts:
                        continue
                    seen_texts.add(key)
                    results.append(f"<a>: text='{link_text}', href={href}")

                # Default handling for other tags
                else:
                    text = element.get_text(strip=True)
                    if skip_empty and not text:
                        continue
                    if skip_duplicates and text in seen_texts:
                        continue
                    seen_texts.add(text)
                    results.append(f"<{tag}>: {text}")

        return "\n".join(results) if results else "No matching elements found."

    except Exception as e:
        return f"Error: {str(e)}"



def extract_data(url):
    try:
        # Fetch full page with JS rendering
        html = get_rendered_html(url)
        if not html:
            return [], [], "Failed to fetch page with JS rendering."

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Extract visible text
        text_content = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
            text = tag.get_text(strip=True)
            if text:
                text_content.append(text)

        # Extract tables using pandas
        tables = pd.read_html(str(soup))

        if not tables:
            return [], text_content, "No tables found on this page."

        return tables, text_content, None

    except ValueError:
        return [], text_content, "No tables found on this page."
    except Exception as e:
        return [], [], f"Error during extraction: {str(e)}"


def extract_by_tags_structured(url, tags, class_filter="", id_filter="", skip_empty=True, skip_duplicates=True, skip_hidden=True, depth="deep"):
    try:
        html = get_rendered_html(url)
        if not html:
            return pd.DataFrame(), "Error: Failed to fetch page with JS rendering."

        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        rows = []

        for tag in tags:
            elements = soup.find_all(tag, recursive=(depth == "deep"))

            for element in elements:
                # Filter by class
                if class_filter and class_filter not in element.get("class", []):
                    continue

                # Filter by ID
                if id_filter and element.get("id") != id_filter:
                    continue

                # Skip hidden
                if skip_hidden:
                    style = element.get("style", "")
                    if "display:none" in style.replace(" ", "").lower():
                        continue

                # Extract main content and metadata
                text = element.get_text(strip=True)
                src_or_href = element.get("src") or element.get("href") or ""
                alt = element.get("alt", "")

                # Skip if empty
                if skip_empty and not text and not src_or_href:
                    continue

                # Prepare duplicate key
                key = f"{tag}|{text}|{src_or_href}"
                if skip_duplicates and key in seen:
                    continue
                seen.add(key)

                # Add row
                rows.append({
                    "tag": tag,
                    "text": text,
                    "src_or_href": src_or_href,
                    "alt": alt
                })

        df = pd.DataFrame(rows)
        if df.empty:
            return df, "No matching elements found."

        return df, None

    except Exception as e:
        return pd.DataFrame(), f"Error: {str(e)}"
