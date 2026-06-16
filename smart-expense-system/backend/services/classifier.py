"""
Nigerian bank transaction classifier – 3-pass approach.

  1. Brand lookup  — known merchant/brand substrings → category (longest match first)
  2. Phrase match  — curated descriptive phrases → category
  3. Token scoring — accumulate per-word evidence; pick highest-scored category
"""

import re
from collections import defaultdict

CATEGORIES = [
    "food", "transport", "entertainment", "bills",
    "health", "education", "shopping", "other",
]

# ── Pass 1: brand / merchant name lookup ──────────────────────────────────────
# Sorted longest-first so "jumia food" beats "jumia", "bolt food" beats "bolt", etc.
_BRANDS: list[tuple[str, str]] = sorted([
    # ── food ──────────────────────────────────────────────────────────────────
    ("the place restaurant",    "food"),
    ("debonairs pizza",         "food"),
    ("dominos pizza",           "food"),
    ("domino's pizza",          "food"),
    ("chicken republic",        "food"),
    ("sweet sensation",         "food"),
    ("mega chicken",            "food"),
    ("food concepts",           "food"),
    ("mama cass",               "food"),
    ("tasty way",               "food"),
    ("yellowchilli",            "food"),
    ("jumia food",              "food"),
    ("bolt food",               "food"),
    ("glovo food",              "food"),
    ("cold stone",              "food"),
    ("pizza hut",               "food"),
    ("burger king",             "food"),
    ("mr biggs",                "food"),
    ("mama put",                "food"),
    ("mr chef",                 "food"),
    ("shoprite",                "food"),
    ("coldstone",               "food"),
    ("dominos",                 "food"),
    ("domino's",                "food"),
    ("tantalizers",             "food"),
    ("tantalizer",              "food"),
    ("kilimanjaro",             "food"),
    ("barcelos",                "food"),
    ("toasties",                "food"),
    ("nandos",                  "food"),
    ("glovo",                   "food"),
    ("kfc",                     "food"),

    # ── transport ─────────────────────────────────────────────────────────────
    ("united nigeria airlines", "transport"),
    ("green africa airways",    "transport"),
    ("ethiopian airlines",      "transport"),
    ("overland airways",        "transport"),
    ("british airways",         "transport"),
    ("turkish airlines",        "transport"),
    ("peace mass transit",      "transport"),
    ("young shall grow",        "transport"),
    ("filling station",         "transport"),
    ("petrol station",          "transport"),
    ("total filling",           "transport"),
    ("total petrol",            "transport"),
    ("total fuel",              "transport"),
    ("forte oil",               "transport"),
    ("kenya airways",           "transport"),
    ("god is good",             "transport"),
    ("abc transport",           "transport"),
    ("air peace",               "transport"),
    ("dana air",                "transport"),
    ("arik air",                "transport"),
    ("ibom air",                "transport"),
    ("max air",                 "transport"),
    ("taxify",                  "transport"),
    ("indriver",                "transport"),
    ("gokada",                  "transport"),
    ("shuttlers",               "transport"),
    ("gigm",                    "transport"),
    ("oando",                   "transport"),
    ("conoil",                  "transport"),
    ("ardova",                  "transport"),
    ("nnpc",                    "transport"),
    ("uber",                    "transport"),
    ("bolt",                    "transport"),   # after "bolt food" due to sort

    # ── entertainment ─────────────────────────────────────────────────────────
    ("playstation network",     "entertainment"),
    ("playstation store",       "entertainment"),
    ("silverbird cinema",       "entertainment"),
    ("filmhouse cinema",        "entertainment"),
    ("genesis cinema",          "entertainment"),
    ("ebonylife cinema",        "entertainment"),
    ("ozone cinema",            "entertainment"),
    ("youtube premium",         "entertainment"),
    ("apple music",             "entertainment"),
    ("amazon prime",            "entertainment"),
    ("disney plus",             "entertainment"),
    ("disney+",                 "entertainment"),
    ("disneyplus",              "entertainment"),
    ("surebet247",              "entertainment"),
    ("betbonanza",              "entertainment"),
    ("parimatch",               "entertainment"),
    ("accessbet",               "entertainment"),
    ("silverbird",              "entertainment"),
    ("filmhouse",               "entertainment"),
    ("sportybet",               "entertainment"),
    ("nairabet",                "entertainment"),
    ("merrybet",                "entertainment"),
    ("betking",                 "entertainment"),
    ("bangbet",                 "entertainment"),
    ("audiomack",               "entertainment"),
    ("soundcloud",              "entertainment"),
    ("boomplay",                "entertainment"),
    ("netflix",                 "entertainment"),
    ("showmax",                 "entertainment"),
    ("spotify",                 "entertainment"),
    ("bet9ja",                  "entertainment"),
    ("betway",                  "entertainment"),
    ("msport",                  "entertainment"),
    ("1xbet",                   "entertainment"),
    ("xbox",                    "entertainment"),
    ("nintendo",                "entertainment"),

    # ── bills ─────────────────────────────────────────────────────────────────
    ("ikeja electric",          "bills"),
    ("eko electricity",         "bills"),
    ("kano electricity",        "bills"),
    ("phed electricity",        "bills"),
    ("bedc electricity",        "bills"),
    ("jed electricity",         "bills"),
    ("eedc enugu",              "bills"),
    ("jos electricity",         "bills"),
    ("ibadan disco",            "bills"),
    ("swift networks",          "bills"),
    ("smile internet",          "bills"),
    ("hygeia hmo",              "bills"),
    ("reliance hmo",            "bills"),
    ("leadway insurance",       "bills"),
    ("aiico insurance",         "bills"),
    ("mutual benefit",          "bills"),
    ("canal plus",              "bills"),
    ("aedc abuja",              "bills"),
    ("spectranet",              "bills"),
    ("enedisco",                "bills"),
    ("startimes",               "bills"),
    ("wakanet",                 "bills"),
    ("ekedc",                   "bills"),
    ("ikedc",                   "bills"),
    ("kedco",                   "bills"),
    ("ibedc",                   "bills"),
    ("tizeti",                  "bills"),
    ("ipnx",                    "bills"),
    ("phed",                    "bills"),
    ("bedc",                    "bills"),
    ("aedc",                    "bills"),
    ("eedc",                    "bills"),
    ("ntel",                    "bills"),
    ("nhis",                    "bills"),
    ("dstv",                    "bills"),
    ("gotv",                    "bills"),
    ("hitv",                    "bills"),
    ("lawma",                   "bills"),

    # ── health ────────────────────────────────────────────────────────────────
    ("reddington hospital",     "health"),
    ("clina-lancet",            "health"),
    ("swiss pharma",            "health"),
    ("eko hospital",            "health"),
    ("healthplus",              "health"),
    ("drugstoc",                "health"),
    ("evercare",                "health"),
    ("pathcare",                "health"),
    ("medplus",                 "health"),
    ("synlab",                  "health"),
    ("emzor",                   "health"),

    # ── education ─────────────────────────────────────────────────────────────
    ("linkedin learning",       "education"),
    ("alison course",           "education"),
    ("pluralsight",             "education"),
    ("skillshare",              "education"),
    ("treehouse",               "education"),
    ("coursera",                "education"),
    ("udemy",                   "education"),
    ("edx",                     "education"),

    # ── shopping ──────────────────────────────────────────────────────────────
    ("computer village",        "shopping"),
    ("slot nigeria",            "shopping"),
    ("slot phones",             "shopping"),
    ("aliexpress",              "shopping"),
    ("payporte",                "shopping"),
    ("dealdey",                 "shopping"),
    ("pointek",                 "shopping"),
    ("fouani",                  "shopping"),
    ("jumia",                   "shopping"),   # after "jumia food" due to sort
    ("amazon",                  "shopping"),   # after "amazon prime" due to sort
    ("konga",                   "shopping"),
    ("shein",                   "shopping"),
    ("temu",                    "shopping"),
    ("jiji",                    "shopping"),
    ("slot",                    "shopping"),
], key=lambda pair: -len(pair[0]))


