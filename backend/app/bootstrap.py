"""Startup bootstrap — create tables and seed baseline data.

Runs on app startup so that local dev with SQLite "just works": delete the
.db file, start the backend, and the app sets itself up. In production with
Postgres, this is idempotent and cheap: tables already exist, seeding is
skipped when the rows are already present.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select

from app.database import Base, async_session, engine
from app.models import (  # noqa: F401 — import for metadata registration
    BankingAnalysis,
    BankingConnection,
    Broker,
    Conversation,
    Customer,
    EligibilityCriteria,
    Lender,
    LenderAffordability,
    Product,
    Recommendation,
)

logger = logging.getLogger(__name__)


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")


async def seed_if_empty() -> None:
    """Seed baseline data (criteria + products + affordability + broker) if missing."""
    async with async_session() as db:
        existing = await db.execute(select(Product).limit(1))
        if existing.scalar_one_or_none() is None:
            await _seed_criteria_and_products(db)

        # Affordability configs can be re-run cheaply (idempotent per-lender).
        from app.seed.seed_lender_affordability import seed_lender_affordability

        created = await seed_lender_affordability(db)
        if created:
            logger.info("Seeded affordability configs for %d lenders.", created)

        await _seed_demo_broker(db)


async def _seed_criteria_and_products(db) -> None:
    """Seed lender criteria + sample products from the Knowledge Bank parser."""
    from app.models.criteria import LendingType
    from app.seed.parse_knowledge_bank import parse_knowledge_bank

    kb_path = Path(__file__).parent.parent.parent / "Knowledge Bank ©.html"
    if kb_path.exists():
        try:
            parsed = parse_knowledge_bank(kb_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to parse Knowledge Bank HTML: %s", exc)
            parsed = []
    else:
        logger.info(
            "Knowledge Bank HTML not found at %s — skipping criteria seed.",
            kb_path,
        )
        parsed = []

    lender_name = parsed[0]["lender_name"] if parsed else "Accord"
    lender_res = await db.execute(select(Lender).where(Lender.name == lender_name))
    lender = lender_res.scalar_one_or_none()
    if not lender:
        lender = Lender(name=lender_name)
        db.add(lender)
        await db.commit()
        await db.refresh(lender)

    if parsed:
        for crit in parsed:
            lending_type = (
                LendingType.buy_to_let
                if crit["lending_type"] == "buy_to_let"
                else LendingType.residential
            )
            db.add(
                EligibilityCriteria(
                    lender_id=lender.id,
                    source_crit_id=crit["source_crit_id"],
                    category=crit["category"],
                    criterion_name=crit["criterion_name"],
                    description=crit["description"],
                    grade=crit["grade"],
                    details_text=crit["details_text"],
                    tags=crit["tags"],
                    lending_type=lending_type,
                )
            )
        logger.info("Seeded %d criteria rows for %s.", len(parsed), lender_name)

    # Sample products — imported from the existing seed module.
    from app.seed.parse_knowledge_bank import seed_sample_products  # noqa: F401

    from app.models.product import ProductType

    sample_products = [
        {
            "name": "Accord 2-Year Fixed 60% LTV",
            "product_type": ProductType.fixed,
            "rate": 4.24,
            "rate_type": "fixed",
            "initial_period_months": 24,
            "svr_rate": 7.99,
            "min_ltv": 0,
            "max_ltv": 60,
            "min_loan": 25000,
            "max_loan": 1000000,
            "arrangement_fee": 0,
            "booking_fee": 0,
            "cashback": 0,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 2-Year Fixed 75% LTV",
            "product_type": ProductType.fixed,
            "rate": 4.49,
            "rate_type": "fixed",
            "initial_period_months": 24,
            "svr_rate": 7.99,
            "min_ltv": 60.01,
            "max_ltv": 75,
            "min_loan": 25000,
            "max_loan": 750000,
            "arrangement_fee": 999,
            "booking_fee": 0,
            "cashback": 250,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 5-Year Fixed 75% LTV",
            "product_type": ProductType.fixed,
            "rate": 4.34,
            "rate_type": "fixed",
            "initial_period_months": 60,
            "svr_rate": 7.99,
            "min_ltv": 60.01,
            "max_ltv": 75,
            "min_loan": 25000,
            "max_loan": 750000,
            "arrangement_fee": 1499,
            "booking_fee": 0,
            "cashback": 0,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 5-Year Fixed 85% LTV",
            "product_type": ProductType.fixed,
            "rate": 4.89,
            "rate_type": "fixed",
            "initial_period_months": 60,
            "svr_rate": 7.99,
            "min_ltv": 75.01,
            "max_ltv": 85,
            "min_loan": 25000,
            "max_loan": 500000,
            "arrangement_fee": 999,
            "booking_fee": 0,
            "cashback": 500,
            "min_income": 30000,
            "max_income_multiple": 4.49,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 2-Year Fixed 90% LTV",
            "product_type": ProductType.fixed,
            "rate": 5.19,
            "rate_type": "fixed",
            "initial_period_months": 24,
            "svr_rate": 7.99,
            "min_ltv": 85.01,
            "max_ltv": 90,
            "min_loan": 25000,
            "max_loan": 500000,
            "arrangement_fee": 0,
            "booking_fee": 0,
            "cashback": 0,
            "min_income": 30000,
            "max_income_multiple": 4.49,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 2-Year Tracker 75% LTV",
            "product_type": ProductType.tracker,
            "rate": 4.74,
            "rate_type": "tracker",
            "initial_period_months": 24,
            "svr_rate": 7.99,
            "min_ltv": 0,
            "max_ltv": 75,
            "min_loan": 25000,
            "max_loan": 750000,
            "arrangement_fee": 0,
            "booking_fee": 0,
            "cashback": 0,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
    ]

    for pd in sample_products:
        db.add(Product(lender_id=lender.id, **pd))
    await db.commit()
    logger.info("Seeded %d sample products.", len(sample_products))


async def _seed_demo_broker(db) -> None:
    """Seed a demo broker account so the broker dashboard is usable out of the box."""
    result = await db.execute(select(Broker).where(Broker.email == "demo@homeward.test"))
    if result.scalar_one_or_none():
        return

    import bcrypt

    hashed = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
    db.add(
        Broker(
            email="demo@homeward.test",
            full_name="Demo Broker",
            hashed_password=hashed,
            active=True,
        )
    )
    await db.commit()
    logger.info("Seeded demo broker account: demo@homeward.test / password")
