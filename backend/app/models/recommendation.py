from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    match_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unmet_criteria: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    customer_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    broker_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Broker review
    broker_id: Mapped[int | None] = mapped_column(
        ForeignKey("brokers.id"), nullable=True
    )
    broker_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    broker_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="recommendations")
    product: Mapped["Product"] = relationship(back_populates="recommendations")
    broker: Mapped["Broker | None"] = relationship(back_populates="reviews")