# ── Pass 2: descriptive phrase match (substring) ──────────────────────────────
_PHRASES: dict[str, list[str]] = {
    "food": [
        "food court", "food store", "food mart", "food hub", "food delivery",
        "food purchase", "meal delivery", "fast food",
        "grocery store", "grocery shop", "groceries",
        "supermarket", "mini mart", "provisions store", "convenience store",
        "restaurant", "eatery", "cafeteria", "canteen", "catering",
        "bakery", "confectionery", "cake shop", "pastry shop",
        "suya spot", "suya", "shawarma", "sharwarma", "peppersoup",
        "local restaurant", "snack bar", "chops bar",
        "fish market", "meat market", "foodstuff market", "foodstuff",
        "farm fresh", "morning fresh", "green basket",
    ],
    "transport": [
        "bolt ride", "bolt trip", "bolt car",
        "fuel station", "fuel purchase", "petrol purchase", "diesel purchase",
        "fuel top up", "fuel topup",
        "flight ticket", "airline ticket", "bus ticket", "interstate transport",
        "motor park", "highway transport",
        "car hire", "vehicle hire", "car rental",
        "toll gate", "toll fee", "car park", "parking fee",
        "bike dispatch", "dispatch rider",
        "auto mechanic", "car wash", "vehicle service",
        "spare part", "auto parts", "engine oil",
        "tyre purchase", "vehicle registration",
        "transport fare", "bus fare",
    ],
    "entertainment": [
        "sports betting", "bet deposit", "bet withdrawal",
        "cinema ticket", "movie ticket", "concert ticket",
        "event ticket", "amusement park", "karaoke",
        "xbox game", "steam game", "game subscription",
        "youtube subscription", "streaming subscription",
    ],
    "bills": [
        "electricity token", "prepaid token", "power token", "meter token",
        "electricity bill", "electric bill", "light bill", "nepa bill",
        "electricity payment", "electricity recharge",
        "prepaid meter", "postpaid bill", "utility bill",
        "internet subscription", "broadband subscription", "wifi subscription",
        "internet data", "data bundle", "data plan", "data subscription", "data purchase",
        "mtn airtime", "airtel airtime", "glo airtime", "9mobile airtime", "etisalat airtime",
        "airtime recharge", "airtime purchase", "airtime topup", "airtime top up",
        "vtu airtime", "airtime vtu", "airtime transfer",
        "mtn data", "airtel data", "glo data", "9mobile data",
        "mtn subscription", "airtel subscription", "glo subscription",
        "cable tv", "cable subscription", "cable tv subscription",
        "water bill", "water rate", "water board",
        "house rent", "monthly rent", "annual rent", "rent payment",
        "service charge", "estate levy", "facility management",
        "ground rent", "tenement rate",
        "insurance premium", "life insurance", "car insurance", "hmo premium",
        "health insurance", "hmo subscription",
        "waste management", "sanitation levy",
    ],
    "health": [
        "pharmacy store", "drug store", "chemist",
        "medication purchase", "medicine purchase", "drug payment", "drugs purchase",
        "teaching hospital", "general hospital", "private hospital",
        "private clinic", "medical center", "health center",
        "maternity home", "specialist hospital",
        "medical laboratory", "radiology scan", "mri scan", "ultrasound scan",
        "blood test", "lab test", "medical test",
        "dental clinic", "eye clinic", "optometry",
        "physiotherapy", "physiotherapist",
        "health plan", "health maintenance",
        "ambulance", "emergency medical",
        "vitamin supplement", "supplement purchase",
        "wellness center", "gym membership", "fitness center", "fitness club",
        "vaccination", "immunization", "antenatal",
        "mental health", "counseling session",
        "doctor consultation", "medical consultation", "hospital bill",
    ],
    "education": [
        "jamb registration", "jamb payment", "jamb utme",
        "waec examination", "waec registration",
        "neco exam", "nabteb exam", "post utme",
        "school fees", "school fee payment", "school fee",
        "tuition payment", "tuition fee",
        "university fees", "polytechnic fees", "college fees",
        "course registration", "exam registration", "admission fee",
        "student hostel", "student accommodation",
        "professional certification", "professional exam",
        "online course", "e-learning", "distance learning",
        "training workshop", "seminar fee", "conference registration",
        "coaching class", "tutorial fee", "lesson payment", "vocational training",
        "study abroad", "ielts registration", "toefl exam",
    ],
    "shopping": [
        "online shopping", "online store", "online purchase",
        "electronics store", "phone purchase", "laptop purchase", "gadget store",
        "clothing store", "shoe store", "footwear",
        "fashion house", "fabric purchase", "apparel store",
        "furniture store", "home appliance", "household item", "home decor",
        "beauty store", "skincare", "hair extension", "makeup store",
        "cosmetics purchase", "perfume purchase",
        "retail store", "department store",
        "gift purchase", "souvenir", "merchandise",
        "boutique fashion",
    ],
    "other": [
        "interbank transfer", "nip transfer", "neft transfer",
        "rtgs transfer", "funds transfer",
        "bank charge", "sms alert charge", "card maintenance fee",
        "stamp duty", "vat charge", "cot charge",
        "account maintenance", "annual fee", "withholding tax",
        "atm withdrawal", "cash withdrawal", "pos withdrawal",
        "transaction reversal", "cashback reversal", "failed transaction",
        "salary payment", "wages payment", "payroll", "dividend payment",
    ],
}

