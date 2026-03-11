import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def main():
    # 1. Configure the browser
    # We use headless=True for speed, but you can set it to False to see it work.
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=True
    )

    # 2. Configure the run settings
    # CacheMode.BYPASS ensures we get fresh content every time.
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )

    url = "https://www.thesamba.com/vw/forum/viewtopic.php?p=6236040#6236040"

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 3. Perform the crawl
        result = await crawler.arun(url=url, config=run_config)

        if result.success:
            # 4. Save the result to FAQ_md.md
            # Crawl4AI provides the markdown in result.markdown
            filename = "FAQ_md.md"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(result.markdown)

            print(f"--- Success! ---")
            print(f"Content from {url} has been saved to {filename}")
        else:
            print(f"Failed to crawl the page. Error: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())