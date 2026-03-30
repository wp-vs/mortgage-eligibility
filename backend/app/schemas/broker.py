from pydantic import BaseModel


class BrokerLogin(BaseModel):
    email: str
    password: str


class BrokerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CaseSummary(BaseModel):
    customer_id: int
    customer_name: str | None
    status: str
    has_banking_analysis: bool
    recommendation_count: int
    created_at: str
