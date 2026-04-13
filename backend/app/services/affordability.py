"""Stress-rate affordability engine.

Computes the maximum loan a lender will offer for a given customer+product
combination by taking the minimum of three caps:

  1. Income multiple cap         — income × lender_multiple
  2. Stress-rate cap              — max monthly payment the customer can
                                    afford at a stressed interest rate,
                                    reversed through the annuity formula
  3. Post-expense cashflow cap    — only applied if Open Banking analysis
                                    exists; loan size must leave a 40%
                                    buffer after commitments + housing

The binding constraint is surfaced so the suitability letter can cite it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.models.banking import BankingAnalysis
from app.models.customer import Customer
from app.models.lender_affordability import LenderAffordability, StressRateMethod
from app.models.product import Product

logger = logging.getLogger(__name__)


@dataclass
class AffordabilityResult:
    max_loan: float
    income_cap: float
    stress_cap: float
    cashflow_cap: float | None
    binding_constraint: str  # "income_multiple" | "stress" | "cashflow"
    multiple_used: float
    stress_rate_used: float
    max_affordable_monthly: float


def compute_monthly_payment(
    loan_amount: float, annual_rate_pct: float, term_years: int
) -> float:
    """Standard annuity formula."""
    if term_years <= 0 or loan_amount <= 0:
        return 0.0
    months = term_years * 12
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return loan_amount / months
    return loan_amount * (r * (1 + r) ** months) / ((1 + r) ** months - 1)


def reverse_annuity(
    monthly_payment: float, annual_rate_pct: float, term_years: int
) -> float:
    """Invert the annuity formula: given a monthly payment, return the
    principal that payment services over `term_years` at `annual_rate_pct`.
    """
    if monthly_payment <= 0 or term_years <= 0:
        return 0.0
    months = term_years * 12
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return monthly_payment * months
    return monthly_payment * ((1 + r) ** months - 1) / (r * (1 + r) ** months)


class AffordabilityEngine:
    """Decides how much a specific lender will lend to a specific customer
    against a specific product.

    This is what a CeMAP advisor does mechanically for every standard case:
    apply the lender's income multiple, their stress rate, and a common-sense
    debt-to-income cap. Returns the binding constraint so the suitability
    letter can quote the actual reasoning.
    """

    def max_loan_for_customer(
        self,
        customer: Customer,
        product: Product,
        lender_config: LenderAffordability | None,
        banking_analysis: BankingAnalysis | None = None,
    ) -> AffordabilityResult:
        income = float(customer.annual_income or 0)
        term_years = customer.mortgage_term_years or 25

        # Fall back to product.max_income_multiple if no lender config seeded.
        if lender_config is None:
            multiple = float(product.max_income_multiple or 4.49)
            stress_rate = float(product.svr_rate or 8.0) + 1.0
            dti_cap = 45.0
        else:
            multiple = self._select_income_multiple(income, lender_config)
            stress_rate = self._compute_stress_rate(product, lender_config)
            dti_cap = float(lender_config.debt_to_income_cap_pct)

        # 1. Income multiple cap
        income_cap = income * multiple

        # 2. Stress cap — how much loan can the customer service at the stressed rate?
        max_affordable_monthly = self._max_affordable_monthly(
            customer, banking_analysis, dti_cap
        )
        stress_cap = reverse_annuity(max_affordable_monthly, stress_rate, term_years)

        # 3. Cashflow cap (only if we have Open Banking data)
        cashflow_cap: float | None = None
        if banking_analysis is not None:
            avg_salary = float(banking_analysis.average_salary or 0)
            committed = float(banking_analysis.total_monthly_commitments or 0)
            if avg_salary > 0:
                # Reserve 40% buffer after commitments, service rest at headline rate
                available = max(0.0, (avg_salary - committed) * 0.60)
                cashflow_cap = reverse_annuity(
                    available, float(product.rate), term_years
                )

        caps: dict[str, float] = {
            "income_multiple": income_cap,
            "stress": stress_cap,
        }
        if cashflow_cap is not None:
            caps["cashflow"] = cashflow_cap

        binding = min(caps, key=lambda k: caps[k])
        max_loan = max(0.0, caps[binding])

        return AffordabilityResult(
            max_loan=round(max_loan, 2),
            income_cap=round(income_cap, 2),
            stress_cap=round(stress_cap, 2),
            cashflow_cap=round(cashflow_cap, 2) if cashflow_cap is not None else None,
            binding_constraint=binding,
            multiple_used=multiple,
            stress_rate_used=stress_rate,
            max_affordable_monthly=round(max_affordable_monthly, 2),
        )

    def _select_income_multiple(
        self, income: float, config: LenderAffordability
    ) -> float:
        if (
            config.income_multiple_enhanced is not None
            and config.enhanced_income_threshold is not None
            and income >= float(config.enhanced_income_threshold)
        ):
            return float(config.income_multiple_enhanced)
        return float(config.income_multiple_standard)

    def _compute_stress_rate(
        self, product: Product, config: LenderAffordability
    ) -> float:
        method = config.stress_rate_method
        svr = float(product.svr_rate or 0)
        margin = float(config.stress_margin_pct)
        floor = float(config.stress_rate_pct)

        if method == StressRateMethod.absolute:
            return floor
        if method == StressRateMethod.svr_plus_margin:
            return svr + margin
        # reversion_plus: SVR + margin, floored
        return max(svr + margin, floor)

    def _max_affordable_monthly(
        self,
        customer: Customer,
        banking_analysis: BankingAnalysis | None,
        dti_cap_pct: float,
    ) -> float:
        """Compute the highest monthly housing payment the customer can afford.

        Preferred path: Open Banking-derived net income minus existing
        monthly commitments, capped at the lender's DTI percentage of net.

        Fallback: estimate net take-home from gross income using a rough
        UK PAYE model (~78% take-home for a £60k earner, tapering down
        for higher earners), then apply the DTI cap.
        """
        if banking_analysis and banking_analysis.average_salary:
            net_monthly = float(banking_analysis.average_salary)
            committed = float(banking_analysis.total_monthly_commitments or 0)
            headroom = (net_monthly * dti_cap_pct / 100) - committed
            return max(0.0, headroom)

        income = float(customer.annual_income or 0)
        if income <= 0:
            return 0.0
        net_monthly = _estimate_net_monthly(income)
        return net_monthly * dti_cap_pct / 100


def _estimate_net_monthly(gross_annual: float) -> float:
    """Very rough UK PAYE + NI take-home estimator.

    Personal allowance £12,570; basic rate 20% up to £50,270; higher 40%
    up to £125,140; additional 45% above. NI: 8% on £12,570–£50,270, 2%
    above. These are 2024-25 figures and deliberately simplified for an
    affordability fallback when Open Banking isn't available.
    """
    allowance = 12_570
    basic_top = 50_270
    higher_top = 125_140

    taxable = max(0.0, gross_annual - allowance)
    income_tax = 0.0
    if gross_annual > higher_top:
        income_tax += (higher_top - basic_top) * 0.40
        income_tax += (gross_annual - higher_top) * 0.45
        income_tax += (basic_top - allowance) * 0.20
    elif gross_annual > basic_top:
        income_tax += (basic_top - allowance) * 0.20
        income_tax += (gross_annual - basic_top) * 0.40
    else:
        income_tax += taxable * 0.20

    ni = 0.0
    if gross_annual > basic_top:
        ni += (basic_top - allowance) * 0.08
        ni += (gross_annual - basic_top) * 0.02
    elif gross_annual > allowance:
        ni += (gross_annual - allowance) * 0.08

    net_annual = gross_annual - income_tax - ni
    return net_annual / 12
