from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.database import get_db
from services.analytics_service import compute_analytics

router = APIRouter()


@router.get("")
def get_analytics(
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return compute_analytics(db, session_id)
