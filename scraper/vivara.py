"""
Vivara scraper — VTEX Intelligent Search API.
Inicializa sessão na homepage para obter cookies VTEX antes de chamar a API.
"""
import asyncio
import json
import random

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from material_detector import detect_material

BASE_URL = "https://www.vivara.com.br"
SEARCH_URL = f"{BASE_URL}/_v/api/intelligent-search/product_search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

BRAND = "vivara"

CATEGORIES = {
    "aneis":             "aneis",
    "pulseiras":         "pulseiras",
    "colares_pingentes": "colares-e-pingentes",
    "brincos":           "brincos",
    "relogios":          "relogios",
}


async def _init_session(client: httpx.AsyncClient) -> None:
    """Visita a homepage para obter cookies de sessão VTEX."""
    try:
        resp = await client.get(BASE_URL, headers={**HEADERS, "Accept": "text/html"}, timeout=15)
        print(f"[vivara] session init: {resp.status_code}, cookies: {list(resp.cookies.keys())}")
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        print(f"[vivara] session init warning: {e}")


def _parse_price(item: dict) -> tuple[float | None, float | None]:
    # Try priceRange (Intelligent Search format)
    try:
        pr = item.get("priceRange", {})
        price = pr.get("sellingPrice", {}).get("lowPrice")
        list_price = pr.get("listPrice", {}).get("lowPrice")
        if price:
            return float(price), float(list_price) if list_price else None
    except Exception:
        pass
    # Try items[0].sellers[0].commertialOffer (Catalog format)
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
    print(f"[vivara] GET {url} page={page} → {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    # debug: print structure keys
    if isinstance(data, dict):
        print(f"[vivara] response keys: {list(data.keys())}")
        products = data.get("products", [])
        print(f"[vivara] products in response: {len(products)}")
    elif isinstance(data, list):
        print(f"[vivara] response is list, len={len(data)}")
    return data


async def scrape_category(client: httpx.AsyncClient, cat_key: str, cat_slug: str) -> list[dict]:
    products = []
    page = 1

    while True:
        try:
            data = await _fetch_page(client, cat_slug, page)
        except Exception as e:
            print(f"[vivara] ERROR page {page} of {cat_key}: {e}")
            break

        # Handle both dict (Intelligent Search) and list (Catalog API) responses
        if isinstance(data, list):
            items = data
        else:
            items = data.get("products", [])

        if not items:
            print(f"[vivara] no items on page {page} for {cat_key}, stopping")
            break

        for item in items:
            name = item.get("productName", "")
            price, original_price = _parse_price(item)
            if not price:
                continue
            link = item.get("link", "")
            url = BASE_URL + link if link.startswith("/") else link
            products.append({
                "id": f"vivara-{cat_key}-{item.get('productId', abs(hash(name)))}",
                "name": name,
                "category": cat_key,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": detect_material(name),
                "in_stock": True,
            })

        pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
        total = pagination.get("count", 0)
        if isinstance(data, list) and len(data) < 50:
            break
        if isinstance(data, dict) and (page * 50 >= total or len(items) < 50):
            break
        page += 1

    print(f"[vivara] {cat_key}: {len(products)} produtos")
    if len(products) < 3:
        print(f"[vivara] WARNING: poucos produtos em {cat_key}")
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
                print(f"[vivara] FATAL {cat_key}: {e}")
    return all_products
