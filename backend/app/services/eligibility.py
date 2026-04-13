"""Product matching engine.

Replaces the original score-first approach with the three pillars of
standard-case mortgage advisory:

  1. Affordability — stress-rate model via AffordabilityEngine
  2. Eligibility — rules-based filter via CriteriaMatcher
  3. Sourcing — sort by total cost over the initial product period

The output still carries a match_score for backwards compatibility and
ranking tiebreakers, but the primary sort key is total cost.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.banking import BankingAnalysis
from app.models.customer import Customer
from app.models.lender import Lender
from app.models.lender_affordability import LenderAffordability
from app.models.product import Product
from app.services.affordability import (
    AffordabilityEngine,
    AffordabilityResult,
    compute_monthly_payment,
)
from app.services.complexity_classifier import (
    ComplexityClassifier,
    ComplexityVerdict,
)
from app.services.criteria_matcher import CriteriaMatcher, CriteriaResult

logger = logging.getLogger(__name__)


class EligibilityEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.affordability = AffordabilityEngine()
        self.complexity = ComplexityClassifier()
        self.criteria = CriteriaMatcher(db)

    async def find_matches(self, customer: Customer) -> list[dict]:
        property_value = float(customer.property_value or 0)
        deposit = float(customer.deposit_amount or 0)
        income = float(customer.annual_income or 0)

        if property_value <= 0 or income <= 0:
            return []

        loan_amount = property_value - deposit
        ltv = (loan_amount / property_value) * 100

        # Most recent banking analysis (if any)
        banking_analysis = await self._latest_banking_analysis(customer.id)

        # Complexity verdict is per-customer, not per-product.
        complexity_verdict = self.complexity.classify(customer, banking_analysis)

        # Fetch all active products with their lender and affordability config.
        result = await self.db.execute(
            select(Product, Lender, LenderAffordability)
            .join(Lender, Product.lender_id == Lender.id)
            .outerjoin(
                LenderAffordability,
                LenderAffordability.lender_id == Lender.id,
            )
            .where(Product.active == True, Lender.active == True)
        )
        rows = result.all()

        # Cache criteria results per lender to avoid re-evaluating the same
        # 600+ rule set for every product of that lender.
        criteria_cache: dict[int, CriteriaResult] = {}

        matches: list[dict] = []

        for product, lender, lender_config in rows:
            # Product-level hard bounds first (cheap filters)
            product_ok, product_issue = self._product_bounds_ok(
                product, loan_amount, ltv, income, customer
            )
            if not product_ok:
                logger.debug(
                    "Skipping %s — %s", product.name, product_issue
                )
                continue

            # Affordability
            afford = self.affordability.max_loan_for_customer(
                customer, product, lender_config, banking_analysis
            )
            if loan_amount > afford.max_loan:
                logger.debug(
                    "Skipping %s — loan £%.0f exceeds max £%.0f (%s)",
                    product.name,
                    loan_amount,
                    afford.max_loan,
                    afford.binding_constraint,
                )
                continue

            # Criteria (per-lender, cached)
            if lender.id not in criteria_cache:
                criteria_cache[lender.id] = await self.criteria.evaluate(
                    customer, lender.id
                )
            criteria_result = criteria_cache[lender.id]
            if criteria_result.has_blockers:
                logger.debug(
                    "Skipping lender %s — failed criteria: %s",
                    lender.name,
                    criteria_result.failed[:3],
                )
                continue

            # Sourcing metrics
            monthly = compute_monthly_payment(
                loan_amount, float(product.rate), customer.mortgage_term_years or 25
            )
            total_cost = self._total_cost_over_initial_period(
                product, loan_amount, customer.mortgage_term_years or 25
            )
            effective_rate = self._effective_rate(
                total_cost, loan_amount, product.initial_period_months
            )
            amortised_fee_pct = self._amortised_fee_pct(
                product, loan_amount, product.initial_period_months
            )

            # Reasons / issues (human-readable)
            reasons, issues = self._describe_match(
                product, lender, afford, criteria_result, ltv, loan_amount
            )

            # Score remains as a tiebreaker — lower total_cost wins, then score.
            score = self._score(product, ltv, loan_amount, afford)

            matches.append({
                "product_id": product.id,
                "lender_id": lender.id,
                "lender_name": lender.name,
                "product_name": product.name,
                "rate": float(product.rate),
                "product_type": product.product_type.value,
                "initial_period_months": product.initial_period_months,
                "max_ltv": float(product.max_ltv),
                "arrangement_fee": float(product.arrangement_fee),
                "match_score": score,
                "match_reasons": reasons,
                "unmet_criteria": issues,
                "estimated_monthly_payment": round(monthly, 2),
                "total_cost_initial": round(total_cost, 2),
                "effective_rate": round(effective_rate, 3),
                "amortised_fee_pct": round(amortised_fee_pct, 3),
                "affordability_max_loan": afford.max_loan,
                "binding_affordability_constraint": afford.binding_constraint,
                "stress_rate_used": afford.stress_rate_used,
                "complexity_reasons": complexity_verdict.reasons,
                "requires_broker_review": not complexity_verdict.is_standard
                or bool(criteria_result.referred),
                "criteria_referred": criteria_result.referred[:5],
            })

        # Primary sort: total cost ascending (cheapest first).
        # Tiebreaker: higher match_score, then lower headline rate.
        matches.sort(
            key=lambda x: (
                x["total_cost_initial"],
                -x["match_score"],
                x["rate"],
            )
        )
        return matches

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _latest_banking_analysis(
        self, customer_id: int
    ) -> BankingAnalysis | None:
        result = await self.db.execute(
            select(BankingAnalysis)
            .where(BankingAnalysis.customer_id == customer_id)
            .order_by(BankingAnalysis.analysis_date.desc())
        )
        return result.scalars().first()

    def _product_bounds_ok(
        self,
        product: Product,
        loan_amount: float,
        ltv: float,
        income: float,
        customer: Customer,
    ) -> tuple[bool, str | None]:
        if ltv > float(product.max_ltv):
            return False, f"LTV {ltv:.1f}% exceeds {product.max_ltv}%"
        if ltv < float(product.min_ltv):
            return False, f"LTV {ltv:.1f}% below {product.min_ltv}%"
        if product.min_loan and loan_amount < float(product.min_loan):
            return False, "loan below product minimum"
        if product.max_loan and loan_amount > float(product.max_loan):
            return False, "loan above product maximum"
        if customer.first_time_buyer and not product.first_time_buyer_eligible:
            return False, "not FTB eligible"
        if product.min_income and income < float(product.min_income):
            return False, "income below product minimum"
        return True, None

    def _total_cost_over_initial_period(
        self, product: Product, loan_amount: float, term_years: int
    ) -> float:
        """Approximate the total customer cost over the initial product period.

        Total cost = interest paid during the initial period
                   + arrangement fee
                   + booking fee
                   - cashback
                   - principal repaid (so a like-for-like comparison; the
                     remaining balance is still owed either way)

        Simplified interest estimate: average balance * rate * months/12.
        For the initial-period window this is close enough to be a reliable
        sort key across products with similar repayment behaviour.
        """
        rate = float(product.rate)
        months = product.initial_period_months or 24
        monthly = compute_monthly_payment(loan_amount, rate, term_years)
        total_paid = monthly * months

        # Principal amortised during initial period (cheap approximation)
        r_monthly = rate / 100 / 12
        balance = loan_amount
        interest_paid = 0.0
        for _ in range(int(months)):
            interest = balance * r_monthly
            principal = monthly - interest
            interest_paid += interest
            balance = max(0.0, balance - principal)

        fees = float(product.arrangement_fee or 0) + float(product.booking_fee or 0)
        cashback = float(product.cashback or 0)
        return interest_paid + fees - cashback

    def _effective_rate(
        self, total_cost: float, loan_amount: float, months: int
    ) -> float:
        if loan_amount <= 0 or months <= 0:
            return 0.0
        years = months / 12
        return (total_cost / loan_amount / years) * 100

    def _amortised_fee_pct(
        self, product: Product, loan_amount: float, months: int
    ) -> float:
        if loan_amount <= 0 or months <= 0:
            return 0.0
        fees = float(product.arrangement_fee or 0) + float(product.booking_fee or 0)
        return (fees / loan_amount) * (12 / months) * 100

    def _describe_match(
        self,
        product: Product,
        lender: Lender,
        afford: AffordabilityResult,
        criteria_result: CriteriaResult,
        ltv: float,
        loan_amount: float,
    ) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        issues: list[str] = []

        reasons.append(
            f"Affordability passed (max loan £{afford.max_loan:,.0f}, "
            f"binding on {afford.binding_constraint.replace('_', ' ')})"
        )
        reasons.append(f"LTV {ltv:.1f}% within product range")

        if criteria_result.passed:
            reasons.append(
                f"Passed {len(criteria_result.passed)} lender criteria"
            )
        if criteria_result.referred:
            issues.append(
                f"{len(criteria_result.referred)} criteria require broker review"
            )

        rate = float(product.rate)
        if rate < 4.5:
            reasons.append(f"Competitive headline rate at {rate:.2f}%")

        total_fee = float(product.arrangement_fee) + float(product.booking_fee)
        if total_fee == 0:
            reasons.append("No arrangement fee")
        elif total_fee > 1500:
            issues.append(f"High product fees totalling £{total_fee:,.0f}")

        return reasons, issues

    def _score(
        self,
        product: Product,
        ltv: float,
        loan_amount: float,
        afford: AffordabilityResult,
    ) -> float:
        """Retained for tiebreaking only. Primary sort is total cost."""
        score = 100.0
        headroom = afford.max_loan - loan_amount
        if afford.max_loan > 0:
            headroom_pct = headroom / afford.max_loan * 100
            if headroom_pct > 30:
                score += 15
            elif headroom_pct > 15:
                score += 5

        ltv_headroom = float(product.max_ltv) - ltv
        if ltv_headroom > 15:
            score += 5

        rate = float(product.rate)
        if rate < 4.5:
            score += 10
        elif rate > 6.0:
            score -= 10

        total_fee = float(product.arrangement_fee) + float(product.booking_fee)
        if total_fee == 0:
            score += 5
        elif total_fee > 1500:
            score -= 5

        if float(product.cashback or 0) > 0:
            score += 3
        return max(0.0, score)
