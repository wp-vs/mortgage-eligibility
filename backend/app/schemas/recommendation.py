from datetime import datetime

from pydantic import BaseModel


class ProductSummary(BaseModel):
    product_id: int
    lender_name: str
    product_name: str
    rate: float
    product_type: str
    initial_period_months: int
    max_ltv: float
    arrangement_fee: float
    estimated_monthly_payment: float | None = None


class RecommendationResponse(BaseModel):
    id: int
    rank: int
    match_score: float
    match_reasons: list[str] | None
    unmet_criteria: list[str] | None
    customer_summary_text: str | None
    broker_summary_text: str | None
    product: ProductSummary
    broker_approved: bool | None
    broker_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BrokerReviewRequest(BaseModel):
    approved: bool
    notes: str | None = None


class RecommendationListResponse(BaseModel):
    customer_id: int
    recommendations: list[RecommendationResponse]
