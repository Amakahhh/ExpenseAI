"""
Keyword-based Nigerian bank transaction classifier.

Two-pass approach:
  1. Phrase match — check if any keyword phrase appears anywhere in the description.
  2. Token match — split description into word tokens, check against a set of
     high-precision single words that are unambiguous category signals.

Categories are checked in priority order; the first match wins.
"""

import re

CATEGORIES = [
    "food", "transport", "entertainment", "bills",
    "health", "education", "shopping", "other",
]

# ── Pass 1: Phrase keywords (substring match, lower-cased) ──────────────────
# Longer / more specific phrases first within each list to reduce false hits.
_PHRASES: dict[str, list[str]] = {
    "food": [
        # Chains & branded restaurants
        "chicken republic", "tastee fried", "sweet sensation",
        "mr biggs", "debonairs pizza", "dominos pizza", "domino's",
        "kilimanjaro", "cold stone", "coldstone", "mega chicken",
        "mama cass", "food concepts", "tantalizer",
        "yahuza suya", "mr chef", "tasty way",
        # Fast food keywords
        "shoprite", "kfc", "pizza hut", "burger king", "subway",
        "spar", "jumia food", "bolt food", "glovo food",
        # General food descriptors
        "restaurant", "eatery", "cafeteria", "canteen", "catering",
        "grocery", "foodstuff", "provisions store",
        "food court", "food store", "food mart",
        "bakery", "confectionery", "cake shop",
        "supermarket", "mini mart", "convenience store",
        "suya", "shawarma", "sharwarma", "peppersoup",
        "buka", "mama put", "local restaurant",
        "fish market", "meat market", "foodstuff market",
        "snack", "chops bar", "eat right", "bite",
        "pizza", "burger", "chicken wings", "fried rice",
        "food delivery", "meal delivery",
        "grocery store", "green basket", "farm fresh",
        "morning fresh", "food hub",
    ],
    "transport": [
        # Ride-hailing
        "uber trip", "uber ride", "uber eats",
        "bolt ride", "bolt car", "taxify ride",
        "indriver trip", "rida trip", "gokada ride",
        # Petrol & fuel
        "filling station", "petrol station", "fuel station",
        "total petrol", "total filling", "total fuel",
        "conoil fuel", "mobil station", "oando station",
        "forte oil", "ardova fuel", "nnpc station",
        "fuel purchase", "petrol purchase", "diesel purchase",
        "fuel top up",
        # Airlines
        "air peace", "dana air", "arik air", "overland airways",
        "ethiopian airlines", "british airways", "turkish airlines",
        "kenya airways", "qatar airways", "emirates airline",
        "air france", "lufthansa", "delta airline",
        "flight ticket", "airline ticket", "airflight",
        # Road transport
        "abc transport", "gigm bus", "ctt bus",
        "peace mass transit", "young shall grow",
        "god is good transport", "chisco transport",
        "bus ticket", "interstate transport", "highway transport",
        "motor park",
        # Other transport
        "car hire", "vehicle hire", "car rental",
        "toll gate", "toll fee", "car park", "parking fee",
        "bike dispatch", "dispatch rider", "keke napep",
        "auto mechanic", "car wash", "vehicle service",
        "spare part", "auto parts", "engine oil",
        "tyre purchase", "vehicle registration",
    ],
    "entertainment": [
        # Streaming
        "netflix subscription", "netflix payment",
        "showmax subscription", "spotify subscription",
        "apple music", "youtube premium", "amazon prime",
        "disney plus", "boomplay",
        # Betting
        "bet9ja", "sportybet", "nairabet", "merrybet",
        "1xbet", "betway", "bangbet", "surebet247",
        "parimatch", "msport", "betking", "betbonanza",
        "accessbet", "cloudbet", "sports betting",
        "bet deposit", "bet withdrawal",
        # Cinema & events
        "silverbird cinema", "filmhouse cinema",
        "genesis cinema", "ebonylife cinema",
        "ozone cinema", "viva cinema", "film house",
        "cinema ticket", "movie ticket", "concert ticket",
        "event ticket", "eventbrite", "nairabox",
        "amusement park", "karaoke",
        # Gaming
        "playstation network", "playstation store",
        "xbox game", "steam game", "nintendo",
        "game subscription",
        # Note: gotv/dstv/startimes/canal plus are classified as bills (recurring)
    ],
    "bills": [
        # Electricity by disco name
        "ekedc", "ikedc", "ikeja electric",
        "eko electricity", "eko disco",
        "kedco", "kano electricity",
        "phed electricity", "portharcourt electricity",
        "bedc electricity", "aedc abuja",
        "enedisco", "jed electricity",
        "jos electricity", "ibadan disco",
        "ibedc", "eedc enugu",
        # Generic electricity
        "electricity token", "prepaid token", "power token",
        "light bill", "electricity bill", "electricity payment",
        "nepa bill",
        # Internet & broadband
        "spectranet", "smile internet", "swift networks",
        "ipnx internet", "tizeti", "ntel",
        "internet subscription", "broadband subscription",
        "wifi subscription",
        # Cable TV (recurring bill, not one-time entertainment)
        "gotv", "dstv", "startimes", "hitv", "canal plus",
        # Airtime & data (recurring phone bills)
        "mtn airtime", "airtel airtime", "glo airtime",
        "9mobile airtime", "etisalat airtime",
        "airtime recharge", "airtime purchase", "airtime topup",
        "airtime top up", "vtu airtime",
        "mtn data", "airtel data", "glo data", "9mobile data",
        "data bundle", "data plan", "data subscription",
        "mtn subscription", "airtel subscription",
        # Water
        "water bill", "water rate", "water board",
        # Rent & housing
        "house rent", "monthly rent", "annual rent",
        "service charge", "estate levy", "caretaker levy",
        "facility management", "ground rent",
        "tenement rate", "building rent",
        # Insurance
        "insurance premium", "life insurance", "car insurance",
        "nhis", "health insurance", "hmo premium",
        "hygeia hmo", "reliance hmo", "leadway insurance",
        "aiico insurance", "mutual benefit",
        # Other utilities
        "waste management", "lawma", "sanitation levy",
        "lcc levy", "toll subscription",
    ],
    "health": [
        # Pharmacies & drug stores
        "medplus pharmacy", "healthplus pharmacy",
        "drug store", "pharmacy store", "chemist",
        "medication purchase", "medicine purchase",
        "drugs purchase", "drug payment",
        # Hospitals & clinics
        "teaching hospital", "general hospital", "private hospital",
        "private clinic", "medical center", "health center",
        "maternity home", "specialist hospital",
        # Diagnostics
        "medical laboratory", "pathcare lab",
        "radiology scan", "mri scan", "ultrasound scan",
        "x-ray", "ecg test", "blood test",
        # Specialists
        "dentist", "dental clinic", "orthodontist",
        "optician", "optometry", "eye clinic",
        "physiotherapy", "physiotherapist",
        # HMO
        "hygeia hmo", "reliance hmo", "hmo subscription",
        "health plan", "health maintenance",
        # Emergency
        "ambulance", "emergency medical",
        # Supplements & wellness
        "vitamin supplement", "supplement purchase",
        "wellness center", "gym membership",
        "fitness center",
        # Other medical
        "vaccination", "immunization", "antenatal",
        "mental health", "counseling session",
        "medical equipment",
    ],
    "education": [
        # Nigerian exams
        "jamb registration", "jamb payment",
        "waec examination", "waec registration",
        "neco exam", "nabteb exam", "post utme",
        "school fees", "school fee payment",
        "tuition payment", "tuition fee",
        "university fees", "polytechnic fees",
        "college of education", "admission fee",
        "course registration", "exam registration",
        "student hostel", "student accommodation",
        # Professional & certifications
        "professional certification", "ican exam",
        "ican membership", "cipm membership",
        "professional exam", "bar exam",
        # Online learning
        "udemy", "coursera", "linkedin learning",
        "skillshare", "alison course",
        "e-learning", "online course",
        # Study abroad
        "study abroad", "ielts registration",
        "toefl exam", "gre registration",
        "gmat exam", "sat exam",
        # Training
        "training workshop", "seminar fee",
        "conference registration", "training fee",
        "coaching class", "tutorial fee",
        "lesson payment", "vocational training",
    ],
    "shopping": [
        # Online marketplaces
        "jumia", "konga", "jiji marketplace",
        "aliexpress", "amazon purchase",
        "shein purchase", "temu purchase",
        # Electronics & tech
        "slot nigeria", "slot tech", "computer village",
        "slot phones", "pointek", "fouani",
        "electronics store", "phone purchase",
        "laptop purchase", "gadget store",
        # Malls & stores
        "ikeja mall", "palms mall", "lekki mall",
        "festac mall", "port harcourt mall",
        "jabi mall", "wuse market",
        "department store", "superstore",
        # Fashion & apparel
        "boutique fashion", "clothing store",
        "shoe store", "footwear", "apparel store",
        "fashion house", "fabric purchase",
        # Home & household
        "furniture store", "home appliance",
        "household item", "home decor",
        # Beauty
        "cosmetics", "beauty store", "skincare",
        "hair extension", "makeup store",
        # General retail
        "gift purchase", "souvenir",
        "merchandise", "general merchandise",
        "trade purchase",
    ],
    "other": [
        # Transfers
        "interbank transfer", "nip transfer", "neft transfer",
        "rtgs transfer", "mobile transfer",
        # Bank charges & fees
        "bank charge", "sms alert charge", "card maintenance fee",
        "stamp duty", "vat charge", "cot charge",
        "account maintenance fee", "annual fee",
        "withholding tax",
        # ATM & cash
        "atm withdrawal", "cash withdrawal", "pos withdrawal",
        # Reversals & adjustments
        "transaction reversal", "cashback reversal",
        "failed transaction", "charge reversal",
        # Income credits (shouldn't appear in debit analysis but handle anyway)
        "salary payment", "wages payment", "payroll",
        "commission earning", "dividend payment",
        "interest earned",
        # Peer & family
        "peer to peer transfer", "family support",
        "personal transfer",
    ],
}


