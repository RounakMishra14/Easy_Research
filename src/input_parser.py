# src/input_parser.py

import re
from urllib.parse import urlparse


def is_youtube_url(url: str) -> bool:
    """
    Checks whether a URL belongs to YouTube.
    Supports both youtube.com and youtu.be links.
    """
    lower_url = url.lower()
    return "youtube.com" in lower_url or "youtu.be" in lower_url


def is_url(text: str) -> bool:
    """
    Validates whether the given text is a proper http/https URL.
    """
    try:
        parsed = urlparse(text)
        return parsed.scheme in ["http", "https"] and bool(parsed.netloc)
    except Exception:
        return False


def extract_urls_and_queries(source_input: str):
    """
    Allows the user to paste mixed input in one box:
    - normal Google search text
    - one or multiple website URLs
    - YouTube URLs

    URLs can be pasted line by line, comma separated, or mixed inside text.

    Returns:
        clean_urls: list of valid unique URLs
        google_query: remaining text to use as Google search query
    """

    if not source_input:
        return [], ""

    url_pattern = r"https?://[^\s,]+"
    urls = re.findall(url_pattern, source_input)

    query_text = re.sub(url_pattern, " ", source_input)
    query_lines = [
        line.strip(" ,")
        for line in query_text.splitlines()
        if line.strip(" ,")
    ]

    google_query = " ".join(query_lines).strip()

    seen = set()
    clean_urls = []

    for url in urls:
        clean_url = url.strip().rstrip(").,]")

        if clean_url and clean_url not in seen and is_url(clean_url):
            clean_urls.append(clean_url)
            seen.add(clean_url)

    return clean_urls, google_query