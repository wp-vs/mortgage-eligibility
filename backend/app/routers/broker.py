from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
import jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.banking import BankingAnalysis
from app.models.broker import Broker
from app.models.customer import Customer, CustomerStatus
from app.models.recommendation import Recommendation
from app.schemas.broker import BrokerLogin, BrokerTokenResponse, CaseSummary
from app.schemas.recommendation import BrokerReviewRequest

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", response_model=BrokerTokenResponse)
async def broker_login(request: BrokerLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Broker).where(Broker.email == request.email))
    broker = result.scalar_one_or_none()
    if not broker or not pwd_context.verify(request.password, broker.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": str(broker.id), "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return BrokerTokenResponse(access_token=token)


@router.get("/cases")
async def list_cases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Customer).where(
            Customer.status.in_([CustomerStatus.submitted, CustomerStatus.reviewed])
        )
    )
    customers = result.scalars().all()

    cases = []
    for c in customers:
        # Count recommendations
        rec_result = await db.execute(
            select(func.count(Recommendation.id)).where(
                Recommendation.customer_id == c.id
            )
        )
        rec_count = rec_result.scalar()

        # Check banking analysis
        ba_result = await db.execute(
            select(func.count(BankingAnalysis.id)).where(
                BankingAnalysis.customer_id == c.id
            )
        )
        has_banking = ba_result.scalar() > 0

        cases.append(
            CaseSummary(
                customer_id=c.id,
                customer_name=c.full_name,
                status=c.status.value,
                has_banking_analysis=has_banking,
                recommendation_count=rec_count,
                created_at=c.created_at.isoformat(),
            )
        )

    return {"cases": cases}


@router.get("/cases/{customer_id}")
async def get_case_detail(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get banking analysis
    ba_result = await db.execute(
        select(BankingAnalysis)
        .where(BankingAnalysis.customer_id == customer_id)
        .order_by(BankingAnalysis.analysis_date.desc())
    )
    banking_analysis = ba_result.scalar_one_or_none()

    # Get recommendations
    rec_result = await db.execute(
        select(Recommendation)
        .where(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.rank)
    )
    recommendations = rec_result.scalars().all()

    return {
        "customer": customer,
        "banking_analysis": banking_analysis,
        "recommendations": recommendations,
    }


@router.post("/cases/{customer_id}/recommendations/{rec_id}/review")
async def review_recommendation(
    customer_id: int,
    rec_id: int,
    review: BrokerReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == rec_id,
            Recommendation.customer_id == customer_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.broker_approved = review.approved
    rec.broker_notes = review.notes
    rec.reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    # Update customer status if all recommendations reviewed
    all_recs = await db.execute(
        select(Recommendation).where(Recommendation.customer_id == customer_id)
    )
    all_reviewed = all(r.reviewed_at is not None for r in all_recs.scalars().all())
    if all_reviewed:
        cust_result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = cust_result.scalar_one()
        customer.status = CustomerStatus.reviewed
        await db.commit()

    return {"status": "reviewed"}
