"""
Nigerian bank transaction classifier – 4-pass approach.

Nigerian transfer descriptions often encode the real intent at the END, e.g.:
  "Transfer to OGECHUKWU PRECIOUS | OPay | 9067451387 | For cake"
                                                        ^^^^^^^^
                                           this is the signal that matters

Pipeline:
  0. Memo extraction  — pull the human-written purpose from the end of the text
  1. Brand lookup     — known merchant/brand substrings → category (longest match first)
  2. Phrase match     — curated descriptive phrases → category
  3. Token scoring    — accumulate per-word evidence; pick highest-scored category
  4. AI fallback      — Claude Haiku for descriptions that survive all keyword passes
                        as "other" yet contain a meaningful human memo.
                        Only runs if ANTHROPIC_API_KEY is set in the environment.
"""

import os
import re
from collections import defaultdict

CATEGORIES = [
    "food", "transport", "entertainment", "utilities", "bills",
    "health", "education", "shopping", "other",
]

# ─────────────────────────────────────────────────────────────────────────────
# Pass 0 — Memo extraction
# ─────────────────────────────────────────────────────────────────────────────

_MEMO_STRIP = re.compile(
    r'^\s*(?:for\s+|re[:\s]+|memo[:\s]+|note[:\s]+|purpose[:\s]+|narration[:\s]+)',
    re.IGNORECASE,
)

_PHONE_RE = re.compile(r'^[\+]?[\d][\d\s\-]{7,14}$')

# Segments that look like data sizes, amounts, or references — not useful memos.
_SKIP_SEGMENT_RE = re.compile(
    r'^(\d+(?:\.\d+)?(?:gb|mb|kb|tb)?'   # data sizes: 25GB, 1.5GB, 500MB
    r'|\d+(?:ngn|naira|k|m)?'             # amounts: 500, 1000NGN, 5k
    r'|[a-z0-9]{12,}'                     # long reference codes (12+ chars)
    r')$',
    re.IGNORECASE,
)

# Bank / wallet names that appear as pipe-segments but carry no category signal.
_BANK_TOKENS = frozenset({
    "gtb", "gtbank", "access", "zenith", "uba", "fcmb", "stanbic", "sterling",
    "union", "heritage", "wema", "opay", "palmpay", "moniepoint", "kuda",
    "fidelity", "firstbank", "first bank", "ecobank", "polaris", "vfd",
    "providus", "jaiz", "lotus", "paystack", "flutterwave", "paystack-titan",
})


