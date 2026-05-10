import asyncio
import json
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import Browser, Page
from tenacity import retry, stop_after_attempt, wait_exponential

ROOT = Path(__file__).parent.parent

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US']});
window.chrome = {runtime: {}};
"""

VIEWPORTS = [
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
]


class BaseScraper(ABC):
    BRAND: str
    CATEGORIES: dict[str, str]

    def __init__(self, browser: Browser):
        self.browser = browser

    async def scrape_all(self) -> list[dict]:
        products = []
        for cat_key, cat_url in self.CATEGORIES.items():
            print(f"[{self.BRAND}] scraping category: {cat_key}")
            try:
                cat_products = await self.scrape_category(cat_key, cat_url)
                print(f"[{self.BRAND}] {cat_key}: {len(cat_products)} products")
                if len(cat_products) < 3:
                    print(f"[{self.BRAND}] WARNING: suspiciously few products for {cat_key}")
                products.extend(cat_products)
            except Exception as e:
                print(f"[{self.BRAND}] ERROR scraping {cat_key}: {e}")
        return products

    async def scrape_category(self, category_key: str, url: str) -> list[dict]:
        page = await self._new_page()
        try:
            return await self._scrape_with_pagination(page, category_key, url)
        finally:
            await page.close()

    async def _new_page(self) -> Page:
        viewport = random.choice(VIEWPORTS)
        context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=viewport,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = await context.new_page()
        await page.add_init_script(STEALTH_SCRIPT)
        return page

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=20))
    async def _goto(self, page: Page, url: str) -> None:
        await asyncio.sleep(random.uniform(2.5, 6.0))
        await page.goto(url, wait_until="networkidle", timeout=30_000)

    async def _scrape_with_pagination(self, page: Page, category_key: str, base_url: str) -> list[dict]:
        await self._goto(page, base_url)
        products = []
        page_num = 0

        while page_num < 50:
            html = await page.content()
            new_products = await self.parse_products(html, category_key)
            products.extend(new_products)
            page_num += 1

            if not await self.go_to_next_page(page, page_num):
                break
            await asyncio.sleep(random.uniform(1.5, 3.5))

        return products

    async def go_to_next_page(self, page: Page, current_page: int) -> bool:
        return False

    @abstractmethod
    async def parse_products(self, html: str, category: str) -> list[dict]:
        ...

    def save_raw(self, products: list[dict], date_str: str) -> None:
        out_dir = ROOT / "data" / "raw" / self.BRAND
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{date_str}.json"
        payload = {
            "brand": self.BRAND,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "products": products,
        }
        out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{self.BRAND}] saved {len(products)} products to {out_file}")