# ── Pass 3: scored token lookup ───────────────────────────────────────────────
# Score = how strongly the word signals the category (0–1).
# Classifier accumulates scores and picks the winner if total >= 0.60.
_SCORES: dict[str, dict[str, float]] = {
    "food": {
        "food": 0.80, "restaurant": 0.90, "eatery": 0.90, "cafeteria": 0.85,
        "canteen": 0.85, "catering": 0.75, "grocery": 0.85, "groceries": 0.85,
        "foodstuff": 0.90, "provisions": 0.75, "bakery": 0.85,
        "shawarma": 0.95, "sharwarma": 0.95, "suya": 0.95,
        "pizza": 0.80, "burger": 0.80, "chicken": 0.55, "snack": 0.65,
        "cafe": 0.70, "supermarket": 0.80, "buka": 0.90, "chops": 0.70,
        "smoothie": 0.80, "pastry": 0.80, "confectionery": 0.85,
        "shoprite": 0.95, "spar": 0.90, "kfc": 0.95, "dominos": 0.95,
    },
    "transport": {
        "uber": 0.95, "bolt": 0.80, "taxify": 0.95, "indriver": 0.95,
        "gokada": 0.95, "shuttlers": 0.95,
        "petrol": 0.90, "diesel": 0.90, "fuel": 0.85,
        "oando": 0.95, "conoil": 0.95, "ardova": 0.95, "nnpc": 0.90,
        "filling": 0.80, "airline": 0.90, "airways": 0.90, "flight": 0.85,
        "gigm": 0.95, "danfo": 0.80, "keke": 0.80, "okada": 0.80,
        "parking": 0.80, "toll": 0.80, "tollgate": 0.90,
        "mechanic": 0.85, "tyre": 0.85, "tyres": 0.85,
        "transport": 0.70, "logistics": 0.60,
    },
    "entertainment": {
        "netflix": 0.99, "showmax": 0.99, "spotify": 0.99, "boomplay": 0.99,
        "audiomack": 0.95, "soundcloud": 0.95,
        "bet9ja": 0.99, "sportybet": 0.99, "nairabet": 0.99,
        "betway": 0.99, "1xbet": 0.99, "betking": 0.99, "bangbet": 0.99,
        "cinema": 0.90, "silverbird": 0.95, "filmhouse": 0.95,
        "playstation": 0.95, "gaming": 0.85, "betting": 0.85,
        "entertainment": 0.80, "streaming": 0.80, "betting": 0.90,
        "casino": 0.90, "lottery": 0.85,
    },
    "bills": {
        "ekedc": 0.99, "ikedc": 0.99, "phed": 0.99, "aedc": 0.99,
        "bedc": 0.99, "kedco": 0.99, "enedisco": 0.99, "ibedc": 0.99,
        "spectranet": 0.99, "tizeti": 0.99, "ipnx": 0.99,
        "gotv": 0.99, "dstv": 0.99, "startimes": 0.99,
        "electricity": 0.90, "airtime": 0.90, "vtu": 0.90,
        "rent": 0.80, "landlord": 0.85,
        "internet": 0.70, "broadband": 0.80, "data": 0.60,
        "utility": 0.75, "token": 0.70, "recharge": 0.75,
        "prepaid": 0.70, "postpaid": 0.75, "bill": 0.65,
        "subscription": 0.55, "insurance": 0.65, "premium": 0.55,
        "cable": 0.70, "wifi": 0.75,
    },
    "health": {
        "pharmacy": 0.95, "pharmacist": 0.95, "chemist": 0.90, "dispensary": 0.90,
        "hospital": 0.90, "clinic": 0.85, "medical": 0.75, "doctor": 0.80,
        "laboratory": 0.80, "pathcare": 0.95, "dentist": 0.90,
        "optician": 0.90, "physiotherapy": 0.90,
        "medication": 0.90, "medicine": 0.90, "drugs": 0.85, "drug": 0.80,
        "vaccine": 0.90, "vaccination": 0.90, "surgery": 0.90,
        "scan": 0.70, "ultrasound": 0.90, "mri": 0.90,
        "health": 0.60, "wellness": 0.70, "gym": 0.65, "fitness": 0.70,
    },
    "education": {
        "jamb": 0.99, "waec": 0.99, "neco": 0.99, "nabteb": 0.99,
        "udemy": 0.99, "coursera": 0.99, "skillshare": 0.99,
        "ielts": 0.99, "toefl": 0.99, "gmat": 0.95,
        "tuition": 0.90, "tutorial": 0.85, "school": 0.80,
        "university": 0.85, "polytechnic": 0.85, "college": 0.65,
        "education": 0.80, "exam": 0.70, "admission": 0.80,
        "training": 0.65, "seminar": 0.80, "certification": 0.80,
        "lesson": 0.80, "academy": 0.80, "institute": 0.65,
    },
    "shopping": {
        "jumia": 0.99, "konga": 0.99, "jiji": 0.95,
        "aliexpress": 0.99, "amazon": 0.90, "shein": 0.99, "temu": 0.99,
        "slot": 0.85, "pointek": 0.95, "fouani": 0.95,
        "boutique": 0.90, "clothing": 0.85, "apparel": 0.85,
        "fashion": 0.75, "cosmetics": 0.85, "beauty": 0.70,
        "skincare": 0.85, "makeup": 0.85, "perfume": 0.85,
        "mall": 0.65, "shopping": 0.70, "retail": 0.70,
        "furniture": 0.80, "appliance": 0.80, "gadget": 0.80,
        "electronics": 0.75, "accessories": 0.70,
    },
}

