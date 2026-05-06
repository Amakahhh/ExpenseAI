import pickle
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional

MODEL_DIR = Path(__file__).parent.parent / "ml_model"
PKL_PATH  = MODEL_DIR / "expense_model.pkl"

CATEGORIES = [
    "food", "transport", "entertainment", "bills",
    "health", "education", "shopping", "other",
]

# Each category gets many realistic Nigerian bank transaction descriptions.
# Encoding them individually and averaging builds a far richer prototype than
# a single keyword blob.
_CATEGORY_SEEDS: dict[str, list[str]] = {
    "food": [
        "POS SHOPRITE LEKKI",
        "POS CHICKEN REPUBLIC IKEJA",
        "POS DOMINOS PIZZA VI",
        "POS COLDSTONE CREAMERY",
        "POS SPAR SUPERMARKET",
        "POS TASTEE FRIED CHICKEN",
        "POS SWEET SENSATION SURULERE",
        "POS MR BIGGS IKORODU",
        "POS KFC MARYLAND",
        "POS DEBONAIRS PIZZA",
        "POS TANTALIZERS RESTAURANT",
        "POS KILIMANJARO RESTAURANT",
        "JUMIA FOOD ORDER PAYMENT",
        "BOLT FOOD DELIVERY PAYMENT",
        "GLOVO FOOD DELIVERY",
        "POS LOCAL RESTAURANT PAYMENT",
        "GROCERY STORE PURCHASE",
        "MARKET FOOD PURCHASE",
        "BUKA FOOD PAYMENT",
        "CAFETERIA PAYMENT",
        "RESTAURANT MEAL PAYMENT",
        "FOOD DELIVERY SERVICE CHARGE",
        "BAKERY BREAD PURCHASE",
        "CANTEEN PAYMENT",
        "CATERER PAYMENT FOR EVENT FOOD",
    ],
    "transport": [
        "UBER TRIP VICTORIA ISLAND",
        "BOLT RIDE LAGOS ISLAND",
        "TAXIFY TRIP PAYMENT",
        "INDRIVER RIDE PAYMENT",
        "POS TOTAL PETROL STATION",
        "POS CONOIL FUEL PURCHASE",
        "FUEL PURCHASE MOBIL STATION",
        "DIESEL PURCHASE OANDO",
        "DANA AIR TICKET PURCHASE",
        "AIR PEACE FLIGHT BOOKING",
        "ARIK AIR TICKET LAGOS ABUJA",
        "WAKANOW FLIGHT TICKET",
        "GATE1 BUS TICKET PAYMENT",
        "ABC TRANSPORT BUS TICKET",
        "GIGM BUS TICKET PAYMENT",
        "CAR HIRE SERVICE PAYMENT",
        "VEHICLE MAINTENANCE PAYMENT",
        "PARKING FEE PAYMENT",
        "TOLL GATE PAYMENT",
        "RIDE HAILING PAYMENT",
        "TRICYCLE KEKE PAYMENT",
        "BIKE DISPATCH DELIVERY CHARGE",
        "INTERSTATE TRANSPORT FARE",
        "VEHICLE REGISTRATION FEE",
        "ROAD TRANSPORT PAYMENT",
    ],
    "entertainment": [
        "NETFLIX SUBSCRIPTION PAYMENT",
        "SHOWMAX SUBSCRIPTION RENEWAL",
        "DSTV SUBSCRIPTION PAYMENT",
        "GOTV SUBSCRIPTION RENEWAL",
        "CANAL PLUS SUBSCRIPTION",
        "SPOTIFY MUSIC SUBSCRIPTION",
        "APPLE MUSIC SUBSCRIPTION",
        "YOUTUBE PREMIUM PAYMENT",
        "SILVERBIRD CINEMA TICKET",
        "FILMHOUSE CINEMAS PAYMENT",
        "GENESIS CINEMA TICKET PURCHASE",
        "EBONYLIFE CINEMAS PAYMENT",
        "POS CLUB 57 LOUNGE PAYMENT",
        "POS SKY BAR NIGHTCLUB",
        "CONCERT TICKET PURCHASE",
        "EVENTBRITE EVENT TICKET",
        "NAIRABET BETTING PAYMENT",
        "BET9JA SPORTS BETTING",
        "SPORTYBET PAYMENT",
        "1XBET ONLINE BETTING",
        "GAMING SUBSCRIPTION PAYMENT",
        "PLAYSTATION NETWORK PURCHASE",
        "STEAM GAME PURCHASE",
        "KARAOKE BAR PAYMENT",
        "AMUSEMENT PARK TICKET",
    ],
    "bills": [
        "EKEDC ELECTRICITY TOKEN PURCHASE",
        "IKEDC PREPAID TOKEN PAYMENT",
        "KEDCO ELECTRICITY BILL",
        "PHED ELECTRICITY TOKEN",
        "ENEDISCO ELECTRICITY PAYMENT",
        "AEDC ELECTRICITY TOKEN",
        "JED ELECTRICITY TOKEN PURCHASE",
        "BEDC ELECTRICITY PREPAID TOKEN",
        "WATER BILL PAYMENT LAWMA",
        "SPECTRANET INTERNET SUBSCRIPTION",
        "SMILE INTERNET SUBSCRIPTION",
        "SWIFT NETWORKS INTERNET BILL",
        "HOME INTERNET SUBSCRIPTION PAYMENT",
        "MTN INTERNET DATA SUBSCRIPTION",
        "AIRTEL BROADBAND SUBSCRIPTION",
        "GLO UNLIMITED DATA PLAN",
        "9MOBILE DATA BUNDLE PAYMENT",
        "HOUSE RENT PAYMENT",
        "MONTHLY RENT LANDLORD TRANSFER",
        "SERVICE CHARGE ESTATE LEVY",
        "FACILITY MANAGEMENT FEE",
        "WASTE MANAGEMENT BILL LAWMA",
        "INSURANCE PREMIUM PAYMENT",
        "NHIS HEALTH INSURANCE PAYMENT",
        "ANNUAL SUBSCRIPTION UTILITY",
    ],
    "health": [
        "MEDPLUS PHARMACY PURCHASE",
        "HEALTHPLUS PHARMACY PAYMENT",
        "POS PHARMACY DRUG PURCHASE",
        "DRUG STORE MEDICATION PAYMENT",
        "LAGOS UNIVERSITY TEACHING HOSPITAL",
        "GENERAL HOSPITAL CONSULTATION FEE",
        "PRIVATE CLINIC DOCTOR CONSULTATION",
        "MEDICAL LABORATORY TEST PAYMENT",
        "PATHCARE LAB BLOOD TEST",
        "RADIOLOGY SCAN PAYMENT",
        "DENTIST CONSULTATION FEE",
        "OPTICIAN EYE TEST PAYMENT",
        "PHYSIOTHERAPY SESSION PAYMENT",
        "HMO HEALTH MAINTENANCE PAYMENT",
        "RELIANCE HMO PAYMENT",
        "HYGEIA HMO SUBSCRIPTION",
        "SURGERY HOSPITAL BILL PAYMENT",
        "AMBULANCE SERVICE FEE",
        "MENTAL HEALTH THERAPY SESSION",
        "WELLNESS CENTER PAYMENT",
        "VITAMIN SUPPLEMENT PURCHASE",
        "MEDICAL EQUIPMENT PURCHASE",
        "VACCINATION FEE PAYMENT",
        "ANTENATAL CARE PAYMENT",
        "EMERGENCY MEDICAL BILL",
    ],
    "education": [
        "SCHOOL FEES PAYMENT LAGOS",
        "UNIVERSITY TUITION FEE PAYMENT",
        "JAMB REGISTRATION FEE PAYMENT",
        "WAEC EXAMINATION FEE",
        "NECO EXAM REGISTRATION FEE",
        "POST UTME SCREENING FEE",
        "NABTEB EXAM FEE PAYMENT",
        "COURSE REGISTRATION FEE",
        "PROFESSIONAL CERTIFICATION FEE",
        "UDEMY COURSE PURCHASE",
        "COURSERA SUBSCRIPTION PAYMENT",
        "LINKEDIN LEARNING SUBSCRIPTION",
        "BOOK PURCHASE PAYMENT",
        "EDUCATIONAL MATERIAL PURCHASE",
        "STUDY ABROAD APPLICATION FEE",
        "STUDENT ACCOMMODATION PAYMENT",
        "IELTS REGISTRATION FEE",
        "TOEFL EXAM FEE PAYMENT",
        "TRAINING WORKSHOP REGISTRATION",
        "SEMINAR ATTENDANCE FEE",
        "E-LEARNING PLATFORM SUBSCRIPTION",
        "COACHING CLASS PAYMENT",
        "TUTORIAL FEE PAYMENT",
        "VOCATIONAL TRAINING FEE",
        "SKILLS ACQUISITION PROGRAM FEE",
    ],
    "shopping": [
        "JUMIA ONLINE SHOPPING PAYMENT",
        "KONGA ONLINE STORE PURCHASE",
        "JIJI MARKETPLACE PAYMENT",
        "ALIEXPRESS ORDER PAYMENT",
        "AMAZON PURCHASE PAYMENT",
        "POS SLOT NIGERIA PHONE PURCHASE",
        "POS COMPUTER VILLAGE ACCESSORY",
        "POS MARKET CLOTHES PURCHASE",
        "POS BOUTIQUE FASHION PAYMENT",
        "POS SHOE STORE PURCHASE",
        "POS ELECTRONICS STORE PAYMENT",
        "POS GAME STORE PURCHASE",
        "POS IKEJA MALL SHOPPING",
        "POS PALMS MALL PURCHASE",
        "POS LEKKI MALL SHOPPING",
        "HOUSEHOLD ITEM STORE PURCHASE",
        "FURNITURE STORE PAYMENT",
        "FABRIC MATERIAL PURCHASE",
        "POS NNPC MEGA STATION SHOP",
        "FASHION STORE ONLINE PAYMENT",
        "COSMETICS BEAUTY PURCHASE",
        "GIFT ITEM PURCHASE PAYMENT",
        "POS SUPERSTORE PURCHASE",
        "ARTISAN CRAFT PURCHASE",
        "MARKET SHOPPING PAYMENT",
    ],
    "other": [
        "INTERBANK TRANSFER TO JOHN DOE",
        "NIP TRANSFER OUTWARD PAYMENT",
        "ATM WITHDRAWAL ZENITH BANK",
        "ATM CASH WITHDRAWAL GTB",
        "BANK CHARGE MONTHLY FEE",
        "SMS ALERT CHARGE DEBIT",
        "CARD MAINTENANCE FEE",
        "STAMP DUTY CHARGE",
        "VAT CHARGE ON TRANSACTION",
        "ACCOUNT MAINTENANCE FEE",
        "CASHBACK REVERSAL CREDIT",
        "TRANSACTION REVERSAL REFUND",
        "SALARY PAYMENT CREDIT",
        "WAGES PAYMENT TRANSFER",
        "COMMISSION EARNING CREDIT",
        "USSD AIRTIME PURCHASE MTN",
        "MTN AIRTIME RECHARGE",
        "AIRTEL AIRTIME TOP UP",
        "GLO AIRTIME PURCHASE",
        "9MOBILE AIRTIME RECHARGE",
        "MISCELLANEOUS PAYMENT",
        "PEER TO PEER TRANSFER",
        "FAMILY SUPPORT TRANSFER",
        "PERSONAL TRANSFER SAVINGS",
        "UNKNOWN DEBIT TRANSACTION",
    ],
}

