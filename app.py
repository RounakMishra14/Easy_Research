import os
import sys
import asyncio
import requests
import trafilatura
import streamlit as st

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.async_api import async_playwright


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def search_serper(query, num_results=10):
    url = "https://google.serper.dev/search"

    payload = {
        "q": query,
        "num": num_results
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()
    return data.get("organic", [])


def extract_with_trafilatura(url):
    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        return None

    text = trafilatura.extract(downloaded)

    if text and len(text.strip()) > 200:
        return text.strip()

    return None


async def extract_with_playwright(url):
    browser = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            html = await page.content()

            await browser.close()
            browser = None

        text = trafilatura.extract(html)

        if text and len(text.strip()) > 200:
            return text.strip()

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)

        if len(cleaned_text) > 200:
            return cleaned_text

        return None

    except Exception as e:
        return f"EXTRACTION_ERROR: {type(e).__name__} - {repr(e)}"

    finally:
        if browser:
            await browser.close()


async def extract_content(url):
    text = extract_with_trafilatura(url)

    if text:
        return text, "trafilatura"

    text = await extract_with_playwright(url)

    if text and not text.startswith("EXTRACTION_ERROR"):
        return text, "playwright"

    return None, text or "No content extracted"


async def process_results(results):
    extracted_data = []

    for item in results:
        title = item.get("title", "No title")
        url = item.get("link", "")
        snippet = item.get("snippet", "")

        if not url:
            continue

        content, method = await extract_content(url)

        extracted_data.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": content,
            "method": method
        })

    return extracted_data


st.set_page_config(
    page_title="Easy Answer - Web Content Extractor",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Easy Answer - Web Content Extractor")

st.write(
    "Enter a query. The app will search using Serper API, take top 10 URLs, "
    "extract webpage content, and display it directly."
)

query = st.text_input("Enter your search query")

num_results = st.slider("Number of URLs to fetch", min_value=1, max_value=10, value=10)

if st.button("Search and Extract"):
    if not SERPER_API_KEY:
        st.error("SERPER_API_KEY not found. Please add it in your .env file.")
    elif not query.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("Searching Serper API..."):
            try:
                results = search_serper(query, num_results)
            except Exception as e:
                st.error(f"Serper search failed: {e}")
                st.stop()

        st.success(f"Found {len(results)} search results.")

        with st.spinner("Extracting webpage content..."):
            extracted_data = asyncio.run(process_results(results))

        st.subheader("Extracted Results")

        for idx, item in enumerate(extracted_data, start=1):
            with st.expander(f"{idx}. {item['title']}", expanded=False):
                st.write("**URL:**", item["url"])
                st.write("**Snippet:**", item["snippet"])
                st.write("**Extraction Method:**", item["method"])

                if item["content"]:
                    st.text_area(
                        label="Extracted Content",
                        value=item["content"],
                        height=400,
                        key=f"content_{idx}"
                    )
                else:
                    st.error(f"Could not extract content. Reason: {item['method']}")