import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StressRateMethod(str, enum.Enum):
    """How a lender computes the stress test rate."""

    svr_plus_margin = "svr_plus_margin"  # product.svr_rate + stress_margin_pct
    absolute = "absolute"  # use stress_rate_pct directly
    reversion_plus = "reversion_plus"  # product SVR + margin, floor at stress_rate_pct


class LenderAffordability(Base):
    """Per-lender affordability configuration.

    Represents the policy a lender applies when deciding how much they are
    willing to lend: income multiples (standard + enhanced above a threshold),
    the stress rate method, and a debt-to-income cap.

    These values are the inputs to the affordability calculation; they do not
    change per product. Seeded with publicly-known approximations — brokers
    should verify before going live.
    """

    __tablename__ = "lender_affordability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lender_id: Mapped[int] = mapped_column(
        ForeignKey("lenders.id"), nullable=False, unique=True
    )

    income_multiple_standard: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False, default=4.5
    )
    income_multiple_enhanced: Mapped[float | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    enhanced_income_threshold: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    stress_rate_method: Mapped[StressRateMethod] = mapped_column(
        Enum(StressRateMethod),
        default=StressRateMethod.svr_plus_margin,
        nullable=False,
    )
    stress_rate_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=8.0
    )
    stress_margin_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=1.0
    )

    # Max fraction of net monthly income that can go to committed debt + housing.
    debt_to_income_cap_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=45.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lender: Mapped["Lender"] = relationship(back_populates="affordability")
