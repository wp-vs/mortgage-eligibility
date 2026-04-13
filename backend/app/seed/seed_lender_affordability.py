"""Seed per-lender affordability configuration.

Values are best-known public approximations and should be verified by a
qualified broker before going live. They represent the rules each lender
applies when deciding the maximum loan they will offer: income multiples
(with an enhanced multiple above an income threshold), stress rate method,
and debt-to-income cap.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lender import Lender
from app.models.lender_affordability import LenderAffordability, StressRateMethod

# lender_name -> config dict
LENDER_AFFORDABILITY_DEFAULTS: dict[str, dict] = {
    "Accord": {
        "income_multiple_standard": 4.49,
        "income_multiple_enhanced": 5.00,
        "enhanced_income_threshold": 75000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.00,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
    "Halifax": {
        "income_multiple_standard": 4.50,
        "income_multiple_enhanced": 5.50,
        "enhanced_income_threshold": 75000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.49,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
    "NatWest": {
        "income_multiple_standard": 4.49,
        "income_multiple_enhanced": 5.00,
        "enhanced_income_threshold": 50000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.00,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
    "Santander": {
        "income_multiple_standard": 4.45,
        "income_multiple_enhanced": 5.00,
        "enhanced_income_threshold": 45000,
        "stress_rate_method": StressRateMethod.absolute,
        "stress_rate_pct": 8.50,
        "stress_margin_pct": 0.0,
        "debt_to_income_cap_pct": 45.0,
    },
    "Barclays": {
        "income_multiple_standard": 4.49,
        "income_multiple_enhanced": 5.50,
        "enhanced_income_threshold": 75000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.49,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
    "Nationwide": {
        "income_multiple_standard": 4.49,
        "income_multiple_enhanced": 5.00,
        "enhanced_income_threshold": 40000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.00,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
    "HSBC": {
        "income_multiple_standard": 4.49,
        "income_multiple_enhanced": 4.75,
        "enhanced_income_threshold": 100000,
        "stress_rate_method": StressRateMethod.svr_plus_margin,
        "stress_rate_pct": 8.00,
        "stress_margin_pct": 1.00,
        "debt_to_income_cap_pct": 45.0,
    },
}

# Default config applied if a lender is not in the table above.
DEFAULT_CONFIG = {
    "income_multiple_standard": 4.49,
    "income_multiple_enhanced": None,
    "enhanced_income_threshold": None,
    "stress_rate_method": StressRateMethod.svr_plus_margin,
    "stress_rate_pct": 8.00,
    "stress_margin_pct": 1.00,
    "debt_to_income_cap_pct": 45.0,
}


async def seed_lender_affordability(db: AsyncSession) -> int:
    """Seed affordability configs for all known lenders.

    Idempotent — skips any lender that already has a config row.
    Returns the number of rows created.
    """
    result = await db.execute(select(Lender))
    lenders = result.scalars().all()

    created = 0
    for lender in lenders:
        existing = await db.execute(
            select(LenderAffordability).where(
                LenderAffordability.lender_id == lender.id
            )
        )
        if existing.scalar_one_or_none():
            continue

        cfg = LENDER_AFFORDABILITY_DEFAULTS.get(lender.name, DEFAULT_CONFIG)
        db.add(LenderAffordability(lender_id=lender.id, **cfg))
        created += 1

    await db.commit()
    return created