# ── Pass 2: Single-token keywords (whole-word match after tokenising) ─────────
# Only include unambiguous words that reliably signal a single category.
# Keys are sets for O(1) lookup.
_TOKENS: dict[str, frozenset[str]] = {
    "food": frozenset({
        "shoprite", "spar", "kfc", "dominos", "domino's",
        "chicken", "pizza", "burger", "shawarma", "sharwarma",
        "suya", "bakery", "eatery", "cafeteria", "canteen",
        "restaurant", "catering", "groceries", "grocery",
        "foodstuff", "provisions",
    }),
    "transport": frozenset({
        "uber", "bolt", "taxify", "indriver",
        "petrol", "diesel", "fuel", "oando", "conoil", "mobil",
        "filling", "airline", "airways", "flight",
        "danfo", "keke", "okada", "brt",
        "gigm", "parking", "tollgate",
    }),
    "entertainment": frozenset({
        "netflix", "showmax", "spotify",
        "bet9ja", "sportybet", "nairabet", "betway", "merrybet",
        "1xbet", "bangbet", "betking",
        "cinema", "silverbird", "filmhouse",
        "playstation", "gaming",
        "boomplay",
    }),
    "bills": frozenset({
        "ekedc", "ikedc", "phed", "aedc", "bedc", "kedco",
        "enedisco", "ibedc", "eedc",
        "spectranet", "smile", "ipnx", "tizeti",
        "electricity", "airtime", "vtu",
        "rent", "landlord",
    }),
    "health": frozenset({
        "pharmacy", "pharmacist", "chemist",
        "hospital", "clinic", "dispensary",
        "laboratory", "pathcare", "dentist",
        "optician", "physiotherapy",
        "medication", "medicine", "drugs",
        "vaccine", "vaccination",
    }),
    "education": frozenset({
        "jamb", "waec", "neco", "nabteb",
        "udemy", "coursera", "skillshare",
        "ielts", "toefl", "gre", "gmat",
        "tuition", "tutorial",
    }),
    "shopping": frozenset({
        "jumia", "konga", "jiji", "aliexpress", "amazon",
        "shein", "temu",
        "slot", "pointek",
        "boutique", "superstore",
    }),
}

# Words that appear in bank descriptions but carry no category signal.
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
})

_TOKEN_SPLIT = re.compile(r"[\s/\-_,\.;:@#\(\)\[\]]+")


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t and t not in _NOISE]


def classify_transaction(description: str) -> dict:
    text = (description or "").lower().strip()

    # Pass 1 — phrase match (categories checked in priority order)
    for category, phrases in _PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                return {"category": category, "confidence": 0.90}

    # Pass 2 — token match
    toks = set(_tokens(text))
    for category, word_set in _TOKENS.items():
        if toks & word_set:  # any overlap
            return {"category": category, "confidence": 0.75}

    return {"category": "other", "confidence": 0.45}


def classify_batch(descriptions: list) -> list:
    return [classify_transaction(d) for d in descriptions]


def update_prototype(category: str, description: str) -> None:
    # No-op: keyword classifier has no learnable parameters.
    # User corrections are persisted via DB for analytics.
    pass
