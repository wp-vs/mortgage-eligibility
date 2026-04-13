"""Standard-case vs. edge-case classifier.

The platform automates the standard mortgage case (employed applicant,
clean credit, freehold house, LTV ≤ 85%). Anything else gets a "broker
required" flag so a human CeMAP-qualified advisor reviews before the
customer sees a final recommendation. This reflects both the regulatory
reality (Consumer Duty, suitability liability) and the practical reality
(irregular income, adverse credit, portfolio landlords, and interest-only
repayment vehicles all require judgment the rules engine can't substitute).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.banking import BankingAnalysis
from app.models.customer import CreditProfile, Customer, EmploymentType, PropertyType

STANDARD_PROPERTY_TYPES = {
    PropertyType.detached,
    PropertyType.semi_detached,
    PropertyType.terraced,
    PropertyType.bungalow,
}

STANDARD_EMPLOYMENT_TYPES = {EmploymentType.employed}

HIGH_LTV_THRESHOLD = 85.0
LOW_REGULARITY_THRESHOLD = 70


@dataclass
class ComplexityVerdict:
    is_standard: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def routing(self) -> str:
        return "auto_recommend" if self.is_standard else "broker_required"


class ComplexityClassifier:
    def classify(
        self,
        customer: Customer,
        banking_analysis: BankingAnalysis | None = None,
    ) -> ComplexityVerdict:
        reasons: list[str] = []

        # Employment
        if (
            customer.employment_type is not None
            and customer.employment_type not in STANDARD_EMPLOYMENT_TYPES
        ):
            reasons.append("non_standard_employment")

        # Credit
        if customer.credit_profile in (
            CreditProfile.minor_adverse,
            CreditProfile.major_adverse,
        ):
            reasons.append("adverse_credit")

        # LTV (only check if we have the numbers)
        property_value = float(customer.property_value or 0)
        deposit = float(customer.deposit_amount or 0)
        if property_value > 0:
            ltv = ((property_value - deposit) / property_value) * 100
            if ltv > HIGH_LTV_THRESHOLD:
                reasons.append("high_ltv")

        # Property type
        if (
            customer.property_type is not None
            and customer.property_type not in STANDARD_PROPERTY_TYPES
        ):
            reasons.append("non_standard_property")

        if customer.property_subtype:
            subtype_lc = customer.property_subtype.lower()
            if any(
                token in subtype_lc
                for token in ("ex-local", "ex local", "non-standard", "concrete")
            ):
                reasons.append("non_standard_property")

        # Banking signals
        if banking_analysis is not None:
            if (
                banking_analysis.salary_regularity_score is not None
                and banking_analysis.salary_regularity_score < LOW_REGULARITY_THRESHOLD
            ):
                reasons.append("irregular_income")

            if self._has_critical_flags(banking_analysis):
                reasons.append("critical_expenses")

        # De-duplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for r in reasons:
            if r not in seen:
                deduped.append(r)
                seen.add(r)

        return ComplexityVerdict(is_standard=not deduped, reasons=deduped)

    def _has_critical_flags(self, banking_analysis: BankingAnalysis) -> bool:
        flags = banking_analysis.flagged_expenses or []
        for flag in flags:
            if isinstance(flag, dict) and flag.get("severity") == "critical":
                return True
        return False
