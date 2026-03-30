import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConnectionStatus(str, enum.Enum):
    pending = "pending"
    connected = "connected"
    expired = "expired"
    error = "error"


class SalaryFrequency(str, enum.Enum):
    weekly = "weekly"
    fortnightly = "fortnightly"
    monthly = "monthly"
    irregular = "irregular"


class BankingConnection(Base):
    __tablename__ = "banking_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    truelayer_connection_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    access_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus), default=ConnectionStatus.pending
    )

    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="banking_connections")


class BankingAnalysis(Base):
    __tablename__ = "banking_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # Income analysis
    salary_frequency: Mapped[SalaryFrequency | None] = mapped_column(
        Enum(SalaryFrequency), nullable=True
    )
    salary_regularity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_variation_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Expense analysis
    flagged_expenses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    estimated_monthly_rent: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    total_monthly_commitments: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    analysis_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="banking_analyses")
