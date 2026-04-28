import asyncio
import os
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

FAQ_INDEX_URL = "https://www.thesamba.com/vw/forum/viewtopic.php?p=6236040#6236040"
OUTPUT_DIR    = "./samba_content"
OUTPUT_FILE   = "./samba_full_content.md"

# Only follow Vanagon forum thread links — ignore classifieds, gallery etc.
THREAD_PATTERN = re.compile(
    r'https://www\.thesamba\.com/vw/forum/viewtopic\.php\?t=\d+'
)

async def scrape_thread(crawler, url, run_config, index, total):
    """Scrape a single forum thread and return its markdown content."""
    try:
        result = await crawler.arun(url=url, config=run_config)
        if result.success:
            print(f"  [{index}/{total}] OK: {url}")
            return f"\n\n{'='*60}\nSOURCE: {url}\n{'='*60}\n{result.markdown}"
        else:
            print(f"  [{index}/{total}] FAILED: {url} — {result.error_message}")
            return ""
    except Exception as e:
        print(f"  [{index}/{total}] ERROR: {url} — {e}")
        return ""

async def main():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False      # quiet during bulk scrape
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Step 1 — Scrape the FAQ index to get all thread URLs
        print("Scraping FAQ index...")
        index_result = await crawler.arun(url=FAQ_INDEX_URL, config=run_config)

        if not index_result.success:
            print(f"Failed to scrape FAQ index: {index_result.error_message}")
            return

        # Step 2 — Extract unique thread URLs from the markdown
        thread_urls = list(set(THREAD_PATTERN.findall(index_result.markdown)))
        print(f"Found {len(thread_urls)} unique thread URLs")

        # Step 3 — Scrape each thread
        # Rate limit: small delay between requests to be respectful to TheSamba
        all_content = [f"# TheSamba Vanagon FAQ — Full Content\n"
                       f"# Scraped from: {FAQ_INDEX_URL}\n"
                       f"# Total threads: {len(thread_urls)}\n"]

        for i, url in enumerate(thread_urls, 1):
            content = await scrape_thread(crawler, url, run_config, i, len(thread_urls))
            all_content.append(content)
            await asyncio.sleep(1)   # 1 second between requests

        # Step 4 — Save everything to one file for ingest.py
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(all_content))

        print(f"\nDone! {len(thread_urls)} threads saved to {OUTPUT_FILE}")
        print(f"File size: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    asyncio.run(main())