def _extract_memo(raw: str) -> str:
    """
    Return the human-written reason/purpose embedded in a bank description,
    or the full text if no structured memo is found.

    Examples
    --------
    "Transfer to JOHN DOE | OPay | 0812345678 | For cake"  →  "cake"
    "Sent to JANE/rent payment"                             →  "rent payment"
    "Payment for school fees today"                         →  "school fees today"
    "POS SHOPRITE MARYLAND"                                 →  (unchanged)
    """
    text = raw.strip()

    # ── Pipe-delimited (OPay / PalmPay / Moniepoint / direct bank transfers) ──
    if '|' in text:
        parts = [p.strip() for p in text.split('|')]
        for part in reversed(parts):
            if not part:
                continue
            if _PHONE_RE.match(part):
                continue                      # skip phone numbers
            candidate = _MEMO_STRIP.sub('', part).strip()
            if len(candidate) <= 2:
                continue
            if _SKIP_SEGMENT_RE.match(candidate):
                continue                      # skip "25GB", "500", ref codes
            if candidate.lower() in _BANK_TOKENS:
                continue                      # skip bank/wallet names
            # Skip ALL-CAPS personal names (recipient names, not purposes).
            if re.fullmatch(r'[A-Z][A-Z\s]+', candidate):
                continue
            return candidate

    # ── Slash-delimited (some NIP/NEFT descriptions) ──────────────────────────
    if text.count('/') >= 2:
        parts = [p.strip() for p in text.split('/')]
        for part in reversed(parts):
            candidate = _MEMO_STRIP.sub('', part).strip()
            if len(candidate) < 3:
                continue
            if _PHONE_RE.match(part) or re.match(r'^\d{6,}$', candidate):
                continue
            return candidate

    # ── Inline "for X" anywhere in the text ──────────────────────────────────
    m = re.search(r'\bfor\s+(.{3,60})$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return text  # no structured memo — use the full description


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — Brand / merchant name lookup
# ─────────────────────────────────────────────────────────────────────────────
# Sorted longest-first so "jumia food" matches before "jumia",
# "bolt food" matches before "bolt", etc.

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
    ("fuel station",            "transport"),
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

    # ── utilities (electricity / water / airtime / data / internet) ──────────
    # OPay / PalmPay / Moniepoint service codes (pipe-segment format)
    ("mobile data",             "utilities"),
    ("data purchase",           "utilities"),
    ("airtime purchase",        "utilities"),
    ("bill payment",            "utilities"),
    ("datamtn",                 "utilities"),
    ("dataairtel",              "utilities"),
    ("dataglo",                 "utilities"),
    ("data9mobile",             "utilities"),
    ("dataetisalat",            "utilities"),
    ("airtimemtn",              "utilities"),
    ("airtimeairtel",           "utilities"),
    ("airtimeglo",              "utilities"),
    ("airtime9mobile",          "utilities"),
    ("ikeja electric",          "utilities"),
    ("eko electricity",         "utilities"),
    ("kano electricity",        "utilities"),
    ("phed electricity",        "utilities"),
    ("bedc electricity",        "utilities"),
    ("jed electricity",         "utilities"),
    ("eedc enugu",              "utilities"),
    ("jos electricity",         "utilities"),
    ("ibadan disco",            "utilities"),
    ("swift networks",          "utilities"),
    ("smile internet",          "utilities"),
    ("aedc abuja",              "utilities"),
    ("spectranet",              "utilities"),
    ("enedisco",                "utilities"),
    ("wakanet",                 "utilities"),
    ("ekedc",                   "utilities"),
    ("ikedc",                   "utilities"),
    ("kedco",                   "utilities"),
    ("ibedc",                   "utilities"),
    ("tizeti",                  "utilities"),
    ("ipnx",                    "utilities"),
    ("phed",                    "utilities"),
    ("bedc",                    "utilities"),
    ("aedc",                    "utilities"),
    ("eedc",                    "utilities"),
    ("ntel",                    "utilities"),

    # ── bills (rent / insurance / recurring subscriptions) ───────────────────
    ("nhis",                    "bills"),
    ("hygeia hmo",              "bills"),
    ("reliance hmo",            "bills"),
    ("leadway insurance",       "bills"),
    ("aiico insurance",         "bills"),
    ("mutual benefit",          "bills"),
    ("canal plus",              "bills"),
    ("startimes",               "bills"),
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


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — Phrase match (substring)
# ─────────────────────────────────────────────────────────────────────────────

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
        # Nigerian dishes and ingredients
        "jollof rice", "fried rice", "egusi soup", "ogbono soup", "banga soup",
        "pepper soup", "oha soup", "efo riro", "edikaikong",
        "pounded yam", "amala", "eba", "fufu", "semolina", "semo",
        "akara", "puff puff", "moi moi", "moimoi",
        "kilishi", "suya", "chin chin", "boli", "roasted corn",
        "garri", "indomie", "noodles",
        "tomatoes", "tomato paste", "pepper", "onions", "vegetables", "fruits",
        "yam", "plantain", "cassava", "potato", "potatoes",
        "fish", "meat", "beef", "chicken", "turkey", "assorted meat",
        "ponmo", "kpomo", "goat meat", "cow leg",
        "palm oil", "groundnut oil", "vegetable oil",
        "groundnut", "peanut", "tiger nut", "zobo", "kunu",
        "bread", "loaf", "butter",
        # colloquial memo words people type in transfers
        "buy food", "for food", "food money",
        "lunch money", "dinner money", "breakfast money",
        "buy cake", "for cake", "cake money",
        "buy snacks", "for snacks",
        "buy groceries", "for groceries",
        "buy drinks", "for drinks",
        "chop money", "feeding money", "feeding allowance",
        "for market", "market money", "market list",
        "cook", "cooking", "for cooking",
    ],
    "transport": [
        "bolt ride", "bolt trip", "bolt car",
        "fuel purchase", "petrol purchase", "diesel purchase",
        "fuel top up", "fuel topup", "buy fuel", "buy petrol", "for fuel", "for petrol",
        "fuel money", "transport fare", "bus fare", "transport money",
        "flight ticket", "airline ticket", "bus ticket", "interstate transport",
        "motor park", "highway transport",
        "car hire", "vehicle hire", "car rental",
        "toll gate", "toll fee", "car park", "parking fee",
        "bike dispatch", "dispatch rider",
        "auto mechanic", "car wash", "vehicle service",
        "spare part", "auto parts", "engine oil",
        "tyre purchase", "vehicle registration",
        "for transport", "for fare", "for uber", "for bolt",
        "for ticket", "flight money",
        # courier / dispatch (sending packages)
        "waybill fee", "waybill payment", "dispatch fee", "courier fee",
        "for waybill", "waybill money", "for dispatch", "dispatch money",
        "gig logistics", "gig courier",
        # informal travel
        "road money", "for road", "travel money", "for travel",
        "going home", "for journey",
    ],
    "entertainment": [
        "sports betting", "bet deposit", "bet withdrawal",
        "cinema ticket", "movie ticket", "concert ticket",
        "event ticket", "amusement park", "karaoke",
        "xbox game", "steam game", "game subscription",
        "youtube subscription", "streaming subscription",
        "for bet", "for betting", "betting money",
        "for movie", "for cinema",
    ],
    "utilities": [
        # electricity
        "electricity token", "prepaid token", "power token", "meter token",
        "electricity bill", "electric bill", "light bill", "nepa bill",
        "electricity payment", "electricity recharge",
        "prepaid meter", "postpaid bill", "utility bill",
        # internet & data
        "internet subscription", "broadband subscription", "wifi subscription",
        "internet data", "data bundle", "data plan", "data subscription", "data purchase",
        "mtn data", "airtel data", "glo data", "9mobile data",
        "mtn subscription", "airtel subscription", "glo subscription",
        # airtime
        "mtn airtime", "airtel airtime", "glo airtime", "9mobile airtime",
        "airtime recharge", "airtime purchase", "airtime topup", "airtime top up",
        "vtu airtime", "airtime vtu", "airtime transfer", "buy airtime",
        # water
        "water bill", "water rate", "water board",
        # colloquial
        "for light", "for electricity", "for airtime", "for data", "for internet",
        "light bill money", "buy data",
    ],
    "bills": [
        # cable TV subscriptions
        "cable tv", "cable subscription", "cable tv subscription",
        "for dstv", "for gotv",
        # rent
        "house rent", "monthly rent", "annual rent", "rent payment",
        "for rent", "rent money",
        "service charge", "estate levy", "facility management",
        "ground rent", "tenement rate",
        # insurance
        "insurance premium", "life insurance", "car insurance", "hmo premium",
        "health insurance", "hmo subscription",
        # waste
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
        # common Nigerian illnesses / specific drugs people name in memos
        "malaria treatment", "malaria drugs", "malaria medicine", "for malaria",
        "typhoid treatment", "typhoid drugs", "for typhoid",
        "for drip", "drip money", "intravenous drip",
        "for paracetamol", "paracetamol", "panadol", "ibuprofen",
        "amoxicillin", "ampiclox", "flagyl", "ciprofloxacin",
        "for glasses", "for specs", "for spectacles", "glasses money",
        "eye glasses", "contact lenses", "for lenses",
        "for circumcision",
        # colloquial memo words
        "for hospital", "for drugs", "for medicine", "for treatment",
        "for doctor", "for clinic", "for injection", "hospital money",
        "drug money", "medical money",
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
        # school supplies — the most-missed category in informal memos
        "school supplies", "school items", "school materials",
        "for cardboard", "cardboard money", "buy cardboard",   # packing for school/hostel
        "for carton", "carton money", "buy carton",            # same usage
        "for trunk", "school trunk",                           # boarding school trunk
        "for notebook", "notebook money", "buy notebook", "exercise book",
        "for handout", "handout money", "buy handout", "lecture note", "handouts",
        "for textbook", "textbook money", "buy textbook",
        "for stationery", "stationery money", "stationery items",
        "for biro", "biro money", "buy biro", "pen money", "for pen",
        "for pencil", "pencil money",
        "for printing", "printing money", "for photocopy", "photocopy money",
        "for uniform", "school uniform", "uniform money",
        "for school bag", "school bag money",
        "for reading", "reading material",
        "for nysc", "nysc allowance", "nysc registration",
        "for ppa", "nysc ppa",                                 # place of primary assignment
        "for resumption", "resumption money",                  # school resumption
        "for clearance", "clearance fee",                      # school clearance
        "for result", "result checking",                       # checking school results
        # colloquial memo words
        "for school", "school money", "for tuition", "for lesson",
        "for exam", "for jamb", "for waec", "for books", "book money",
        "for course", "for training",
        "lesson money", "for extra lesson", "extra lesson",
        "lesson fee", "tutorial money",
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
        # Nigerian fabrics and tailoring
        "ankara fabric", "for ankara", "ankara money",
        "lace fabric", "for lace", "george fabric", "aso ebi", "aso-ebi",
        "for fabric", "fabric money", "for material", "cloth material",
        "for tailoring", "tailoring money", "for tailor",
        "native wear", "for native", "agbada", "buba", "iro and buba",
        # jewelry and accessories
        "for jewelry", "jewelry purchase", "for jewellery",
        "for necklace", "for bracelet", "for earrings", "for ring",
        "for gold", "gold jewelry",
        # beauty / salon services
        "for barbing", "barbing money", "barbing salon", "haircut money",
        "for manicure", "manicure money", "for pedicure", "pedicure money",
        "for nail", "nail salon", "nail fix",
        "hair extension", "for extension", "for weave",
        "lace frontal", "lace closure", "hair closure",
        "for wig", "wig money", "buy wig",
        # household items
        "for mattress", "for pot", "for pots", "cooking pot",
        "for pressing iron", "for fan", "for television",
        "household items", "home items",
        # colloquial memo words
        "for shopping", "for clothes", "for shoes", "for bag",
        "for phone", "for laptop", "for makeup", "for hair",
        "shopping money", "market money",
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

# ─────────────────────────────────────────────────────────────────────────────
# Pass 3 — Token scoring
# ─────────────────────────────────────────────────────────────────────────────

_SCORES: dict[str, dict[str, float]] = {
    "food": {
        "food": 0.80, "restaurant": 0.90, "eatery": 0.90, "cafeteria": 0.85,
        "canteen": 0.85, "catering": 0.75, "grocery": 0.85, "groceries": 0.85,
        "foodstuff": 0.90, "provisions": 0.75, "bakery": 0.85,
        "shawarma": 0.95, "sharwarma": 0.95, "suya": 0.95,
        "pizza": 0.80, "burger": 0.80, "chicken": 0.55, "snack": 0.65,
        "snacks": 0.65, "cake": 0.80, "cakes": 0.80,
        "lunch": 0.80, "dinner": 0.80, "breakfast": 0.80,
        "cafe": 0.70, "supermarket": 0.80, "buka": 0.90, "chops": 0.70,
        "smoothie": 0.80, "pastry": 0.80, "confectionery": 0.85,
        "shoprite": 0.95, "spar": 0.90, "kfc": 0.95, "dominos": 0.95,
        "drinks": 0.65, "drink": 0.55, "beer": 0.65, "wine": 0.65,
        "rice": 0.70, "beans": 0.70, "stew": 0.70, "pepper": 0.60,
        "feeding": 0.80, "chop": 0.75,
        # Nigerian dishes and ingredients
        "egusi": 0.95, "ogbono": 0.95, "jollof": 0.90, "banga": 0.80,
        "akara": 0.95, "puff": 0.75, "moimoi": 0.95, "kilishi": 0.95,
        "garri": 0.90, "indomie": 0.90, "noodles": 0.80,
        "amala": 0.90, "eba": 0.85, "fufu": 0.90, "semolina": 0.75,
        "plantain": 0.85, "yam": 0.80, "cassava": 0.75,
        "tomato": 0.70, "tomatoes": 0.75, "vegetables": 0.65, "fruits": 0.65,
        "fish": 0.65, "meat": 0.65, "beef": 0.70, "turkey": 0.65,
        "ponmo": 0.90, "kpomo": 0.90, "assorted": 0.65,
        "groundnut": 0.80, "peanut": 0.75, "zobo": 0.90, "kunu": 0.90,
        "bread": 0.70, "loaf": 0.70,
        "cooking": 0.65, "cook": 0.60, "ingredient": 0.70,
        "oha": 0.90, "efo": 0.85, "edikaikong": 0.95,
        "chin": 0.70, "boli": 0.85,
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
        "fare": 0.75, "ride": 0.70, "trip": 0.65, "ticket": 0.70,
        "bus": 0.65, "taxi": 0.75, "motor": 0.60,
        "courier": 0.75, "dispatch": 0.70, "waybill": 0.80,
        "delivery": 0.55, "logistics": 0.65,
        "travel": 0.70, "journey": 0.70,
    },
    "entertainment": {
        "netflix": 0.99, "showmax": 0.99, "spotify": 0.99, "boomplay": 0.99,
        "audiomack": 0.95, "soundcloud": 0.95,
        "bet9ja": 0.99, "sportybet": 0.99, "nairabet": 0.99,
        "betway": 0.99, "1xbet": 0.99, "betking": 0.99, "bangbet": 0.99,
        "cinema": 0.90, "silverbird": 0.95, "filmhouse": 0.95,
        "playstation": 0.95, "gaming": 0.85, "betting": 0.90,
        "entertainment": 0.80, "streaming": 0.80,
        "casino": 0.90, "lottery": 0.85, "movie": 0.80, "movies": 0.80,
        "bet": 0.75, "wager": 0.85, "odds": 0.75,
    },
    "utilities": {
        # electricity DISCOs
        "ekedc": 0.99, "ikedc": 0.99, "phed": 0.99, "aedc": 0.99,
        "bedc": 0.99, "kedco": 0.99, "enedisco": 0.99, "ibedc": 0.99,
        # internet providers
        "spectranet": 0.99, "tizeti": 0.99, "ipnx": 0.99,
        # generic utility words
        "electricity": 0.90, "airtime": 0.90, "vtu": 0.90,
        "internet": 0.80, "broadband": 0.80, "data": 0.70,
        "token": 0.75, "recharge": 0.80, "prepaid": 0.75, "nepa": 0.90,
        "wifi": 0.80, "light": 0.65, "utility": 0.75,
        "mtn": 0.65, "airtel": 0.65, "glo": 0.65,
    },
    "bills": {
        "gotv": 0.99, "dstv": 0.99, "startimes": 0.99,
        "rent": 0.85, "landlord": 0.90,
        "insurance": 0.75, "premium": 0.65,
        "cable": 0.75, "subscription": 0.60,
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
        "injection": 0.85, "treatment": 0.75, "therapy": 0.80,
        "lab": 0.70, "test": 0.55, "checkup": 0.80, "consultation": 0.75,
        # specific illnesses / drug names common in Nigerian memos
        "malaria": 0.90, "typhoid": 0.90, "malaria": 0.90,
        "paracetamol": 0.95, "panadol": 0.95, "ibuprofen": 0.90,
        "amoxicillin": 0.95, "ampiclox": 0.95, "flagyl": 0.95,
        "ciprofloxacin": 0.95, "coartem": 0.95, "lonart": 0.95,
        "drip": 0.80, "infusion": 0.80,
        "glasses": 0.70, "specs": 0.80, "spectacles": 0.85, "lenses": 0.75,
        "prescription": 0.75,
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
        "books": 0.75, "stationery": 0.80, "lecture": 0.80,
        "hostel": 0.75, "fees": 0.70,
        # school supplies often typed as memos
        "cardboard": 0.80,   # students buy cardboard for school packing / projects
        "carton": 0.70,      # same use — packing trunk for boarding school/hostel
        "notebook": 0.85, "notebooks": 0.85,
        "textbook": 0.90, "textbooks": 0.90,
        "handout": 0.85, "handouts": 0.85,
        "biro": 0.85, "pencil": 0.80,
        "printing": 0.70, "photocopy": 0.80,
        "uniform": 0.72,     # school uniform (moderate — could be work uniform)
        "resumption": 0.85,  # school resumption fees/money
        "clearance": 0.70,   # school clearance
        "nysc": 0.90,        # National Youth Service Corps
        "reading": 0.60,     # "for reading" — mild signal
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
        "clothes": 0.85, "shoes": 0.85, "bag": 0.75, "bags": 0.75,
        "phone": 0.70, "laptop": 0.80, "wristwatch": 0.80, "watch": 0.65,
        "hair": 0.65, "wig": 0.80, "weave": 0.80,
        # Nigerian fabrics
        "ankara": 0.85, "fabric": 0.80, "lace": 0.75,
        "george": 0.75, "asoebi": 0.95, "aso-ebi": 0.95,
        "tailoring": 0.85, "tailor": 0.80, "sewing": 0.75,
        "agbada": 0.85, "buba": 0.75, "kaftan": 0.85,
        # jewelry
        "jewelry": 0.85, "jewellery": 0.85, "necklace": 0.85,
        "bracelet": 0.85, "earrings": 0.85, "earring": 0.85,
        "ring": 0.65, "gold": 0.70,
        # salon services
        "barbing": 0.75, "haircut": 0.70,
        "manicure": 0.85, "pedicure": 0.85,
        "nail": 0.70, "extensions": 0.75, "frontal": 0.80, "closure": 0.75,
        # household
        "mattress": 0.80, "appliances": 0.80, "generator": 0.70,
        "television": 0.75, "fridge": 0.80, "freezer": 0.80,
    },
}

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
    "gtb", "gtbank", "access", "zenith", "uba", "fcmb", "stanbic",
    "sterling", "union", "heritage", "wema", "opay", "palmpay",
    "moniepoint", "kuda",
})