_sentence_model = None
_prototypes: Optional[dict]     = None
_prototype_counts: Optional[dict] = None


def _load_model() -> None:
    global _sentence_model, _prototypes, _prototype_counts

    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")

    if _prototypes is not None:
        return

    if PKL_PATH.exists():
        with open(PKL_PATH, "rb") as f:
            data = pickle.load(f)

        if isinstance(data, dict):
            _prototypes      = {k: np.array(v, dtype=np.float32) for k, v in data.items()}
            _prototype_counts = {k: 25 for k in _prototypes}   # treat loaded protos as 25-sample avg
        elif isinstance(data, (list, np.ndarray)):
            arr = np.array(data, dtype=np.float32)
            if arr.ndim == 2 and arr.shape[0] == len(CATEGORIES):
                _prototypes      = {cat: arr[i] for i, cat in enumerate(CATEGORIES)}
                _prototype_counts = {cat: 25 for cat in CATEGORIES}
            else:
                _build_default_prototypes()
        else:
            _build_default_prototypes()
    else:
        _build_default_prototypes()


def _build_default_prototypes() -> None:
    """
    Encode every seed sentence individually and average them per category.
    This gives a much richer prototype than encoding a single keyword string.
    """
    global _prototypes, _prototype_counts

    all_sentences = [s for seeds in _CATEGORY_SEEDS.values() for s in seeds]
    all_embeddings = _sentence_model.encode(
        all_sentences, show_progress_bar=False, batch_size=64
    )

    _prototypes      = {}
    _prototype_counts = {}
    idx = 0
    for cat, seeds in _CATEGORY_SEEDS.items():
        n = len(seeds)
        cat_embs = all_embeddings[idx : idx + n]
        _prototypes[cat]       = cat_embs.mean(axis=0).astype(np.float32)
        _prototype_counts[cat] = n
        idx += n

    # Persist so we don't rebuild every restart
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    persisted = {k: v.tolist() for k, v in _prototypes.items()}
    with open(PKL_PATH, "wb") as f:
        pickle.dump(persisted, f)


