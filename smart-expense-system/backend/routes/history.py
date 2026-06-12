from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from models.database import get_db, UploadSession, Transaction, User
from routes.auth import get_current_user

router = APIRouter()


@router.get("")
def get_sessions(
    session_ids: Optional[str] = Query(None, description="Comma-separated session IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(UploadSession).filter(UploadSession.user_id == current_user.id)
    if session_ids:
        ids = [s.strip() for s in session_ids.split(",") if s.strip()]
        query = query.filter(UploadSession.session_id.in_(ids))
    sessions = query.order_by(UploadSession.upload_date.desc()).all()

    return {
        "sessions": [
            {
                "session_id":         s.session_id,
                "filename":           s.filename,
                "upload_date":        s.upload_date.isoformat() if s.upload_date else None,
                "total_transactions": s.total_transactions,
                "total_spend":        s.total_spend,
                "total_income":       s.total_income,
                "date_range_start":   s.date_range_start,
                "date_range_end":     s.date_range_end,
                "top_category":       s.top_category,
            }
            for s in sessions
        ]
    }


@router.get("/compare")
def compare_sessions(
    session_ids: str = Query(..., description="Comma-separated session IDs to compare"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ids = [s.strip() for s in session_ids.split(",") if s.strip()]
    if not ids:
        return {"sessions": []}

    results = []
    for sid in ids:
        txs = (
            db.query(Transaction)
            .filter(
                Transaction.session_id == sid,
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == "debit",
            )
            .all()
        )
        cat_totals: dict = defaultdict(float)
        total = 0.0
        for tx in txs:
            cat = tx.corrected_category if tx.is_corrected else tx.predicted_category
            amt = abs(tx.amount or 0.0)
            cat_totals[cat] += amt
            total += amt

        results.append({
            "session_id":  sid,
            "total_spend": round(total, 2),
            "by_category": [
                {"category": cat, "total": round(amt, 2)}
                for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
            ],
        })

    return {"sessions": results}
