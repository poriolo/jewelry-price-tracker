import re

from playwright.async_api import Page
from selectolax.parser import HTMLParser

from base_scraper import BaseScraper
from material_detector import detect_material

BASE_URL = "https://www.vivara.com.br"


def _parse_price(text: str) -> float | None:
    text = text.strip().replace("\xa0", " ")
    m = re.search(r"[\d.,]+", text.replace(".", "").replace(",", "."))
    if not m:
        return None
    # handle "1.299,00" format
    clean = re.sub(r"[^\d,.]", "", text)
    clean = clean.replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def _parse_brl(text: str) -> float | None:
    if not text:
        return None
    # "R$ 1.299,00" → 1299.0
    clean = re.sub(r"[^\d,]", "", text)
    if not clean:
        return None
    clean = clean.replace(",", ".")
    # if there are multiple dots, keep only last as decimal
    parts = clean.split(".")
    if len(parts) > 2:
        clean = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(clean)
    except ValueError:
        return None


class VivaraScraper(BaseScraper):
    BRAND = "vivara"
    CATEGORIES = {
        "aneis": f"{BASE_URL}/aneis",
        "pulseiras": f"{BASE_URL}/pulseiras",
        "colares_pingentes": f"{BASE_URL}/colares-e-pingentes",
        "brincos": f"{BASE_URL}/brincos",
        "relogios": f"{BASE_URL}/relogios",
    }

    async def go_to_next_page(self, page: Page, current_page: int) -> bool:
        # Try "Ver mais" / load-more button
        load_more = page.locator(
            "button:has-text('Ver mais'), button:has-text('Carregar mais'), [data-testid='load-more']"
        ).first
        try:
            if await load_more.is_visible(timeout=3_000):
                prev_count = await page.locator("[class*='product-card'], [class*='ProductCard']").count()
                await load_more.click()
                await page.wait_for_function(
                    f"document.querySelectorAll(\"[class*='product-card'], [class*='ProductCard']\").length > {prev_count}",
                    timeout=10_000,
                )
                return True
        except Exception:
            pass

        # Try numbered pagination — click next page number
        next_btn = page.locator("a[aria-label='Próxima página'], a[aria-label='Next'], .pagination-next").first
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

        # Vivara product cards — selectors may need updating if site redesigns
        cards = (
            tree.css("[class*='ProductCard']")
            or tree.css("[class*='product-card']")
            or tree.css("[data-testid*='product']")
            or tree.css("article")
        )

        for card in cards:
            name_node = (
                card.css_first("[class*='ProductName'], [class*='product-name'], h2, h3")
            )
            if not name_node:
                continue
            name = name_node.text(strip=True)
            if not name:
                continue

            # price — prefer sale price, fall back to original
            price_node = card.css_first(
                "[class*='price-sale'], [class*='PriceSale'], "
                "[class*='price-final'], [class*='BestPrice'], "
                "[class*='price']:not([class*='original']):not([class*='list'])"
            )
            original_node = card.css_first(
                "[class*='price-original'], [class*='PriceOriginal'], "
                "[class*='price-list'], [class*='ListPrice']"
            )

            price = _parse_brl(price_node.text(strip=True)) if price_node else None
            original_price = _parse_brl(original_node.text(strip=True)) if original_node else None

            if price is None:
                continue

            link_node = card.css_first("a[href]")
            url = (BASE_URL + link_node.attributes.get("href", "")) if link_node else None

            material = detect_material(name)

            products.append({
                "id": f"vivara-{category}-{abs(hash(name + str(price))) % 10**8}",
                "name": name,
                "category": category,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": material,
                "in_stock": True,
            })

        return products
