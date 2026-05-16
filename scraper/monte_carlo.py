"""
Monte Carlo scraper — VTEX Intelligent Search API.
"""
import asyncio
import random

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://www.montecarlo.com.br"
SEARCH_URL = f"{BASE_URL}/_v/api/intelligent-search/product_search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

BRAND = "monte_carlo"

CATEGORIES = {
    "aneis":     "joias/aneis",
    "pulseiras": "joias/pulseiras",
    "colares":   "joias/colares",
    "brincos":   "joias/brincos",
}


async def _init_session(client: httpx.AsyncClient) -> None:
    try:
        resp = await client.get(BASE_URL, headers={**HEADERS, "Accept": "text/html"}, timeout=15)
        print(f"[monte_carlo] session init: {resp.status_code}, cookies: {list(resp.cookies.keys())}")
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        print(f"[monte_carlo] session init warning: {e}")


def _parse_price(item: dict) -> tuple[float | None, float | None]:
    try:
        pr = item.get("priceRange", {})
        price = pr.get("sellingPrice", {}).get("lowPrice")
        list_price = pr.get("listPrice", {}).get("lowPrice")
        if price:
            return float(price), float(list_price) if list_price else None
    except Exception:
        pass
    try:
        offer = item["items"][0]["sellers"][0]["commertialOffer"]
        price = offer.get("Price")
        list_price = offer.get("ListPrice")
        if price:
            return float(price), float(list_price) if list_price else None
    except Exception:
        pass
    return None, None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=5, max=20))
async def _fetch_page(client: httpx.AsyncClient, category_slug: str, page: int) -> dict:
    await asyncio.sleep(random.uniform(1.5, 3.0))
    url = f"{SEARCH_URL}/{category_slug}"
    resp = await client.get(
        url,
        params={"count": 50, "page": page, "locale": "pt-BR"},
        headers={**HEADERS, "Referer": f"{BASE_URL}/{category_slug}"},
        timeout=20,
    )
    print(f"[monte_carlo] GET {url} page={page} → {resp.status_code}")
    resp.raise_for_status()
    # Monte Carlo retorna encoding não-UTF8 — decodifica manualmente
    try:
        data = resp.json()
    except (UnicodeDecodeError, Exception):
        import json as _json
        data = _json.loads(resp.content.decode("latin-1", errors="replace"))
    if isinstance(data, dict):
        print(f"[monte_carlo] keys: {list(data.keys())}, products: {len(data.get('products', []))}")
    return data


async def scrape_category(client: httpx.AsyncClient, cat_key: str, cat_slug: str) -> list[dict]:
    products = []
    page = 1

    while True:
        try:
            data = await _fetch_page(client, cat_slug, page)
        except Exception as e:
            print(f"[monte_carlo] ERROR page {page} of {cat_key}: {e}")
            break

        items = data.get("products", []) if isinstance(data, dict) else data
        if not items:
            break

        for item in items:
            name = item.get("productName", "")
            price, original_price = _parse_price(item)
            if not price:
                continue
            link = item.get("link", "")
            url = BASE_URL + link if link.startswith("/") else link
            products.append({
                "id": f"monte_carlo-{cat_key}-{item.get('productId', abs(hash(name)))}",
                "name": name,
                "category": cat_key,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": None,
                "in_stock": True,
            })

        pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
        total = pagination.get("count", 0)
        if page * 50 >= total or len(items) < 50:
            break
        page += 1

    print(f"[monte_carlo] {cat_key}: {len(products)} produtos")
    if len(products) < 3:
        print(f"[monte_carlo] WARNING: poucos produtos em {cat_key}")
    return products


async def scrape_all() -> list[dict]:
    all_products = []
    async with httpx.AsyncClient(follow_redirects=True, cookies=httpx.Cookies()) as client:
        await _init_session(client)
        for cat_key, cat_slug in CATEGORIES.items():
            try:
                products = await scrape_category(client, cat_key, cat_slug)
                all_products.extend(products)
            except Exception as e:
                print(f"[monte_carlo] FATAL {cat_key}: {e}")
    return all_products
