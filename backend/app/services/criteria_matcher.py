"""Rules-based eligibility filter.

Walks the per-lender rows in the `eligibility_criteria` table (seeded from
the Knowledge Bank HTML) and decides whether each one passes, fails, or
needs human review for a given customer. This is the dormant half of the
matching engine — previously only product-level LTV bounds were checked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.criteria import CriteriaGrade, EligibilityCriteria, LendingType
from app.models.customer import CreditProfile, Customer, EmploymentType, PropertyType

logger = logging.getLogger(__name__)

STANDARD_PROPERTY_TYPES = {
    PropertyType.detached,
    PropertyType.semi_detached,
    PropertyType.terraced,
    PropertyType.bungalow,
}


@dataclass
class CriteriaResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    referred: list[str] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        return bool(self.failed)


class CriteriaMatcher:
    """Evaluates the per-lender rules against a customer profile.

    Rules are tag-driven. Each row in EligibilityCriteria has a category
    (e.g. "Income & Employment", "Property") and a grade
    (yes/no/refer/condition/yes_by_exception). For each rule we look for
    tokens in the criterion name/tags to decide which evaluator to run,
    then bucket the result.

    The strategy is conservative: if we don't know how to evaluate a rule,
    we leave it alone (we don't claim to pass it). Only rules we can
    positively evaluate against the customer contribute to the result.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, customer: Customer, lender_id: int) -> CriteriaResult:
        result = await self.db.execute(
            select(EligibilityCriteria).where(
                EligibilityCriteria.lender_id == lender_id,
                EligibilityCriteria.lending_type == LendingType.residential,
            )
        )
        rules = result.scalars().all()

        res = CriteriaResult()
        for rule in rules:
            outcome = self._evaluate_rule(rule, customer)
            if outcome == "pass":
                res.passed.append(rule.criterion_name)
            elif outcome == "fail":
                res.failed.append(rule.criterion_name)
            elif outcome == "refer":
                res.referred.append(rule.criterion_name)
            # outcome == "skip" → we don't know, ignore
        return res

    def _evaluate_rule(
        self, rule: EligibilityCriteria, customer: Customer
    ) -> str:
        """Return one of: pass | fail | refer | skip."""
        # Any grade of `refer` sends the rule straight to manual review if
        # our evaluator matches — the underwriter wants to see the case.
        grade = rule.grade
        if grade is None:
            return "skip"

        name_lc = (rule.criterion_name or "").lower()
        tags_lc = [t.lower() for t in (rule.tags or [])]
        haystack = f"{name_lc} {' '.join(tags_lc)}"

        evaluator = self._pick_evaluator(haystack)
        if evaluator is None:
            return "skip"

        matches = evaluator(customer)
        if matches is None:
            return "skip"

        # Translate the (matches, grade) pair into an outcome.
        return self._outcome_from_grade(matches, grade)

    def _outcome_from_grade(self, customer_matches: bool, grade: CriteriaGrade) -> str:
        """Map the (customer-matches-this-rule, grade) pair to an outcome.

        We deliberately do NOT treat a `no` grade as a hard-fail: the
        Knowledge Bank rows are nuanced ("does the lender accept
        accountant's projections?" — the answer being "no" doesn't
        actually disqualify every self-employed applicant) and our tag
        evaluators are approximate. Anything other than a clean `yes`
        therefore routes to human review, which matches the intent of
        reserving the broker for the 10% of cases the rules engine
        shouldn't be trusted to auto-approve.
        """
        if not customer_matches:
            # Rule doesn't apply to this customer.
            return "skip"
        if grade == CriteriaGrade.yes:
            return "pass"
        # `no`, `refer`, `condition`, `yes_by_exception` → broker review
        return "refer"

    def _pick_evaluator(self, haystack: str):
        """Choose a customer-attribute evaluator based on tokens in the rule."""
        if "self-employed" in haystack or "self employed" in haystack:
            return self._is_self_employed
        if "contractor" in haystack:
            return self._is_contractor
        if "employed" in haystack and "self" not in haystack:
            return self._is_employed
        if "retired" in haystack or "pension" in haystack:
            return self._is_retired
        if "first time buyer" in haystack or "ftb" in haystack:
            return self._is_first_time_buyer
        if "ccj" in haystack or "bankruptcy" in haystack or "iva" in haystack:
            return self._has_adverse_credit
        if "adverse" in haystack or "default" in haystack:
            return self._has_adverse_credit
        if "ex-local" in haystack or "ex local" in haystack:
            return self._is_ex_local_authority
        if "new build" in haystack:
            return self._is_new_build
        if "flat" in haystack and "house" not in haystack:
            return self._is_flat
        if "leasehold" in haystack:
            return self._is_leasehold_flat
        return None

    # ------------------------------------------------------------------
    # Evaluators — each returns True / False / None (unknown)
    # ------------------------------------------------------------------

    def _is_employed(self, c: Customer) -> bool | None:
        if c.employment_type is None:
            return None
        return c.employment_type == EmploymentType.employed

    def _is_self_employed(self, c: Customer) -> bool | None:
        if c.employment_type is None:
            return None
        return c.employment_type == EmploymentType.self_employed

    def _is_contractor(self, c: Customer) -> bool | None:
        if c.employment_type is None:
            return None
        return c.employment_type == EmploymentType.contractor

    def _is_retired(self, c: Customer) -> bool | None:
        if c.employment_type is None:
            return None
        return c.employment_type == EmploymentType.retired

    def _is_first_time_buyer(self, c: Customer) -> bool | None:
        return c.first_time_buyer

    def _has_adverse_credit(self, c: Customer) -> bool | None:
        if c.credit_profile in (None, CreditProfile.unknown):
            return None
        return c.credit_profile in (
            CreditProfile.minor_adverse,
            CreditProfile.major_adverse,
        )

    def _is_ex_local_authority(self, c: Customer) -> bool | None:
        if not c.property_subtype:
            return None
        return "ex-local" in c.property_subtype.lower() or "ex local" in c.property_subtype.lower()

    def _is_new_build(self, c: Customer) -> bool | None:
        return c.property_type == PropertyType.new_build

    def _is_flat(self, c: Customer) -> bool | None:
        if c.property_type is None:
            return None
        return c.property_type == PropertyType.flat

    def _is_leasehold_flat(self, c: Customer) -> bool | None:
        if c.property_type is None:
            return None
        return c.property_type == PropertyType.flat  # assume flat ⇒ leasehold