_TOKEN_SPLIT = re.compile(r"[\s/\-_,\.;:@#\(\)\[\]\*\+\&]+")

_SCORE_THRESHOLD = 0.60


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.lower()) if t and t not in _NOISE]


def _classify_text(text: str) -> dict:
    """Apply brand → phrase → token-score passes to a single text string."""
    # Pass 1: brand lookup
    for brand, category in _BRANDS:
        if brand in text:
            return {"category": category, "confidence": 0.92}

    # Pass 2: phrase match
    for category, phrases in _PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                return {"category": category, "confidence": 0.88}

    # Pass 3: token scoring
    cat_scores: dict[str, float] = defaultdict(float)
    for tok in _tokens(text):
        for cat, word_map in _SCORES.items():
            if tok in word_map:
                cat_scores[cat] += word_map[tok]

    if cat_scores:
        best = max(cat_scores, key=cat_scores.__getitem__)
        score = cat_scores[best]
        if score >= _SCORE_THRESHOLD:
            confidence = round(min(0.88, 0.65 + score * 0.15), 2)
            return {"category": best, "confidence": confidence}

    return {"category": "other", "confidence": 0.45}


# ─────────────────────────────────────────────────────────────────────────────
# Pass 4 — Claude Haiku AI fallback
# ─────────────────────────────────────────────────────────────────────────────
# Only active when ANTHROPIC_API_KEY is set.  Used for memos that survive all
# keyword passes as "other" yet are clearly human-written purpose descriptions.

