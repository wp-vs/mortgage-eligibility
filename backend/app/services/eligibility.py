import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.lender import Lender
from app.models.product import Product

logger = logging.getLogger(__name__)


class EligibilityEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_matches(self, customer: Customer) -> list[dict]:
        # Calculate key metrics
        property_value = float(customer.property_value or 0)
        deposit = float(customer.deposit_amount or 0)
        income = float(customer.annual_income or 0)

        if property_value <= 0 or income <= 0:
            return []

        loan_amount = property_value - deposit
        ltv = (loan_amount / property_value) * 100 if property_value > 0 else 100

        # Fetch all active products
        result = await self.db.execute(
            select(Product, Lender)
            .join(Lender, Product.lender_id == Lender.id)
            .where(Product.active == True, Lender.active == True)
        )
        rows = result.all()

        matches = []

        for product, lender in rows:
            score, reasons, issues = self._evaluate_product(
                product, lender, customer, loan_amount, ltv, income
            )

            if score > 0:
                # Estimate monthly payment
                monthly = self._estimate_monthly_payment(
                    loan_amount,
                    float(product.rate),
                    customer.mortgage_term_years or 25,
                )

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
                    "estimated_monthly_payment": monthly,
                })

        # Sort by score descending, then by rate ascending
        matches.sort(key=lambda x: (-x["match_score"], x["rate"]))
        return matches

    def _evaluate_product(
        self,
        product: Product,
        lender: Lender,
        customer: Customer,
        loan_amount: float,
        ltv: float,
        income: float,
    ) -> tuple[float, list[str], list[str]]:
        score = 100.0
        reasons = []
        issues = []

        # Hard fail: LTV check
        if ltv > float(product.max_ltv):
            return 0, [], [f"LTV {ltv:.1f}% exceeds maximum {product.max_ltv}%"]

        if ltv < float(product.min_ltv):
            return 0, [], [f"LTV {ltv:.1f}% below minimum {product.min_ltv}%"]

        # Hard fail: Loan amount bounds
        if product.min_loan and loan_amount < float(product.min_loan):
            return 0, [], [f"Loan £{loan_amount:,.0f} below minimum £{product.min_loan:,.0f}"]

        if product.max_loan and loan_amount > float(product.max_loan):
            return 0, [], [f"Loan £{loan_amount:,.0f} exceeds maximum £{product.max_loan:,.0f}"]

        # Hard fail: Income multiple
        max_borrowing = income * float(product.max_income_multiple)
        if loan_amount > max_borrowing:
            return 0, [], [
                f"Loan £{loan_amount:,.0f} exceeds {product.max_income_multiple}x income (max £{max_borrowing:,.0f})"
            ]

        # Hard fail: First-time buyer
        if customer.first_time_buyer and not product.first_time_buyer_eligible:
            return 0, [], ["Product not available to first-time buyers"]

        # Hard fail: Minimum income
        if product.min_income and income < float(product.min_income):
            return 0, [], [f"Income £{income:,.0f} below minimum £{product.min_income:,.0f}"]

        # Scoring bonuses
        reasons.append(f"LTV {ltv:.1f}% within product range")

        # Better LTV = better rate usually
        ltv_headroom = float(product.max_ltv) - ltv
        if ltv_headroom > 15:
            score += 10
            reasons.append("Strong LTV position with good headroom")

        # Income headroom
        income_usage = loan_amount / max_borrowing * 100
        if income_usage < 70:
            score += 10
            reasons.append("Comfortable income-to-borrowing ratio")
        elif income_usage > 90:
            score -= 10
            issues.append("Borrowing near maximum income multiple")

        # Rate competitiveness (lower is better, normalised)
        rate = float(product.rate)
        if rate < 4.0:
            score += 15
            reasons.append(f"Competitive rate at {rate}%")
        elif rate < 5.0:
            score += 5
        elif rate > 6.0:
            score -= 10

        # Fee consideration
        total_fee = float(product.arrangement_fee) + float(product.booking_fee)
        if total_fee == 0:
            score += 5
            reasons.append("No arrangement fees")
        elif total_fee > 1500:
            score -= 5
            issues.append(f"High fees totalling £{total_fee:,.0f}")

        # Cashback bonus
        if float(product.cashback) > 0:
            score += 3
            reasons.append(f"£{product.cashback:,.0f} cashback offered")

        return max(0, score), reasons, issues

    def _estimate_monthly_payment(
        self, loan_amount: float, annual_rate: float, term_years: int
    ) -> float:
        monthly_rate = annual_rate / 100 / 12
        num_payments = term_years * 12

        if monthly_rate == 0:
            return round(loan_amount / num_payments, 2)

        payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / ((1 + monthly_rate) ** num_payments - 1)

        return round(payment, 2)
