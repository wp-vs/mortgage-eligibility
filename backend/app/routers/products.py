from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.recommendation import Recommendation
from app.schemas.recommendation import BrokerReviewRequest, RecommendationResponse
from app.services.eligibility import EligibilityEngine
from app.services.recommendation import RecommendationService

router = APIRouter()


@router.post("/{customer_id}/match")
async def match_products(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    engine = EligibilityEngine(db)
    matches = await engine.find_matches(customer)

    rec_service = RecommendationService(db)
    recommendations = await rec_service.create_recommendations(customer, matches[:3])

    return {"customer_id": customer_id, "recommendation_count": len(recommendations)}


@router.get("/{customer_id}/recommendations")
async def get_recommendations(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.rank)
    )
    recommendations = result.scalars().all()
    return {"customer_id": customer_id, "recommendations": recommendations}
