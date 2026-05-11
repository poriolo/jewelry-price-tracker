import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SUMMARIES_FILE = ROOT / "data" / "summaries" / "daily_summary.json"
HISTORY_FILE = ROOT / "data" / "history.json"
RAW_DIR = ROOT / "data" / "raw"

MIN_PRODUCTS = 3  # minimum count to consider an avg trustworthy


def _remove_outliers(prices: list[float]) -> list[float]:
    if len(prices) < 4:
        return prices
    q1 = statistics.quantiles(prices, n=4)[0]
    q3 = statistics.quantiles(prices, n=4)[2]
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [p for p in prices if lo <= p <= hi and p >= 10]
    return filtered if filtered else prices


def _stats(prices: list[float]) -> dict:
    clean = _remove_outliers(prices)
    if not clean:
        return {"avg_price": None, "median": None, "count": 0}
    return {
        "avg_price": round(statistics.mean(clean), 2),
        "median": round(statistics.median(clean), 2),
        "count": len(clean),
    }


def compute_daily_entry(date_str: str) -> dict:
    entry = {"date": date_str, "brands": {}}

    for brand_dir in RAW_DIR.iterdir():
        raw_file = brand_dir / f"{date_str}.json"
        if not raw_file.exists():
            continue
        data = json.loads(raw_file.read_text(encoding="utf-8"))
        brand = data["brand"]
        products = [p for p in data["products"] if p.get("in_stock", True) and p.get("price")]

        brand_entry = {}
        for p in products:
            cat = p["category"]
            mat = p.get("material")  # None for non-Vivara brands

            if brand == "vivara":
                mat_key = mat if mat in ("ouro", "prata") else None
                if mat_key is None:
                    mat_key = "outros"
                bucket = brand_entry.setdefault(cat, {}).setdefault(mat_key, [])
            else:
                bucket = brand_entry.setdefault(cat, {}).setdefault("all", [])

            bucket.append(p["price"])

        # convert price lists to stats dicts
        brand_summary = {}
        for cat, mats in brand_entry.items():
            brand_summary[cat] = {mat: _stats(prices) for mat, prices in mats.items()}

        entry["brands"][brand] = brand_summary

    return entry


def append_daily_summary(date_str: str) -> None:
    SUMMARIES_FILE.parent.mkdir(parents=True, exist_ok=True)

    if SUMMARIES_FILE.exists():
        summaries = json.loads(SUMMARIES_FILE.read_text(encoding="utf-8-sig"))
    else:
        summaries = []

    # remove existing entry for same date (idempotent re-run)
    summaries = [s for s in summaries if s["date"] != date_str]
    summaries.append(compute_daily_entry(date_str))
    summaries.sort(key=lambda s: s["date"])

    SUMMARIES_FILE.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[aggregator] appended summary for {date_str}")


# ---------------------------------------------------------------------------
# history.json builder
# ---------------------------------------------------------------------------

VIVARA_SERIES = [
    ("vivara_aneis_ouro",          "Vivara — Anéis Ouro",            "vivara", "aneis",            "ouro"),
    ("vivara_aneis_prata",         "Vivara — Anéis Prata",           "vivara", "aneis",            "prata"),
    ("vivara_pulseiras_ouro",      "Vivara — Pulseiras Ouro",        "vivara", "pulseiras",         "ouro"),
    ("vivara_pulseiras_prata",     "Vivara — Pulseiras Prata",       "vivara", "pulseiras",         "prata"),
    ("vivara_colares_ouro",        "Vivara — Colares Ouro",          "vivara", "colares_pingentes", "ouro"),
    ("vivara_colares_prata",       "Vivara — Colares Prata",         "vivara", "colares_pingentes", "prata"),
    ("vivara_brincos_ouro",        "Vivara — Brincos Ouro",          "vivara", "brincos",           "ouro"),
    ("vivara_brincos_prata",       "Vivara — Brincos Prata",         "vivara", "brincos",           "prata"),
    ("vivara_relogios",            "Vivara — Relógios",              "vivara", "relogios",          "all"),
]

OTHER_SERIES = [
    ("pandora_moments",            "Pandora — Moments",              "pandora",      "moments",    "all"),
    ("pandora_pulseiras",          "Pandora — Pulseiras",            "pandora",      "pulseiras",  "all"),
    ("pandora_colares",            "Pandora — Colares",              "pandora",      "colares",    "all"),
    ("pandora_aneis",              "Pandora — Anéis",                "pandora",      "aneis",      "all"),
    ("pandora_brincos",            "Pandora — Brincos",              "pandora",      "brincos",    "all"),
    ("monte_carlo_aneis",          "Monte Carlo — Anéis",            "monte_carlo",  "aneis",      "all"),
    ("monte_carlo_pulseiras",      "Monte Carlo — Pulseiras",        "monte_carlo",  "pulseiras",  "all"),
    ("monte_carlo_colares",        "Monte Carlo — Colares",          "monte_carlo",  "colares",    "all"),
    ("monte_carlo_brincos",        "Monte Carlo — Brincos",          "monte_carlo",  "brincos",    "all"),
]

ALL_SERIES = VIVARA_SERIES + OTHER_SERIES


def _get_avg(summary_entry: dict, brand: str, cat: str, mat: str) -> float | None:
    try:
        return summary_entry["brands"][brand][cat][mat]["avg_price"]
    except KeyError:
        return None


def rebuild_history() -> None:
    if not SUMMARIES_FILE.exists():
        print("[aggregator] no summaries yet, skipping history rebuild")
        return

    summaries = json.loads(SUMMARIES_FILE.read_text(encoding="utf-8"))
    dates = [s["date"] for s in summaries]

    series_data: dict[str, list] = {key: [] for key, *_ in ALL_SERIES}
    series_index: dict[str, list] = {key: [] for key, *_ in ALL_SERIES}
    baselines: dict[str, float | None] = {key: None for key, *_ in ALL_SERIES}

    for s in summaries:
        for key, label, brand, cat, mat in ALL_SERIES:
            avg = _get_avg(s, brand, cat, mat)
            series_data[key].append(avg)
            if baselines[key] is None and avg is not None:
                baselines[key] = avg
            if avg is not None and baselines[key]:
                series_index[key].append(round(avg / baselines[key] * 100, 2))
            else:
                series_index[key].append(None)

    history = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_date": dates[0] if dates else None,
        "dates": dates,
        "series": {
            key: {
                "label": label,
                "brand": brand,
                "category": cat,
                "material": mat,
                "prices": series_data[key],
                "index": series_index[key],
            }
            for key, label, brand, cat, mat in ALL_SERIES
        },
    }

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[aggregator] rebuilt history.json with {len(dates)} dates")