_AI_SYSTEM = (
    "You are a Nigerian bank transaction classifier. "
    "Given a short memo or transaction description, output EXACTLY ONE word from:\n"
    "food, transport, entertainment, bills, health, education, shopping, other\n\n"
    "Rules:\n"
    "- food: anything edible — restaurants, groceries, cakes, drinks, market food\n"
    "- transport: fuel/petrol, Uber/Bolt rides, flights, bus tickets, car repairs\n"
    "- entertainment: betting, cinema, Netflix/Spotify/streaming, gaming\n"
    "- bills: electricity tokens, airtime/data, rent, DSTV/GOTV, water, insurance\n"
    "- health: pharmacy/drugs, hospital/clinic, doctor, gym membership\n"
    "- education: school fees, JAMB/WAEC, online courses, tutoring, books\n"
    "- shopping: Jumia/Konga/online shops, clothing, shoes, electronics, beauty\n"
    "- other: peer transfers with no stated purpose, bank charges, salary\n\n"
    "Output only the category word, nothing else."
)

_ai_client = None
_AI_AVAILABLE = False


def _get_ai_client():
    global _ai_client, _AI_AVAILABLE
    if _ai_client is not None:
        return _ai_client
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        _ai_client = anthropic.Anthropic(api_key=key)
        _AI_AVAILABLE = True
        return _ai_client
    except Exception:
        return None


