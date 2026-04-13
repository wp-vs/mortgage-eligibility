import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CriteriaGrade(str, enum.Enum):
    yes = "yes"
    no = "no"
    refer = "refer"
    condition = "condition"
    yes_by_exception = "yes_by_exception"


class LendingType(str, enum.Enum):
    residential = "residential"
    buy_to_let = "buy_to_let"


class EligibilityCriteria(Base):
    __tablename__ = "eligibility_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"), nullable=False)

    source_crit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criterion_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[CriteriaGrade | None] = mapped_column(
        Enum(CriteriaGrade), nullable=True
    )
    details_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    lending_type: Mapped[LendingType] = mapped_column(
        Enum(LendingType), default=LendingType.residential
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    lender: Mapped["Lender"] = relationship(back_populates="criteria")
