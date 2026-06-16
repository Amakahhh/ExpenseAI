"""
Evaluates the keyword classifier against a labeled test set and writes
metrics to app/ml/metrics.json (or services/metrics.json as fallback).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from services.classifier import classify_transaction, CATEGORIES

# ── Labeled test set ─────────────────────────────────────────────────────────
# 10+ examples per category; realistic Nigerian bank statement descriptions.
TEST_DATA = [
    # food
    ("POS PURCHASE CHICKEN REPUBLIC IKEJA", "food"),
    ("JUMIA FOOD DELIVERY PAYMENT", "food"),
    ("BOLT FOOD ORDER LEKKI", "food"),
    ("POS SHOPRITE SUPERMARKET MARYLAND", "food"),
    ("TRANSFER TO MAMA PUT BUKA AJAH", "food"),
    ("PAYMENT DOMINOS PIZZA VI", "food"),
    ("POS KFC VICTORIA ISLAND", "food"),
    ("GROCERY STORE PURCHASE SURULERE", "food"),
    ("SWEET SENSATION RESTAURANT PAYMENT", "food"),
    ("POS COLDSTONE CREAMERY LEKKI", "food"),
    ("COLD STONE ICE CREAM PURCHASE", "food"),
    ("CAFETERIA PAYMENT OFFICE CANTEEN", "food"),
    # harder food cases (short / abbreviated)
    ("FOOD PURCHASE", "food"),
    ("KFC", "food"),
    ("SHOPRITE", "food"),
    ("RESTAURANT PAYMENT LEKKI", "food"),
    ("BAKERY PURCHASE", "food"),
    ("SHAWARMA SPOT IKEJA", "food"),

    # transport
    ("UBER TRIP PAYMENT LAGOS", "transport"),
    ("BOLT RIDE ABUJA WUSE", "transport"),
    ("TOTAL PETROL FILLING STATION IKEJA", "transport"),
    ("FUEL PURCHASE OANDO STATION VI", "transport"),
    ("AIR PEACE FLIGHT TICKET LAGOS ABJ", "transport"),
    ("GIGM BUS TICKET BENIN LAGOS", "transport"),
    ("CAR PARK FEE VICTORIA ISLAND", "transport"),
    ("TOLL GATE PAYMENT LEKKI EPRESS", "transport"),
    ("AUTO MECHANIC SERVICE SURULERE", "transport"),
    ("TAXIFY RIDE PAYMENT", "transport"),
    ("PETROL PURCHASE NNPC STATION", "transport"),
    ("VEHICLE SERVICE SPARE PARTS", "transport"),
    # harder transport cases
    ("UBER", "transport"),
    ("BOLT RIDE PAYMENT", "transport"),
    ("UBER*TRIP", "transport"),
    ("FUEL PURCHASE NNPC", "transport"),
    ("PETROL", "transport"),
    ("FILLING STATION PAYMENT", "transport"),

    # entertainment
    ("NETFLIX SUBSCRIPTION MONTHLY", "entertainment"),
    ("SPOTIFY SUBSCRIPTION RENEWAL", "entertainment"),
    ("BET9JA DEPOSIT SPORTS BETTING", "entertainment"),
    ("SPORTYBET WALLET FUNDING", "entertainment"),
    ("SILVERBIRD CINEMA TICKET PURCHASE", "entertainment"),
    ("SHOWMAX SUBSCRIPTION PAYMENT", "entertainment"),
    ("BETWAY DEPOSIT ONLINE BETTING", "entertainment"),
    ("FILMHOUSE CINEMA IKEJA TICKET", "entertainment"),
    ("1XBET ACCOUNT DEPOSIT", "entertainment"),
    ("PLAYSTATION NETWORK SUBSCRIPTION", "entertainment"),
    ("YOUTUBE PREMIUM SUBSCRIPTION", "entertainment"),
    ("BOOMPLAY MUSIC SUBSCRIPTION", "entertainment"),
    # harder entertainment cases
    ("NETFLIX", "entertainment"),
    ("SPOTIFY", "entertainment"),
    ("BET9JA DEPOSIT", "entertainment"),
    ("SHOWMAX", "entertainment"),
    ("SILVERBIRD CINEMA", "entertainment"),
    ("BETWAY", "entertainment"),

    # bills
    ("EKEDC ELECTRICITY TOKEN PURCHASE", "bills"),
    ("MTN AIRTIME RECHARGE 1000", "bills"),
    ("DSTV SUBSCRIPTION RENEWAL", "bills"),
    ("SPECTRANET INTERNET SUBSCRIPTION", "bills"),
    ("IKEDC PREPAID TOKEN PAYMENT", "bills"),
    ("AIRTEL DATA BUNDLE PURCHASE", "bills"),
    ("GOTV MONTHLY SUBSCRIPTION", "bills"),
    ("HOUSE RENT PAYMENT DECEMBER", "bills"),
    ("WATER BILL PAYMENT LSWC", "bills"),
    ("AIRTIME TOPUP GLO NETWORK", "bills"),
    ("PHED ELECTRICITY PAYMENT", "bills"),
    ("NHIS HEALTH INSURANCE PREMIUM", "bills"),
    # harder bills cases
    ("DSTV", "bills"),
    ("GOTV PAYMENT", "bills"),
    ("AIRTIME", "bills"),
    ("DATA PURCHASE MTN", "bills"),
    ("PREPAID METER TOKEN", "bills"),
    ("INTERNET DATA SUBSCRIPTION", "bills"),

    # health
    ("MEDPLUS PHARMACY DRUG PURCHASE", "health"),
    ("GENERAL HOSPITAL CONSULTATION FEE", "health"),
    ("PATHCARE LABORATORY TEST PAYMENT", "health"),
    ("DENTAL CLINIC CHECKUP PAYMENT", "health"),
    ("HEALTHPLUS PHARMACY MEDICATION", "health"),
    ("PRIVATE HOSPITAL ADMISSION FEE", "health"),
    ("ULTRASOUND SCAN PAYMENT", "health"),
    ("GYM MEMBERSHIP FITNESS CENTER", "health"),
    ("PHARMACY DRUG PURCHASE CHEMIST", "health"),
    ("EYE CLINIC OPTICIAN PAYMENT", "health"),
    ("VACCINATION IMMUNIZATION PAYMENT", "health"),
    ("BLOOD TEST MEDICAL LABORATORY", "health"),
    # harder health cases
    ("PHARMACY", "health"),
    ("HOSPITAL BILL", "health"),
    ("CLINIC CONSULTATION", "health"),
    ("MEDPLUS", "health"),
    ("GYM MEMBERSHIP PAYMENT", "health"),
    ("VACCINATION PAYMENT", "health"),

    # education
    ("JAMB REGISTRATION FEE PAYMENT", "education"),
    ("WAEC EXAMINATION REGISTRATION", "education"),
    ("SCHOOL FEES PAYMENT UNIVERSITY", "education"),
    ("UDEMY ONLINE COURSE PURCHASE", "education"),
    ("TUITION PAYMENT SECOND SEMESTER", "education"),
    ("IELTS REGISTRATION FEE PAYMENT", "education"),
    ("COURSERA SUBSCRIPTION PAYMENT", "education"),
    ("TRAINING WORKSHOP FEE PAYMENT", "education"),
    ("JAMB UTME FEE PAYMENT 2025", "education"),
    ("SCHOOL FEE POLYTECHNIC PAYMENT", "education"),
    ("LESSON PAYMENT COACHING CLASS", "education"),
    ("PROFESSIONAL CERTIFICATION FEE", "education"),
    # harder education cases
    ("SCHOOL FEE", "education"),
    ("WAEC", "education"),
    ("JAMB", "education"),
    ("TUITION", "education"),
    ("UDEMY COURSE", "education"),
    ("EXAM REGISTRATION FEE", "education"),

    # shopping
    ("JUMIA ONLINE SHOPPING PURCHASE", "shopping"),
    ("KONGA PRODUCT PURCHASE PAYMENT", "shopping"),
    ("SLOT NIGERIA PHONE PURCHASE", "shopping"),
    ("ALIEXPRESS ORDER PAYMENT", "shopping"),
    ("AMAZON PURCHASE DELIVERY", "shopping"),
    ("BOUTIQUE FASHION CLOTHING STORE", "shopping"),
    ("SHOE STORE FOOTWEAR PURCHASE", "shopping"),
    ("SHEIN ONLINE PURCHASE", "shopping"),
    ("FURNITURE STORE HOME APPLIANCE", "shopping"),
    ("COSMETICS BEAUTY STORE PURCHASE", "shopping"),
    ("ELECTRONICS STORE GADGET PURCHASE", "shopping"),
    ("JIJI MARKETPLACE PURCHASE", "shopping"),
    # harder shopping cases
    ("JUMIA", "shopping"),
    ("AMAZON", "shopping"),
    ("SHEIN PURCHASE", "shopping"),
    ("CLOTHING STORE PURCHASE", "shopping"),
    ("ONLINE SHOPPING", "shopping"),
    ("ELECTRONICS PURCHASE", "shopping"),

    # memo extraction cases (the key insight — purpose at end of transfer description)
    ("Transfer to OGECHUKWU PRECIOUS OKIKA | OPay | 9067451387 | For cake", "food"),
    ("Sent to JOHN DOE | GTBank | 0801234567 | For fuel", "transport"),
    ("Transfer to JANE | PalmPay | 0901234567 | For school fees", "education"),
    ("Transfer to MIKE | Kuda | 0712345678 | Netflix subscription", "entertainment"),
    ("Transfer to MRS ADEOLA | Opay | 0813456789 | For hospital bill", "health"),
    ("Transfer to EMEKA | 0705432198 | For rent", "bills"),
    ("Sent to BLESSING | OPay | 0901234567 | Clothing shopping", "shopping"),
    ("Transfer to DAVID | Access | 0811234567 | For lunch", "food"),
    ("Transfer to CHUKWU | GTB | 0701234567 | For drugs", "health"),
    ("Sent to MAMA | OPay | 08012345 | Feeding money", "food"),

    # other
    ("NIP TRANSFER TO ACCESS BANK", "other"),
    ("INTERBANK TRANSFER ZENITH BANK", "other"),
    ("ATM WITHDRAWAL FIRST BANK", "other"),
    ("BANK CHARGE SMS ALERT FEE", "other"),
    ("STAMP DUTY CHARGE ACCOUNT", "other"),
    ("POS CASH WITHDRAWAL AGENT", "other"),
    ("TRANSACTION REVERSAL CREDIT", "other"),
    ("SALARY PAYMENT DECEMBER 2025", "other"),
    ("ACCOUNT MAINTENANCE FEE ANNUAL", "other"),
    ("CARD MAINTENANCE FEE DEBIT", "other"),
    ("TRANSFER FROM OPAY WALLET", "other"),
    ("MOBILE TRANSFER PERSONAL", "other"),
]

# ── Run classifier ────────────────────────────────────────────────────────────
y_true, y_pred, confidences = [], [], []

for description, true_label in TEST_DATA:
    result = classify_transaction(description)
    y_true.append(true_label)
    y_pred.append(result["category"])
    confidences.append(result["confidence"])

# ── Compute metrics ───────────────────────────────────────────────────────────
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

accuracy   = accuracy_score(y_true, y_pred)
precision  = precision_score(y_true, y_pred, average="weighted", zero_division=0)
recall     = recall_score(y_true, y_pred, average="weighted", zero_division=0)
f1         = f1_score(y_true, y_pred, average="weighted", zero_division=0)
avg_conf   = sum(confidences) / len(confidences)

report = classification_report(
    y_true, y_pred, labels=CATEGORIES, zero_division=0, output_dict=True
)

cm = confusion_matrix(y_true, y_pred, labels=CATEGORIES)

# ── Build output dict ─────────────────────────────────────────────────────────
metrics = {
    "overall": {
        "accuracy":           round(accuracy,  4),
        "weighted_precision": round(precision, 4),
        "weighted_recall":    round(recall,    4),
        "weighted_f1":        round(f1,        4),
        "avg_confidence":     round(avg_conf,  4),
        "test_samples":       len(TEST_DATA),
    },
    "per_category": {
        cat: {
            "precision": round(report[cat]["precision"], 4),
            "recall":    round(report[cat]["recall"],    4),
            "f1_score":  round(report[cat]["f1-score"],  4),
            "support":   int(report[cat]["support"]),
        }
        for cat in CATEGORIES
    },
    "confusion_matrix": {
        "labels": CATEGORIES,
        "matrix": cm.tolist(),
    },
}

# ── Save metrics.json ─────────────────────────────────────────────────────────
out_dir = os.path.join(os.path.dirname(__file__), "app", "ml")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "metrics.json")

with open(out_path, "w") as f:
    json.dump(metrics, f, indent=2)

print(f"Saved -> {out_path}")
print()
print("=" * 50)
print(f"  Accuracy           : {accuracy*100:.1f}%")
print(f"  Weighted Precision : {precision*100:.1f}%")
print(f"  Weighted Recall    : {recall*100:.1f}%")
print(f"  Weighted F1        : {f1*100:.1f}%")
print(f"  Avg Confidence     : {avg_conf*100:.1f}%")
print(f"  Test samples       : {len(TEST_DATA)}")
print("=" * 50)
print()
print("Per-category breakdown:")
for cat in CATEGORIES:
    r = report[cat]
    print(f"  {cat:<15} P={r['precision']:.2f}  R={r['recall']:.2f}  F1={r['f1-score']:.2f}  (n={int(r['support'])})")
