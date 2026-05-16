"""
Pandora scraper — VTEX Catalog Search API com IDs de categoria.
IDs: moments=2, braceletes=3, aneis=4, brincos=5, colares=6
"""
import asyncio
import random

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://www.pandorajoias.com.br"
SEARCH_URL = f"{BASE_URL}/api/catalog_system/pub/products/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

BRAND = "pandora"

CATEGORY_IDS = {
    "moments":   2,
    "pulseiras": 3,
    "aneis":     4,
    "brincos":   5,
    "colares":   6,
}


async def _init_session(client: httpx.AsyncClient) -> None:
    try:
        resp = await client.get(BASE_URL, headers={**HEADERS, "Accept": "text/html"}, timeout=15)
        print(f"[pandora] session init: {resp.status_code}, cookies: {list(resp.cookies.keys())}")
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        print(f"[pandora] session init warning: {e}")


def _parse_price(item: dict) -> tuple[float | None, float | None]:
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
async def _fetch_page(client: httpx.AsyncClient, cat_id: int, offset: int) -> list:
    await asyncio.sleep(random.uniform(1.5, 3.0))
    resp = await client.get(
        SEARCH_URL,
        params={"fq": f"C:{cat_id}", "_from": offset, "_to": offset + 49},
        headers={**HEADERS, "Referer": BASE_URL},
        timeout=20,
    )
    print(f"[pandora] GET catalog fq=C:{cat_id} offset={offset} → {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    print(f"[pandora] response type={type(data).__name__}, len={len(data) if isinstance(data, list) else 'n/a'}")
    return data if isinstance(data, list) else []


async def scrape_category(client: httpx.AsyncClient, cat_key: str, cat_id: int) -> list[dict]:
    products = []
    offset = 0

    while True:
        try:
            items = await _fetch_page(client, cat_id, offset)
        except Exception as e:
            print(f"[pandora] ERROR offset {offset} of {cat_key}: {e}")
            break

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
                "id": f"pandora-{cat_key}-{item.get('productId', abs(hash(name)))}",
                "name": name,
                "category": cat_key,
                "price": price,
                "original_price": original_price,
                "url": url,
                "material": None,
                "in_stock": True,
            })

        if len(items) < 50:
            break
        offset += 50

    print(f"[pandora] {cat_key}: {len(products)} produtos")
    if len(products) < 3:
        print(f"[pandora] WARNING: poucos produtos em {cat_key}")
    return products


async def scrape_all() -> list[dict]:
    all_products = []
    async with httpx.AsyncClient(follow_redirects=True, cookies=httpx.Cookies()) as client:
        await _init_session(client)
        for cat_key, cat_id in CATEGORY_IDS.items():
            try:
                products = await scrape_category(client, cat_key, cat_id)
                all_products.extend(products)
            except Exception as e:
                print(f"[pandora] FATAL {cat_key}: {e}")
    return all_products
