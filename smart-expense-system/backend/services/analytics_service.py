from collections import defaultdict
from typing import Optional
from sqlalchemy.orm import Session
from models.database import Transaction


def compute_analytics(db: Session, session_id: Optional[str] = None) -> dict:
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    transactions = query.all()

    if not transactions:
        return {
            "by_category": [],
            "by_month": [],
            "top_merchants": [],
            "total_spend": 0.0,
            "transaction_count": 0,
        }

    category_agg: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
    monthly_agg: dict = defaultdict(float)
    merchant_agg: dict = defaultdict(lambda: {"total": 0.0, "count": 0, "cat_counts": {}})
    total_spend = 0.0

    for tx in transactions:
        cat = tx.corrected_category if tx.is_corrected else tx.predicted_category
        amt = abs(tx.amount or 0.0)
        is_income = (tx.transaction_type or "debit") == "credit"

        # Income transactions are excluded from spend breakdowns
        if not is_income:
            category_agg[cat]["total"] += amt
            category_agg[cat]["count"] += 1

            month = _parse_month(tx.date)
            monthly_agg[month] += amt

            merchant = _extract_merchant(tx.description)
            merchant_agg[merchant]["total"] += amt
            merchant_agg[merchant]["count"] += 1
            merchant_agg[merchant]["cat_counts"][cat] = merchant_agg[merchant]["cat_counts"].get(cat, 0) + 1

            total_spend += amt

    by_category = [
        {"category": cat, "total": round(v["total"], 2), "count": v["count"]}
        for cat, v in sorted(category_agg.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    by_month = [
        {"month": month, "total": round(total, 2)}
        for month, total in sorted(monthly_agg.items())
        if month != "Unknown"
    ]

    top_merchants = sorted(
        [
            {
                "merchant": m,
                "total":    round(v["total"], 2),
                "count":    v["count"],
                "category": max(v["cat_counts"], key=v["cat_counts"].get) if v["cat_counts"] else "other",
            }
            for m, v in merchant_agg.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )[:10]

    expense_count = sum(1 for tx in transactions if (tx.transaction_type or "debit") != "credit")
    income_count  = len(transactions) - expense_count
    total_income  = sum(abs(tx.amount or 0.0) for tx in transactions
                        if (tx.transaction_type or "debit") == "credit")

    return {
        "by_category":      by_category,
        "by_month":         by_month,
        "top_merchants":    top_merchants,
        # total_spend = sum of all debit rows (OWealth excluded at parse time)
        "total_spend":      round(total_spend, 2),
        "total_income":     round(total_income, 2),
        "transaction_count": expense_count,
        "income_count":     income_count,
        "total_count":      len(transactions),   # debit + credit combined
    }


def _parse_month(date_val) -> str:
    if not date_val:
        return "Unknown"
    s = str(date_val).strip()
    if len(s) >= 7 and s not in ("nan", "None", ""):
        try:
            return s[:7]
        except Exception:
            pass
    return "Unknown"


def _extract_merchant(description: str) -> str:
    words = str(description).strip().split()
    return " ".join(words[:3]) if len(words) >= 3 else description[:24]