# Strip these common filler words before token scoring so they don't dilute signals.
_NOISE = frozenset({
    "via", "to", "from", "at", "by", "for", "the", "and", "or",
    "of", "a", "an", "on", "in", "with", "per", "rev", "ref",
    "nip", "pos", "atm", "web", "ussd", "dd", "so", "dr", "cr",
    "bank", "transfer", "payment", "purchase", "pay", "debit",
    "credit", "transaction", "mobile", "online", "lagos", "abuja",
    "port", "harcourt", "kano", "ibadan", "benin", "enugu", "kaduna",
    "ng", "ltd", "plc", "nig", "nigeria", "limited",
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
    # common Nigerian bank channels / prefixes that carry no category signal
    "gtb", "gtbank", "access", "zenith", "uba", "fcmb", "stanbic",
    "sterling", "union", "heritage", "wema", "opay", "palmpay",
    "moniepoint", "kuda",
})

# Split on whitespace, slashes, hyphens, underscores, punctuation, and asterisks
_TOKEN_SPLIT = re.compile(r"[\s/\-_,\.;:@#\(\)\[\]\*\+\&]+")

_SCORE_THRESHOLD = 0.60   # minimum accumulated score to accept a category


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t and t not in _NOISE]


def classify_transaction(description: str) -> dict:
    text = (description or "").lower().strip()
    if not text:
        return {"category": "other", "confidence": 0.45}

    # ── Pass 1: brand lookup (longest match first prevents false partial hits) ─
    for brand, category in _BRANDS:
        if brand in text:
            return {"category": category, "confidence": 0.92}

    # ── Pass 2: phrase match ──────────────────────────────────────────────────
    for category, phrases in _PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                return {"category": category, "confidence": 0.88}

    # ── Pass 3: token scoring ────────────────────────────────────────────────
    toks = _tokens(text)
    cat_scores: dict[str, float] = defaultdict(float)
    for tok in toks:
        for cat, word_map in _SCORES.items():
            if tok in word_map:
                cat_scores[cat] += word_map[tok]

    if cat_scores:
        best = max(cat_scores, key=cat_scores.__getitem__)
        score = cat_scores[best]
        if score >= _SCORE_THRESHOLD:
            # Normalise score to a confidence in 0.65–0.88
            confidence = round(min(0.88, 0.65 + score * 0.15), 2)
            return {"category": best, "confidence": confidence}

    return {"category": "other", "confidence": 0.45}


def classify_batch(descriptions: list) -> list:
    return [classify_transaction(d) for d in descriptions]


def update_prototype(category: str, description: str) -> None:
    # No-op: keyword classifier has no learnable parameters.
    pass