def _classify_with_ai(memo: str) -> dict:
    client = _get_ai_client()
    if not client:
        return {"category": "other", "confidence": 0.45}
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=_AI_SYSTEM,
            messages=[{"role": "user", "content": f'"{memo}"'}],
        )
        category = msg.content[0].text.strip().lower().split()[0]
        if category in CATEGORIES:
            return {"category": category, "confidence": 0.85}
    except Exception:
        pass
    return {"category": "other", "confidence": 0.45}


# ─────────────────────────────────────────────────────────────────────────────
# User corrections — checked before all other passes
# ─────────────────────────────────────────────────────────────────────────────

import json as _json

_CORRECTIONS_FILE = os.path.join(os.path.dirname(__file__), "user_corrections.json")
_CORRECTIONS: dict[str, str] = {}

try:
    with open(_CORRECTIONS_FILE) as _f:
        _CORRECTIONS = _json.load(_f)
except Exception:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def classify_transaction(description: str) -> dict:
    text = (description or "").lower().strip()
    if not text:
        return {"category": "other", "confidence": 0.45}

    # User corrections take highest priority
    if text in _CORRECTIONS:
        return {"category": _CORRECTIONS[text], "confidence": 1.0}

    # Extract the human-written purpose from the end of the description.
    # e.g. "Transfer to JOHN | OPay | 0801234 | For cake"  →  "cake"
    memo = _extract_memo(text)
    memo_lower = memo.lower()

    # Classify the memo first — it's the most specific human signal.
    if memo_lower != text:
        result = _classify_text(memo_lower)
        if result["category"] != "other":
            return result

    # Classify the full description.
    result = _classify_text(text)

    # AI fallback: if we extracted a meaningful memo but keywords found nothing,
    # let Claude Haiku interpret natural language ("cake", "mama's food", etc.)
    if (result["category"] == "other"
            and memo_lower != text
            and len(memo) >= 3
            and os.getenv("ANTHROPIC_API_KEY")):
        return _classify_with_ai(memo)

    return result


def classify_batch(descriptions: list) -> list:
    return [classify_transaction(d) for d in descriptions]


def update_prototype(category: str, description: str) -> None:
    """Store a user correction so it takes effect immediately and persists across restarts."""
    key = (description or "").lower().strip()
    if not key or category not in CATEGORIES:
        return
    _CORRECTIONS[key] = category
    try:
        with open(_CORRECTIONS_FILE, "w") as f:
            _json.dump(_CORRECTIONS, f, indent=2)
    except Exception:
        pass
