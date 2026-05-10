"""Run once to seed data/history.json and data/summaries/daily_summary.json with 90 days of realistic sample data."""
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
random.seed(42)

BASE = {
    "vivara_aneis_ouro":        3200.0,
    "vivara_aneis_prata":        480.0,
    "vivara_pulseiras_ouro":    1850.0,
    "vivara_pulseiras_prata":    390.0,
    "vivara_colares_ouro":      2200.0,
    "vivara_colares_prata":      520.0,
    "vivara_brincos_ouro":       990.0,
    "vivara_brincos_prata":      315.0,
    "vivara_relogios":          4300.0,
    "pandora_moments":           275.0,
    "pandora_pulseiras":         520.0,
    "pandora_colares":           460.0,
    "pandora_aneis":             390.0,
    "pandora_brincos":           310.0,
    "monte_carlo_aneis":         190.0,
    "monte_carlo_pulseiras":     155.0,
    "monte_carlo_colares":       175.0,
    "monte_carlo_brincos":       120.0,
}

TRENDS = {
    "vivara_aneis_ouro":        0.0008,
    "vivara_aneis_prata":       0.0004,
    "vivara_pulseiras_ouro":    0.0009,
    "vivara_pulseiras_prata":   0.0003,
    "vivara_colares_ouro":      0.0007,
    "vivara_colares_prata":     0.0003,
    "vivara_brincos_ouro":      0.0006,
    "vivara_brincos_prata":     0.0002,
    "vivara_relogios":          0.0004,
    "pandora_moments":          0.0002,
    "pandora_pulseiras":        0.0002,
    "pandora_colares":          0.0002,
    "pandora_aneis":            0.0002,
    "pandora_brincos":          0.0001,
    "monte_carlo_aneis":        0.0001,
    "monte_carlo_pulseiras":    0.0001,
    "monte_carlo_colares":      0.0001,
    "monte_carlo_brincos":      0.0000,
}

N_DAYS = 90
start  = date(2026, 2, 9)
dates  = [start + timedelta(days=i) for i in range(N_DAYS)]

series_prices: dict[str, list[float]] = {k: [] for k in BASE}
for i in range(N_DAYS):
    for k, base in BASE.items():
        noise = random.gauss(0, 0.003)
        price = base * (1 + TRENDS.get(k, 0) * i + noise)
        series_prices[k].append(round(price, 2))

ALL_SERIES = [
    ("vivara_aneis_ouro",       "Vivara — Anéis Ouro",            "vivara", "aneis",            "ouro"),
    ("vivara_aneis_prata",      "Vivara — Anéis Prata",           "vivara", "aneis",            "prata"),
    ("vivara_pulseiras_ouro",   "Vivara — Pulseiras Ouro",             "vivara", "pulseiras",        "ouro"),
    ("vivara_pulseiras_prata",  "Vivara — Pulseiras Prata",            "vivara", "pulseiras",        "prata"),
    ("vivara_colares_ouro",     "Vivara — Colares Ouro",               "vivara", "colares_pingentes","ouro"),
    ("vivara_colares_prata",    "Vivara — Colares Prata",              "vivara", "colares_pingentes","prata"),
    ("vivara_brincos_ouro",     "Vivara — Brincos Ouro",               "vivara", "brincos",          "ouro"),
    ("vivara_brincos_prata",    "Vivara — Brincos Prata",              "vivara", "brincos",          "prata"),
    ("vivara_relogios",         "Vivara — Relógios",              "vivara", "relogios",         "all"),
    ("pandora_moments",         "Pandora — Moments",                   "pandora","moments",           "all"),
    ("pandora_pulseiras",       "Pandora — Pulseiras",                 "pandora","pulseiras",         "all"),
    ("pandora_colares",         "Pandora — Colares",                   "pandora","colares",           "all"),
    ("pandora_aneis",           "Pandora — Anéis",                "pandora","aneis",             "all"),
    ("pandora_brincos",         "Pandora — Brincos",                   "pandora","brincos",           "all"),
    ("monte_carlo_aneis",       "Monte Carlo — Anéis",            "monte_carlo","aneis",         "all"),
    ("monte_carlo_pulseiras",   "Monte Carlo — Pulseiras",             "monte_carlo","pulseiras",     "all"),
    ("monte_carlo_colares",     "Monte Carlo — Colares",               "monte_carlo","colares",       "all"),
    ("monte_carlo_brincos",     "Monte Carlo — Brincos",               "monte_carlo","brincos",       "all"),
]

# Build history.json
all_date_strs = [d.isoformat() for d in dates]
series_out = {}
for key, label, brand, cat, mat in ALL_SERIES:
    prices = series_prices[key]
    base_p = prices[0]
    series_out[key] = {
        "label": label, "brand": brand, "category": cat, "material": mat,
        "prices": prices,
        "index":  [round(p / base_p * 100, 2) for p in prices],
    }

history = {
    "generated_at": "2026-05-09T06:00:00Z",
    "baseline_date": all_date_strs[0],
    "dates": all_date_strs,
    "series": series_out,
}

hist_file = ROOT / "data" / "history.json"
hist_file.parent.mkdir(parents=True, exist_ok=True)
hist_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"history.json written: {len(all_date_strs)} dates, {len(series_out)} series")

# Build daily_summary.json (last 5 days for reference)
VIVARA_COUNTS = {"aneis": (45,90), "pulseiras": (32,68), "colares_pingentes": (55,92), "brincos": (60,105), "relogios": (18,)}
summaries = []
for i in range(N_DAYS - 5, N_DAYS):
    d = dates[i].isoformat()
    vivara_brand = {}
    for cat, counts in VIVARA_COUNTS.items():
        if cat == "relogios":
            vivara_brand[cat] = {"all": {"avg_price": series_prices["vivara_relogios"][i], "median": series_prices["vivara_relogios"][i], "count": counts[0]}}
        else:
            key_o = f"vivara_{cat.replace('colares_pingentes','colares')}_ouro"
            key_p = f"vivara_{cat.replace('colares_pingentes','colares')}_prata"
            vivara_brand[cat] = {
                "ouro":  {"avg_price": series_prices[key_o][i], "median": series_prices[key_o][i], "count": counts[0]},
                "prata": {"avg_price": series_prices[key_p][i], "median": series_prices[key_p][i], "count": counts[1]},
            }

    pandora_brand = {
        cat: {"all": {"avg_price": series_prices[f"pandora_{cat}"][i], "median": series_prices[f"pandora_{cat}"][i], "count": 80}}
        for cat in ["moments", "pulseiras", "colares", "aneis", "brincos"]
    }
    mc_brand = {
        cat: {"all": {"avg_price": series_prices[f"monte_carlo_{cat}"][i], "median": series_prices[f"monte_carlo_{cat}"][i], "count": 50}}
        for cat in ["aneis", "pulseiras", "colares", "brincos"]
    }

    summaries.append({"date": d, "brands": {"vivara": vivara_brand, "pandora": pandora_brand, "monte_carlo": mc_brand}})

summ_file = ROOT / "data" / "summaries" / "daily_summary.json"
summ_file.parent.mkdir(parents=True, exist_ok=True)
summ_file.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"daily_summary.json written: {len(summaries)} entries")
