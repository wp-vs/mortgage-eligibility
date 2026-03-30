import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductType(str, enum.Enum):
    fixed = "fixed"
    variable = "variable"
    tracker = "tracker"
    discount = "discount"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)

    # Rates
    rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "fixed", "variable"
    initial_period_months: Mapped[int] = mapped_column(Integer, nullable=False)
    svr_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # LTV and loan limits
    min_ltv: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_ltv: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    min_loan: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_loan: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Fees
    arrangement_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    booking_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    cashback: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    # Eligibility basics
    min_income: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_income_multiple: Mapped[float] = mapped_column(Numeric(4, 2), default=4.5)
    first_time_buyer_eligible: Mapped[bool] = mapped_column(Boolean, default=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    lender: Mapped["Lender"] = relationship(back_populates="products")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="product")
