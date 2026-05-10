OURO_KEYWORDS = [
    "ouro amarelo", "ouro branco", "ouro rosé", "ouro rose",
    "ouro 18k", "ouro 14k", "ouro 10k", "18k", "14k", "10k",
    "ouro", "gold",
]

PRATA_KEYWORDS = [
    "prata 925", "prata esterlina", "sterling silver",
    "prata ródio", "prata", "silver",
]

OUTROS_KEYWORDS = [
    "aço", "titanio", "titânio", "couro", "borracha", "inox",
]


def detect_material(name: str, description: str = "") -> str | None:
    text = (name + " " + description).lower()
    for kw in OURO_KEYWORDS:
        if kw in text:
            return "ouro"
    for kw in PRATA_KEYWORDS:
        if kw in text:
            return "prata"
    return None
