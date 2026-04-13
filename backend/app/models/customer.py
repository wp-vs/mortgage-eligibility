import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmploymentType(str, enum.Enum):
    employed = "employed"
    self_employed = "self_employed"
    contractor = "contractor"
    retired = "retired"
    other = "other"


class PropertyType(str, enum.Enum):
    detached = "detached"
    semi_detached = "semi_detached"
    terraced = "terraced"
    flat = "flat"
    bungalow = "bungalow"
    new_build = "new_build"
    other = "other"


class MortgageType(str, enum.Enum):
    purchase = "purchase"
    remortgage = "remortgage"


class CustomerStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"
    approved = "approved"
    declined = "declined"


class CreditProfile(str, enum.Enum):
    clean = "clean"
    minor_adverse = "minor_adverse"
    major_adverse = "major_adverse"
    unknown = "unknown"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Mortgage details
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(EmploymentType), nullable=True
    )
    annual_income: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    property_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    property_type: Mapped[PropertyType | None] = mapped_column(
        Enum(PropertyType), nullable=True
    )
    mortgage_type: Mapped[MortgageType | None] = mapped_column(
        Enum(MortgageType), nullable=True
    )
    mortgage_term_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_time_buyer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    property_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Credit & property detail (advisor-grade)
    credit_profile: Mapped[CreditProfile] = mapped_column(
        Enum(CreditProfile), default=CreditProfile.unknown, nullable=False
    )
    property_subtype: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus), default=CustomerStatus.in_progress
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")
    banking_connections: Mapped[list["BankingConnection"]] = relationship(
        back_populates="customer"
    )
    banking_analyses: Mapped[list["BankingAnalysis"]] = relationship(
        back_populates="customer"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="customer"
    )
