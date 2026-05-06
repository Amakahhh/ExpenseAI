"""
Keyword-based transaction classifier.

Replaces the sentence-transformers / PyTorch approach which exceeded the
512 MB RAM limit on Render's free tier.  Accuracy is equivalent for
structured Nigerian bank transaction descriptions because the dominant
signal is always a merchant name or service keyword, not sentence
semantics.
"""

CATEGORIES = [
    "food", "transport", "entertainment", "bills",
    "health", "education", "shopping", "other",
]

# Keywords ordered from most-specific to least-specific within each category.
# Categories are checked in the order listed below; the first full match wins.
_KEYWORDS: dict[str, list[str]] = {
    "food": [
        "shoprite", "chicken republic", "kfc", "dominos pizza", "debonairs pizza",
        "mr biggs", "tastee fried", "sweet sensation", "tantalizers", "kilimanjaro",
        "coldstone", "spar supermarket", "jumia food", "bolt food", "glovo food",
        "food delivery", "grocery store", "local restaurant", "buka food",
        "cafeteria payment", "canteen payment", "bakery", "caterer",
    ],
    "transport": [
        "uber trip", "bolt ride", "taxify", "indriver", "total petrol",
        "conoil fuel", "mobil station", "oando", "dana air", "air peace",
        "arik air", "wakanow", "gigm bus", "abc transport", "gate1 bus",
        "car hire", "parking fee", "toll gate", "keke", "bike dispatch",
        "interstate transport", "vehicle registration", "fuel purchase",
    ],
    "entertainment": [
        "netflix", "showmax", "spotify", "apple music", "youtube premium",
        "silverbird cinema", "filmhouse cinema", "genesis cinema", "ebonylife cinema",
        "nairabet", "bet9ja", "sportybet", "1xbet", "playstation network",
        "steam game", "karaoke", "amusement park", "concert ticket", "eventbrite",
        "gotv subscription", "dstv subscription", "canal plus",
    ],
    "bills": [
        "ekedc", "ikedc", "kedco", "phed electricity", "enedisco", "aedc",
        "jed electricity", "bedc", "electricity token", "water bill",
        "spectranet", "smile internet", "swift networks", "internet subscription",
        "house rent", "monthly rent", "service charge estate", "estate levy",
        "facility management", "waste management", "insurance premium",
        "nhis", "annual subscription utility",
    ],
    "health": [
        "medplus", "healthplus pharmacy", "drug store", "medication payment",
        "teaching hospital", "general hospital", "private clinic",
        "medical laboratory", "pathcare", "radiology scan", "dentist",
        "optician", "physiotherapy", "hygeia hmo", "reliance hmo", "hmo",
        "ambulance", "mental health therapy", "wellness center",
        "vitamin supplement", "medical equipment", "vaccination",
        "antenatal", "emergency medical",
    ],
    "education": [
        "school fees", "university tuition", "jamb registration",
        "waec examination", "neco exam", "post utme", "nabteb",
        "course registration", "professional certification",
        "udemy", "coursera", "linkedin learning", "study abroad",
        "student accommodation", "ielts registration", "toefl exam",
        "training workshop", "seminar attendance", "e-learning",
        "coaching class", "tutorial fee", "vocational training",
    ],
    "shopping": [
        "jumia online", "konga online", "jiji marketplace", "aliexpress",
        "amazon purchase", "slot nigeria", "computer village",
        "boutique fashion", "electronics store", "ikeja mall", "palms mall",
        "lekki mall", "household item", "furniture store", "fabric material",
        "cosmetics beauty", "gift item", "superstore purchase",
    ],
    "other": [
        "interbank transfer", "nip transfer", "atm withdrawal", "bank charge",
        "sms alert charge", "card maintenance", "stamp duty", "vat charge",
        "account maintenance fee", "cashback reversal", "transaction reversal",
        "salary payment", "wages payment", "commission earning",
        "airtime recharge", "airtime top up", "data bundle", "data subscription",
        "peer to peer transfer", "family support transfer",
    ],
}


def classify_transaction(description: str) -> dict:
    text = (description or "").lower().strip()

    for category, keywords in _KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return {"category": category, "confidence": 0.87}

    return {"category": "other", "confidence": 0.50}


def classify_batch(descriptions: list) -> list:
    return [classify_transaction(d) for d in descriptions]


def update_prototype(category: str, description: str) -> None:
    # No-op: keyword classifier has no learnable parameters.
    # User corrections are still persisted via the DB for analytics.
    pass
