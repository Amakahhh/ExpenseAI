from fastapi import APIRouter
from pydantic import BaseModel
from services.classifier import classify_transaction

router = APIRouter()


class CategorizeRequest(BaseModel):
    description: str


@router.post("")
def categorize_single(req: CategorizeRequest):
    result = classify_transaction(req.description)
    return {
        "description": req.description,
        "category":    result["category"],
        "confidence":  result["confidence"],
    }
