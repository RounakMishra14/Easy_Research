import asyncio
import sys
import trafilatura

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.config import (
    MIN_CONTENT_LENGTH,
    PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_WAIT_TIME,
    USER_AGENT
)


# Windows fix for Playwright
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )


def clean_text(text: str) -> str:
    """
    Basic text cleaning.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    cleaned_text = "\n".join(lines)

    return cleaned_text


def extract_with_trafilatura(url: str):
    """
    Try extracting content using trafilatura.
    Best for blogs/articles/docs/news pages.
    """

    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        return None

    text = trafilatura.extract(downloaded)

    if not text:
        return None

    text = clean_text(text)

    if len(text) < MIN_CONTENT_LENGTH:
        return None

    return text


async def extract_with_playwright(url: str):
    """
    Fallback extraction using Playwright.
    Useful for JavaScript-heavy pages.
    """

    browser = None

    try:

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                user_agent=USER_AGENT
            )

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PLAYWRIGHT_TIMEOUT
            )

            await page.wait_for_timeout(
                PLAYWRIGHT_WAIT_TIME
            )

            html = await page.content()

            await browser.close()

            browser = None

        # Try trafilatura on rendered HTML
        text = trafilatura.extract(html)

        if text:

            text = clean_text(text)

            if len(text) >= MIN_CONTENT_LENGTH:
                return text

        # Backup BeautifulSoup extraction
        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript"
        ]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        text = clean_text(text)

        if len(text) >= MIN_CONTENT_LENGTH:
            return text

        return None

    except Exception as e:

        print(f"Playwright extraction failed for: {url}")

        print("Error type:", type(e).__name__)

        print("Error repr:", repr(e))

        return None

    finally:

        if browser:
            await browser.close()


async def extract_content(
    url: str,
    title: str = "",
    snippet: str = ""
):
    """
    Main extraction pipeline.

    Returns:
    {
        title,
        url,
        snippet,
        content,
        extraction_method
    }
    """

    print(f"\nTrying trafilatura for: {url}")

    text = extract_with_trafilatura(url)

    if text:

        print("✅ Extracted using trafilatura")

        return {
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": text,
            "extraction_method": "trafilatura"
        }

    print("⚠️ Trafilatura failed. Trying Playwright...")

    text = await extract_with_playwright(url)

    if text:

        print("✅ Extracted using Playwright")

        return {
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": text,
            "extraction_method": "playwright"
        }

    print("❌ Could not extract content")

    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "content": None,
        "extraction_method": None
    }