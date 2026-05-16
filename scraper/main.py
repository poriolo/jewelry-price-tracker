import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aggregator import append_daily_summary, rebuild_history
import vivara
import pandora
import monte_carlo


async def run(date_str: str) -> None:
    scrapers = [
        ("vivara",      vivara.scrape_all),
        ("pandora",     pandora.scrape_all),
        ("monte_carlo", monte_carlo.scrape_all),
    ]

    for brand, scrape_fn in scrapers:
        print(f"\n{'='*50}\nStarting {brand}\n{'='*50}")
        try:
            products = await scrape_fn()
            # save raw file
            import json
            out_dir = Path(__file__).parent.parent / "data" / "raw" / brand
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{date_str}.json"
            out_file.write_text(
                json.dumps(
                    {"brand": brand, "scraped_at": datetime.now(timezone.utc).isoformat(), "products": products},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
            print(f"[{brand}] saved {len(products)} products")
        except Exception as e:
            print(f"[main] FATAL error for {brand}: {e}")

    print("\n[main] computing aggregates...")
    append_daily_summary(date_str)
    rebuild_history()
    print("[main] done.")


if __name__ == "__main__":
    date_override = os.getenv("SCRAPER_DATE_OVERRIDE", "").strip()
    today = date_override or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[main] scraping for date: {today}")
    asyncio.run(run(today))
