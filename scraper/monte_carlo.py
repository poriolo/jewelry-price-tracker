import re

import httpx
from playwright.async_api import Browser, Page
from selectolax.parser import HTMLParser

from base_scraper import BaseScraper

BASE_URL = "https://www.montecarlo.com.br"

# VTEX search API (available on many Brazilian e-commerce sites built on VTEX)
VTEX_SEARCH_URL = f"{BASE_URL}/api/catalog_system/pub/products/search"


def _parse_brl(text: str) -> float | None:
    if not text:
        return None
    clean = re.sub(r"[^\d,]", "", text).replace(",", ".")
    parts = clean.split(".")
    if len(parts) > 2:
        clean = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(clean)
    except ValueError:
        return None


class MonteCarloScraper(BaseScraper):
    BRAND = "monte_carlo"
    CATEGORIES = {
        "aneis": f"{BASE_URL}/aneis",
        "pulseiras": f"{BASE_URL}/pulseiras",
        "colares": f"{BASE_URL}/colares",
        "brincos": f"{BASE_URL}/brincos",
    }

    # VTEX category tree IDs — filled after first manual inspection
    VTEX_CATEGORY_IDS: dict[str, str] = {}

    async def scrape_category(self, category_key: str, url: str) -> list[dict]:
        # Try VTEX API first (faster, no JS rendering needed)
        vtex_products = await self._try_vtex_api(category_key)
        if vtex_products:
            return vtex_products
        # Fall back to browser scraping
        return await super().scrape_category(category_key, url)

    async def _try_vtex_api(self, category_key: str) -> list[dict]:
        """
        VTEX exposes a public search API. Try fetching paginated JSON.
        Pattern: /api/catalog_system/pub/products/search?fq=C:/{cat_id}/&_from=0&_to=49
        If the site is not on VTEX, this will 404 and we fall back gracefully.
        """
        products = []
        page_size = 50
        offset = 0
        category_path = category_key.replace("_", "-")

        async with httpx.AsyncClient(timeout=15, headers={"Accept": "application/json"}) as client:
            while True:
                try:
                    resp = await client.get(
                        VTEX_SEARCH_URL,
                        params={
                            "fq": f"specificationFilter_1:{category_path}",
                            "_from": offset,
                            "_to": offset + page_size - 1,
                        },
                    )
                    if resp.status_code != 200:
                        return []
                    items = resp.json()
                    if not items:
                        break
                    for item in items:
                        name = item.get("productName", "")
                        price = None
                        original_price = None
                        try:
                            sku = item["items"][0]
                            seller = sku["sellers"][0]["commertialOffer"]
                            price = seller.get("Price")
                            original_price = seller.get("ListPrice")
                            in_stock = seller.get("AvailableQuantity", 0) > 0
                        except (KeyError, IndexError):
                            in_stock = True

                        if not price:
                            continue

                        products.append({
                            "id": f"monte_carlo-{category_key}-{item.get('productId', abs(hash(name)))}",
                            "name": name,
                            "category": category_key,
                            "price": float(price),
                            "original_price": float(original_price) if original_price else None,
                            "url": f"{BASE_URL}/{item.get('linkText', '')}/p",
                            "material": None,
                            "in_stock": in_stock,
                        })

                    offset += page_size
                    if len(items) < page_size:
                        break
                except Exception:
                    return []

        return products

    async def go_to_next_page(self, page: Page, current_page: int) -> bool:
        next_btn = page.locator(
            "a[aria-label='Próxima página'], .pagination__next, a:has-text('Próximo')"
        ).first
        try:
            if await next_btn.is_visible(timeout=2_000):
                await next_btn.click()
                await page.wait_for_load_state("networkidle", timeout=15_000)
                return True
        except Exception:
            pass
        return False

    async def parse_products(self, html: str, category: str) -> list[dict]:
        tree = HTMLParser(html)
        products = []

        cards = (
            tree.css("[class*='product-item'], [class*='ProductItem']")
            or tree.css("[class*='product-card'], [class*='ProductCard']")
            or tree.css("article")
        )

        for card in cards:
            name_node = card.css_first(
                "[class*='product-name'], [class*='ProductName'], h2, h3"
            )
            if not name_node:
                continue
            name = name_node.text(strip=True)
            if not name:
                continue

            price_node = card.css_first(
                "[class*='best-price'], [class*='BestPrice'], "
                "[class*='price-sale'], [class*='sale-price']"
            )
            original_node = card.css_first(
                "[class*='list-price'], [class*='ListPrice'], [class*='price-original']"
            )

            price = _parse_brl(price_node.text(strip=True)) if price_node else None
            original_price = _parse_brl(original_node.text(strip=True)) if original_node else None

            if price is None:
                continue

            link_node = card.css_first("a[href]")
            href = link_node.attributes.get("href", "") if link_node else ""
            url = href if href.startswith("http") else (BASE_URL + href)

            products.append({
                "id": f"monte_carlo-{category}-{abs(hash(name + str(price))) % 10**8}",
                "name": name,
                "category": category,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": None,
                "in_stock": True,
            })

        return products
