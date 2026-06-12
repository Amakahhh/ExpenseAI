from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.database import get_db, Transaction, User
from routes.auth import get_current_user
from services.classifier import update_prototype

router = APIRouter()

VALID_CATEGORIES = frozenset(
    ["food", "transport", "entertainment", "bills", "health", "education", "shopping", "other"]
)


class CorrectRequest(BaseModel):
    transaction_id: int
    correct_category: str


@router.post("")
def correct_transaction(
    req: CorrectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.correct_category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )

    tx = db.query(Transaction).filter(
        Transaction.id == req.transaction_id,
        Transaction.user_id == current_user.id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    tx.is_corrected = True
    tx.corrected_category = req.correct_category
    db.commit()

    update_prototype(req.correct_category, tx.description)

    return {
        "success":        True,
        "transaction_id": req.transaction_id,
        "category":       req.correct_category,
    }
