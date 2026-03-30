from datetime import datetime

from pydantic import BaseModel

from app.models.banking import ConnectionStatus, SalaryFrequency


class BankingConnectRequest(BaseModel):
    customer_id: int


class BankingConnectResponse(BaseModel):
    auth_url: str
    connection_id: int


class BankingCallbackRequest(BaseModel):
    code: str
    connection_id: int


class FlaggedExpense(BaseModel):
    category: str
    description: str
    monthly_amount: float
    severity: str  # "info", "warning", "critical"


class BankingAnalysisResponse(BaseModel):
    id: int
    customer_id: int
    salary_frequency: SalaryFrequency | None
    salary_regularity_score: int | None
    average_salary: float | None
    salary_variation_pct: float | None
    flagged_expenses: list[FlaggedExpense] | None
    estimated_monthly_rent: float | None
    total_monthly_commitments: float | None
    analysis_date: datetime

    model_config = {"from_attributes": True}


class BankingConnectionResponse(BaseModel):
    id: int
    customer_id: int
    provider_name: str | None
    status: ConnectionStatus
    connected_at: datetime | None

    model_config = {"from_attributes": True}
