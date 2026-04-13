from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.banking import BankingAnalysis
from app.models.broker import Broker
from app.models.customer import Customer, CustomerStatus
from app.models.lender import Lender
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.schemas.broker import BrokerLogin, BrokerTokenResponse, CaseSummary
from app.schemas.recommendation import BrokerReviewRequest

router = APIRouter()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


@router.post("/login", response_model=BrokerTokenResponse)
async def broker_login(request: BrokerLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Broker).where(Broker.email == request.email))
    broker = result.scalar_one_or_none()
    if not broker or not _verify_password(request.password, broker.hashed_password):
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

    # Get recommendations joined with product + lender so the dashboard
    # can render the full advisor-grade details in one hop.
    rec_result = await db.execute(
        select(Recommendation, Product, Lender)
        .join(Product, Recommendation.product_id == Product.id)
        .join(Lender, Product.lender_id == Lender.id)
        .where(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.rank)
    )

    recommendations = []
    for rec, product, lender in rec_result.all():
        recommendations.append(
            {
                "id": rec.id,
                "rank": rec.rank,
                "match_score": float(rec.match_score),
                "match_reasons": rec.match_reasons,
                "unmet_criteria": rec.unmet_criteria,
                "customer_summary_text": rec.customer_summary_text,
                "broker_summary_text": rec.broker_summary_text,
                "broker_approved": rec.broker_approved,
                "broker_notes": rec.broker_notes,
                "total_cost_initial": float(rec.total_cost_initial)
                if rec.total_cost_initial is not None
                else None,
                "effective_rate": float(rec.effective_rate)
                if rec.effective_rate is not None
                else None,
                "amortised_fee_pct": float(rec.amortised_fee_pct)
                if rec.amortised_fee_pct is not None
                else None,
                "affordability_max_loan": float(rec.affordability_max_loan)
                if rec.affordability_max_loan is not None
                else None,
                "binding_affordability_constraint": rec.binding_affordability_constraint,
                "stress_rate_used": float(rec.stress_rate_used)
                if rec.stress_rate_used is not None
                else None,
                "complexity_reasons": rec.complexity_reasons or [],
                "requires_broker_review": rec.requires_broker_review,
                "product": {
                    "product_id": product.id,
                    "lender_name": lender.name,
                    "product_name": product.name,
                    "rate": float(product.rate),
                    "product_type": product.product_type.value,
                    "initial_period_months": product.initial_period_months,
                    "max_ltv": float(product.max_ltv),
                    "arrangement_fee": float(product.arrangement_fee),
                },
            }
        )

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
