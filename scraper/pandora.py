import re

from playwright.async_api import Page
from selectolax.parser import HTMLParser

from base_scraper import BaseScraper

BASE_URL = "https://www.pandora.net/pt-br"


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


class PandoraScraper(BaseScraper):
    BRAND = "pandora"
    CATEGORIES = {
        "moments": f"{BASE_URL}/categorias/joias/chaveiros-berloque-pingente",
        "pulseiras": f"{BASE_URL}/categorias/joias/pulseiras",
        "colares": f"{BASE_URL}/categorias/joias/colares-e-pingentes",
        "aneis": f"{BASE_URL}/categorias/joias/aneis",
        "brincos": f"{BASE_URL}/categorias/joias/brincos",
    }

    async def go_to_next_page(self, page: Page, current_page: int) -> bool:
        # Pandora uses a "Show more" button or infinite scroll
        load_more = page.locator(
            "button:has-text('Mostrar mais'), button:has-text('Ver mais'), "
            "[data-testid='load-more-button'], button[class*='load-more']"
        ).first
        try:
            if await load_more.is_visible(timeout=3_000):
                prev_count = await page.locator("[class*='product'], article").count()
                await load_more.scroll_into_view_if_needed()
                await load_more.click()
                await page.wait_for_function(
                    f"document.querySelectorAll(\"[class*='product'], article\").length > {prev_count}",
                    timeout=10_000,
                )
                return True
        except Exception:
            pass
        return False

    async def parse_products(self, html: str, category: str) -> list[dict]:
        tree = HTMLParser(html)
        products = []

        cards = (
            tree.css("[class*='product-tile'], [class*='ProductTile']")
            or tree.css("[class*='product-item'], [class*='ProductItem']")
            or tree.css("[class*='product-card'], [class*='ProductCard']")
            or tree.css("article")
        )

        for card in cards:
            name_node = card.css_first(
                "[class*='product-name'], [class*='ProductName'], h2, h3, [class*='title']"
            )
            if not name_node:
                continue
            name = name_node.text(strip=True)
            if not name:
                continue

            price_node = card.css_first(
                "[class*='sales-price'], [class*='SalesPrice'], "
                "[class*='price--sale'], [class*='price']:not([class*='original'])"
            )
            original_node = card.css_first(
                "[class*='list-price'], [class*='ListPrice'], [class*='price--list']"
            )

            price = _parse_brl(price_node.text(strip=True)) if price_node else None
            original_price = _parse_brl(original_node.text(strip=True)) if original_node else None

            if price is None:
                continue

            link_node = card.css_first("a[href]")
            href = link_node.attributes.get("href", "") if link_node else ""
            url = href if href.startswith("http") else ("https://www.pandora.net" + href)

            products.append({
                "id": f"pandora-{category}-{abs(hash(name + str(price))) % 10**8}",
                "name": name,
                "category": category,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": None,
                "in_stock": True,
            })

        return products
