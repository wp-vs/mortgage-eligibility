import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recommendations(
        self, customer: Customer, top_matches: list[dict]
    ) -> list[dict]:
        # Clear existing recommendations for this customer
        await self.db.execute(
            delete(Recommendation).where(Recommendation.customer_id == customer.id)
        )

        results = []
        for rank, match in enumerate(top_matches, 1):
            rec = Recommendation(
                customer_id=customer.id,
                product_id=match["product_id"],
                rank=rank,
                match_score=match["match_score"],
                match_reasons=match["match_reasons"],
                unmet_criteria=match.get("unmet_criteria"),
                customer_summary_text=self._generate_customer_summary(match, rank),
                broker_summary_text=self._generate_broker_summary(match, customer, rank),
            )
            self.db.add(rec)

            results.append({
                **match,
                "rank": rank,
                "customer_summary": rec.customer_summary_text,
                "broker_summary": rec.broker_summary_text,
            })

        await self.db.commit()
        return results

    def _generate_customer_summary(self, match: dict, rank: int) -> str:
        rate = match["rate"]
        lender = match["lender_name"]
        product = match["product_name"]
        period = match["initial_period_months"]
        fee = match["arrangement_fee"]
        monthly = match.get("estimated_monthly_payment")

        lines = [
            f"Option {rank}: {lender} - {product}",
            f"Rate: {rate}% for {period} months",
        ]

        if monthly:
            lines.append(f"Estimated monthly payment: £{monthly:,.2f}")

        if fee > 0:
            lines.append(f"Arrangement fee: £{fee:,.0f}")
        else:
            lines.append("No arrangement fee")

        if match.get("match_reasons"):
            lines.append("Why this could work for you:")
            for reason in match["match_reasons"][:3]:
                lines.append(f"  - {reason}")

        if match.get("unmet_criteria"):
            lines.append("Points to discuss with your broker:")
            for issue in match["unmet_criteria"][:2]:
                lines.append(f"  - {issue}")

        return "\n".join(lines)

    def _generate_broker_summary(
        self, match: dict, customer: Customer, rank: int
    ) -> str:
        income = float(customer.annual_income or 0)
        property_value = float(customer.property_value or 0)
        deposit = float(customer.deposit_amount or 0)
        loan = property_value - deposit
        ltv = (loan / property_value * 100) if property_value > 0 else 0

        lines = [
            f"Recommendation #{rank}: {match['lender_name']} - {match['product_name']}",
            f"Match score: {match['match_score']:.1f}/100",
            "",
            f"Customer: {customer.full_name or 'N/A'}",
            f"Income: £{income:,.0f} | Employment: {customer.employment_type.value if customer.employment_type else 'N/A'}",
            f"Property: £{property_value:,.0f} | Deposit: £{deposit:,.0f} | Loan: £{loan:,.0f}",
            f"LTV: {ltv:.1f}%",
            "",
            f"Product: {match['rate']}% {match['product_type']} for {match['initial_period_months']}m",
            f"Max LTV: {match['max_ltv']}% | Fee: £{match['arrangement_fee']:,.0f}",
        ]

        if match.get("estimated_monthly_payment"):
            lines.append(f"Est. monthly: £{match['estimated_monthly_payment']:,.2f}")

        if match.get("match_reasons"):
            lines.append("\nMatch reasons:")
            for r in match["match_reasons"]:
                lines.append(f"  + {r}")

        if match.get("unmet_criteria"):
            lines.append("\nConcerns:")
            for i in match["unmet_criteria"]:
                lines.append(f"  ! {i}")

        return "\n".join(lines)
