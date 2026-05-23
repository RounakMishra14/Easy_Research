import asyncio
import sys

import trafilatura
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# Windows fix for Playwright subprocess handling
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def extract_with_trafilatura(url: str) -> str | None:
    """
    First attempt: fetch and extract article-like readable text using trafilatura.
    Works best for blogs, articles, documentation pages, news pages.
    """
    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        return None

    text = trafilatura.extract(downloaded)

    if text and len(text.strip()) > 200:
        return text.strip()

    return None


async def extract_with_playwright(url: str) -> str | None:
    """
    Fallback attempt: render JavaScript-heavy pages using Playwright,
    then extract readable text from the rendered HTML.
    """
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

            # Give dynamic content some time to load
            await page.wait_for_timeout(5000)

            html = await page.content()

            await browser.close()
            browser = None

        # Try trafilatura on rendered HTML first
        text = trafilatura.extract(html)

        if text and len(text.strip()) > 200:
            return text.strip()

        # Backup plain text extraction using BeautifulSoup
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
        print(f"Playwright failed for: {url}")
        print("Error type:", type(e).__name__)
        print("Error repr:", repr(e))
        return None

    finally:
        if browser:
            await browser.close()


async def extract_content(url: str) -> str | None:
    """
    Complete extraction pipeline:
    1. Try trafilatura.
    2. If failed, try Playwright fallback.
    """
    print(f"\nTrying trafilatura for: {url}")

    text = extract_with_trafilatura(url)

    if text:
        print("✅ Extracted using trafilatura")
        return text

    print("⚠️ Trafilatura failed. Trying Playwright...")

    text = await extract_with_playwright(url)

    if text:
        print("✅ Extracted using Playwright fallback")
        return text

    print("❌ Could not extract content")
    return None


async def main():
    test_urls = [
        "https://www.lindy.ai/blog/best-ai-agents",
        "https://agent.ai/",
        "https://www.reddit.com/r/AI_Agents/",
    ]

    for url in test_urls:
        print("=" * 100)

        content = await extract_content(url)

        if content:
            print("\nEXTRACTED CONTENT PREVIEW:\n")
            print(content[:3000])
        else:
            print("No content extracted.")


if __name__ == "__main__":
    asyncio.run(main())
