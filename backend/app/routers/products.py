from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.lender import Lender
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.services.eligibility import EligibilityEngine
from app.services.recommendation import RecommendationService
from app.services.suitability_letter import SuitabilityLetterGenerator

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
        select(Recommendation, Product, Lender)
        .join(Product, Recommendation.product_id == Product.id)
        .join(Lender, Product.lender_id == Lender.id)
        .where(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.rank)
    )
    rows = result.all()

    out = []
    for rec, product, lender in rows:
        out.append(
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

    return {"customer_id": customer_id, "recommendations": out}


@router.get("/recommendations/{recommendation_id}/suitability-letter.pdf")
async def suitability_letter(
    recommendation_id: int, db: AsyncSession = Depends(get_db)
):
    """Generate and stream a suitability letter PDF for a recommendation.

    The PDF documents the affordability assessment (binding constraint,
    stress rate), the products considered, and the recommended product
    with justification based on lowest total cost over the initial period.
    """
    result = await db.execute(
        select(Recommendation, Product, Lender)
        .join(Product, Recommendation.product_id == Product.id)
        .join(Lender, Product.lender_id == Lender.id)
        .where(Recommendation.id == recommendation_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec, product, lender = row

    customer_res = await db.execute(
        select(Customer).where(Customer.id == rec.customer_id)
    )
    customer = customer_res.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Other options = every recommendation for this customer, in rank order.
    others_res = await db.execute(
        select(Recommendation, Product, Lender)
        .join(Product, Recommendation.product_id == Product.id)
        .join(Lender, Product.lender_id == Lender.id)
        .where(Recommendation.customer_id == rec.customer_id)
        .order_by(Recommendation.rank)
    )
    other_options = []
    for other_rec, other_product, other_lender in others_res.all():
        other_options.append(
            {
                "rank": other_rec.rank,
                "lender_name": other_lender.name,
                "product_name": other_product.name,
                "rate": float(other_product.rate),
                "arrangement_fee": float(other_product.arrangement_fee),
                "initial_period_months": other_product.initial_period_months,
                "total_cost_initial": float(other_rec.total_cost_initial)
                if other_rec.total_cost_initial is not None
                else None,
            }
        )

    generator = SuitabilityLetterGenerator()
    pdf_bytes = generator.generate(
        customer=customer,
        recommendation=rec,
        product=product,
        lender_name=lender.name,
        other_options=other_options,
    )

    filename = f"suitability-letter-rec-{rec.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
