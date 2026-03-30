from datetime import datetime

from pydantic import BaseModel

from app.models.customer import CustomerStatus, EmploymentType, MortgageType, PropertyType


class CustomerProfileUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    employment_type: EmploymentType | None = None
    annual_income: float | None = None
    deposit_amount: float | None = None
    property_value: float | None = None
    property_type: PropertyType | None = None
    mortgage_type: MortgageType | None = None
    mortgage_term_years: int | None = None
    first_time_buyer: bool | None = None
    property_location: str | None = None


class CustomerResponse(BaseModel):
    id: int
    email: str | None
    full_name: str | None
    phone: str | None
    employment_type: EmploymentType | None
    annual_income: float | None
    deposit_amount: float | None
    property_value: float | None
    property_type: PropertyType | None
    mortgage_type: MortgageType | None
    mortgage_term_years: int | None
    first_time_buyer: bool | None
    property_location: str | None
    status: CustomerStatus
    created_at: datetime

    model_config = {"from_attributes": True}
