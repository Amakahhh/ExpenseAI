from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.database import get_db, Transaction, User
from routes.auth import get_current_user

router = APIRouter()


@router.get("")
def list_transactions(
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    txs = query.order_by(Transaction.id).all()
    return {
        "transactions": [
            {
                "id":                 t.id,
                "date":               t.date,
                "description":        t.description,
                "amount":             t.amount,
                "transaction_type":   t.transaction_type or "debit",
                "predicted_category": t.predicted_category,
                "confidence":         t.confidence,
                "is_corrected":       t.is_corrected,
                "corrected_category": t.corrected_category,
            }
            for t in txs
        ]
    }
