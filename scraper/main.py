import asyncio
import os
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# allow running from repo root or scraper/ directory
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from aggregator import append_daily_summary, rebuild_history
from vivara import VivaraScraper
from pandora import PandoraScraper
from monte_carlo import MonteCarloScraper

SCRAPERS = [VivaraScraper, PandoraScraper, MonteCarloScraper]


async def run(date_str: str) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for ScraperClass in SCRAPERS:
                scraper = ScraperClass(browser)
                print(f"\n{'='*50}")
                print(f"Starting {scraper.BRAND}")
                print(f"{'='*50}")
                try:
                    products = await scraper.scrape_all()
                    scraper.save_raw(products, date_str)
                except Exception as e:
                    print(f"[main] FATAL error for {scraper.BRAND}: {e}")
        finally:
            await browser.close()

    print("\n[main] computing aggregates...")
    append_daily_summary(date_str)
    rebuild_history()
    print("[main] done.")


if __name__ == "__main__":
    date_override = os.getenv("SCRAPER_DATE_OVERRIDE", "").strip()
    today = date_override or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[main] scraping for date: {today}")
    asyncio.run(run(today))