def classify_transaction(description: str) -> dict:
    _load_model()
    embedding = _sentence_model.encode([description], show_progress_bar=False)
    return _predict(embedding)[0]


def classify_batch(descriptions: list) -> list:
    _load_model()
    if not descriptions:
        return []
    embeddings = _sentence_model.encode(descriptions, show_progress_bar=False, batch_size=64)
    return _predict(embeddings)


def _predict(embeddings: np.ndarray) -> list:
    categories   = list(_prototypes.keys())
    proto_matrix = np.array([_prototypes[c] for c in categories], dtype=np.float32)
    sims         = cosine_similarity(embeddings, proto_matrix)
    results      = []
    for row in sims:
        best_idx   = int(np.argmax(row))
        raw_sim    = float(row[best_idx])
        confidence = round((raw_sim + 1.0) / 2.0, 4)
        results.append({"category": categories[best_idx], "confidence": confidence})
    return results


def update_prototype(category: str, description: str) -> None:
    """Online update — each user correction nudges the prototype toward the corrected embedding."""
    _load_model()
    if category not in _prototypes:
        return

    new_emb = _sentence_model.encode([description], show_progress_bar=False)[0].astype(np.float32)
    n = _prototype_counts.get(category, 1)
    _prototypes[category]      = (_prototypes[category] * n + new_emb) / (n + 1)
    _prototype_counts[category] = n + 1

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    persisted = {k: v.tolist() for k, v in _prototypes.items()}
    with open(PKL_PATH, "wb") as f:
        pickle.dump(persisted, f)
