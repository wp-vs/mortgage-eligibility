"""Suitability letter PDF generator.

Produces a compliance-style document for a single recommendation, using
the inputs the platform already computes: the affordability result
(binding constraint + stress rate), the top products considered (sorted
by total cost of ownership over the initial period), the chosen product,
and the customer's circumstances.

This is the document that in a traditional broker workflow is the
recommendation's audit artifact — it's what the advisor signs their name
to and what regulators inspect if the file is ever reviewed.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.customer import Customer
from app.models.product import Product
from app.models.recommendation import Recommendation


def _fmt_gbp(value: float | None) -> str:
    if value is None:
        return "—"
    return f"£{float(value):,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f}%"


class SuitabilityLetterGenerator:
    """Generate the suitability letter PDF for a single recommendation."""

    def generate(
        self,
        customer: Customer,
        recommendation: Recommendation,
        product: Product,
        lender_name: str,
        other_options: list[dict] | None = None,
    ) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="Mortgage Suitability Letter",
        )
        story = self._build_story(
            customer, recommendation, product, lender_name, other_options or []
        )
        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _build_story(
        self,
        customer: Customer,
        rec: Recommendation,
        product: Product,
        lender_name: str,
        other_options: list[dict],
    ):
        styles = getSampleStyleSheet()
        h1 = styles["Heading1"]
        h2 = styles["Heading2"]
        normal = styles["BodyText"]
        small = ParagraphStyle(
            "small", parent=normal, fontSize=8, textColor=colors.grey
        )

        story: list = []

        # Header
        story.append(Paragraph("Mortgage Suitability Letter", h1))
        story.append(
            Paragraph(
                f"Reference: HW-REC-{rec.id}  |  Date: {datetime.utcnow():%d %B %Y}",
                small,
            )
        )
        story.append(Spacer(1, 8 * mm))

        # Regulatory preamble
        story.append(
            Paragraph(
                "This letter sets out our recommendation in respect of a new "
                "mortgage, the basis on which that recommendation has been "
                "reached, and the key features, costs and risks you should "
                "consider. It is issued subject to review and counter-signature "
                "by a CeMAP-qualified broker before it takes effect.",
                normal,
            )
        )
        story.append(Spacer(1, 6 * mm))

        # Section 1 — About you
        story.append(Paragraph("1. About you", h2))
        story.append(self._customer_table(customer))
        story.append(Spacer(1, 6 * mm))

        # Section 2 — Your objectives
        story.append(Paragraph("2. Your objectives", h2))
        story.append(self._objectives_paragraph(customer, normal))
        story.append(Spacer(1, 6 * mm))

        # Section 3 — Affordability assessment
        story.append(Paragraph("3. Affordability assessment", h2))
        story.append(self._affordability_paragraph(customer, rec, product, normal))
        story.append(Spacer(1, 6 * mm))

        # Section 4 — Products considered
        story.append(Paragraph("4. Products considered", h2))
        story.append(
            Paragraph(
                "The following products were assessed against your profile "
                "and passed the affordability and eligibility filters. They "
                "are listed in order of total cost over the initial product "
                "period (lower is better).",
                normal,
            )
        )
        story.append(Spacer(1, 3 * mm))
        if other_options:
            story.append(self._options_table(other_options))
            story.append(Spacer(1, 6 * mm))

        # Section 5 — Recommendation
        story.append(Paragraph("5. Our recommendation", h2))
        story.append(
            self._recommendation_paragraph(rec, product, lender_name, normal)
        )
        story.append(Spacer(1, 6 * mm))

        # Section 6 — Risks & fees
        story.append(Paragraph("6. Risks and important information", h2))
        story.append(self._risks_paragraph(product, normal))
        story.append(Spacer(1, 6 * mm))

        # Section 7 — Consumer Duty statement
        story.append(Paragraph("7. Consumer Duty statement", h2))
        story.append(
            Paragraph(
                "We have considered whether this product represents fair "
                "value, is suitable for your stated needs and circumstances, "
                "is presented in a way you are likely to understand, and "
                "supports your ability to pursue your financial objectives. "
                "Where this letter is produced by automated systems, a "
                "qualified broker reviews the assessment before any "
                "recommendation is acted upon.",
                normal,
            )
        )
        story.append(Spacer(1, 6 * mm))

        # Section 8 — Broker sign-off
        story.append(Paragraph("8. Broker sign-off", h2))
        story.append(self._signoff_block(rec, normal))
        story.append(Spacer(1, 8 * mm))

        story.append(
            Paragraph(
                "Homeward is not currently authorised by the FCA and this "
                "document does not constitute financial advice. It is issued "
                "for the purpose of broker review.",
                small,
            )
        )

        return story

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _customer_table(self, customer: Customer) -> Table:
        property_value = float(customer.property_value or 0)
        deposit = float(customer.deposit_amount or 0)
        loan = max(0.0, property_value - deposit)
        ltv = (loan / property_value * 100) if property_value > 0 else 0.0

        rows = [
            ["Name", customer.full_name or "—"],
            ["Email", customer.email or "—"],
            [
                "Employment",
                customer.employment_type.value.replace("_", " ").title()
                if customer.employment_type
                else "—",
            ],
            ["Annual income", _fmt_gbp(customer.annual_income)],
            [
                "Credit profile",
                customer.credit_profile.value.replace("_", " ").title()
                if customer.credit_profile
                else "—",
            ],
            ["Property value", _fmt_gbp(property_value)],
            ["Deposit", _fmt_gbp(deposit)],
            ["Requested loan", _fmt_gbp(loan)],
            ["LTV", f"{ltv:.1f}%"],
            [
                "Property type",
                customer.property_type.value.replace("_", " ").title()
                if customer.property_type
                else "—",
            ],
            [
                "Term",
                f"{customer.mortgage_term_years} years"
                if customer.mortgage_term_years
                else "—",
            ],
            [
                "First-time buyer",
                "Yes" if customer.first_time_buyer else "No",
            ],
        ]
        table = Table(rows, colWidths=[55 * mm, 105 * mm])
        table.setStyle(_kv_table_style())
        return table

    def _objectives_paragraph(
        self, customer: Customer, style: ParagraphStyle
    ) -> Paragraph:
        if customer.mortgage_type and customer.mortgage_type.value == "remortgage":
            action = "remortgage an existing property"
        else:
            action = "purchase a new property"
        term = (
            f"{customer.mortgage_term_years}-year"
            if customer.mortgage_term_years
            else "standard-term"
        )
        ftb = " as a first-time buyer" if customer.first_time_buyer else ""
        return Paragraph(
            f"You have indicated that you wish to {action}{ftb} on a "
            f"{term} repayment basis. Based on our conversation and the "
            f"information you provided, our objective is to identify the "
            f"product with the lowest total cost over the initial product "
            f"period, subject to your case passing affordability and the "
            f"lender's published eligibility criteria.",
            style,
        )

    def _affordability_paragraph(
        self,
        customer: Customer,
        rec: Recommendation,
        product: Product,
        style: ParagraphStyle,
    ) -> Paragraph:
        max_loan = (
            float(rec.affordability_max_loan) if rec.affordability_max_loan else None
        )
        stress = (
            float(rec.stress_rate_used) if rec.stress_rate_used else None
        )
        constraint = rec.binding_affordability_constraint or "income_multiple"

        income = float(customer.annual_income or 0)
        constraint_lbl = {
            "income_multiple": "the lender's income multiple",
            "stress": "the lender's stress-rate affordability model",
            "cashflow": "your post-expense monthly cashflow",
        }.get(constraint, constraint)

        lines = [
            f"We calculated the maximum loan the lender is willing to offer "
            f"by applying their published income multiple to your gross "
            f"income of {_fmt_gbp(income)} and stress-testing the resulting "
            f"monthly payment at {_fmt_pct(stress)}.",
            f"The binding constraint on your borrowing was <b>{constraint_lbl}</b>, "
            f"giving a maximum affordable loan of {_fmt_gbp(max_loan)}.",
            f"Your requested loan falls within this limit, which is why "
            f"{product.name} could be recommended.",
        ]
        return Paragraph(" ".join(lines), style)

    def _options_table(self, options: list[dict]) -> Table:
        header = [
            "Rank",
            "Lender / product",
            "Rate",
            "Fees",
            "Initial period",
            "Total cost",
        ]
        rows = [header]
        for opt in options:
            rows.append(
                [
                    str(opt.get("rank", "")),
                    f"{opt.get('lender_name', '')} — {opt.get('product_name', '')}",
                    f"{opt.get('rate', 0):.2f}%",
                    _fmt_gbp(opt.get("arrangement_fee", 0)),
                    f"{opt.get('initial_period_months', 0)}m",
                    _fmt_gbp(opt.get("total_cost_initial")),
                ]
            )
        table = Table(
            rows,
            colWidths=[12 * mm, 62 * mm, 18 * mm, 22 * mm, 22 * mm, 24 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def _recommendation_paragraph(
        self,
        rec: Recommendation,
        product: Product,
        lender_name: str,
        style: ParagraphStyle,
    ) -> Paragraph:
        total_cost = (
            float(rec.total_cost_initial) if rec.total_cost_initial else None
        )
        return Paragraph(
            f"We recommend the <b>{lender_name} — {product.name}</b>, a "
            f"{product.product_type.value} product at "
            f"{float(product.rate):.2f}% for an initial period of "
            f"{product.initial_period_months} months. "
            f"This product was selected because it represents the "
            f"<b>lowest total cost of {_fmt_gbp(total_cost)}</b> over the "
            f"initial product period among all products for which you pass "
            f"affordability and the lender's eligibility criteria.",
            style,
        )

    def _risks_paragraph(self, product: Product, style: ParagraphStyle) -> Paragraph:
        svr = float(product.svr_rate or 0)
        lines = [
            "Your monthly payment is estimated and subject to final lender "
            "underwriting.",
            f"At the end of the initial product period ({product.initial_period_months} "
            f"months) the product will revert to the lender's standard variable "
            f"rate, currently {svr:.2f}%, unless you remortgage.",
            "Early repayment charges may apply if you repay or switch before "
            "the end of the initial period.",
            "Your home may be repossessed if you do not keep up repayments on "
            "your mortgage.",
        ]
        return Paragraph("<br/>".join(f"• {line}" for line in lines), style)

    def _signoff_block(self, rec: Recommendation, style: ParagraphStyle) -> Table:
        rows = [
            ["Broker name", ""],
            ["FCA number", ""],
            ["Signature", ""],
            ["Date", ""],
            ["Notes", rec.broker_notes or ""],
        ]
        table = Table(rows, colWidths=[40 * mm, 120 * mm])
        table.setStyle(_kv_table_style(min_height=8 * mm))
        return table


def _kv_table_style(min_height: float | None = None) -> TableStyle:
    style = [
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    return TableStyle(style)
