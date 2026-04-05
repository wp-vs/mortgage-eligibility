"""
Parse the Knowledge Bank HTML to extract eligibility criteria and seed the database.
Usage: python -m app.seed.parse_knowledge_bank
"""

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Path to the Knowledge Bank HTML file
KB_HTML_PATH = Path(__file__).parent.parent.parent.parent / "Knowledge Bank ©.html"


def parse_knowledge_bank(html_path: Path = KB_HTML_PATH) -> list[dict]:
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    criteria = []

    # Find lender name from the heading
    heading = soup.find("h2")
    lender_name = "Accord"  # Default from the known HTML
    if heading:
        span = heading.find("span", class_="color--primary")
        if span:
            lender_name = span.get_text(strip=True)

    # Determine lending type from heading
    lending_type = "residential"
    if heading:
        heading_text = heading.get_text(strip=True).lower()
        if "buy to let" in heading_text or "btl" in heading_text:
            lending_type = "buy_to_let"

    # Find all criteria rows
    criteria_rows = soup.find_all("div", class_="criteriaRow")

    for row in criteria_rows:
        crit_id = row.get("data-crit-id")
        row_num = row.get("data-row")
        criterion_name = row.get_text(strip=True)

        # Find associated tags
        tags_span = row.find_next_sibling("span", class_="tags")
        tags = []
        if tags_span:
            tags_text = tags_span.get_text(strip=True)
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]

        # Find expanded criteria details
        expanded_id = f"search-criteria-expanded-{row_num}"
        expanded_span = soup.find("span", id=expanded_id)

        grade = None
        details_text = ""
        description = ""

        if expanded_span:
            # Extract description (the question/definition)
            desc_divs = expanded_span.find_all(
                "div", style=lambda s: s and "font-size" in str(s)
            )
            if desc_divs:
                description = desc_divs[0].get_text(strip=True)

            # Extract grade from image
            grade_img = expanded_span.find("img")
            if grade_img:
                src = grade_img.get("src", "")
                if "yes.png" in src:
                    grade = "yes"
                elif "no.png" in src:
                    grade = "no"
                elif "refer.png" in src:
                    grade = "refer"
                elif "yescondition" in src:
                    grade = "condition"
                elif "yesbyexception" in src:
                    grade = "yes_by_exception"

            # Extract grade text
            grade_div = expanded_span.find("div", class_="type--bold")
            grade_text = grade_div.get_text(strip=True) if grade_div else ""

            # Extract detail text
            detail_div = expanded_span.find("div", class_="type--fine-print")
            if detail_div:
                details_text = detail_div.get_text(strip=True)

            # If no detail from fine-print, try to get all text
            if not details_text:
                details_text = expanded_span.get_text(strip=True)

        criteria.append({
            "source_crit_id": int(crit_id) if crit_id else None,
            "lender_name": lender_name,
            "lending_type": lending_type,
            "criterion_name": criterion_name,
            "description": description,
            "grade": grade,
            "details_text": details_text,
            "tags": tags,
            "category": _categorise_criterion(criterion_name, tags),
        })

    return criteria


def _categorise_criterion(name: str, tags: list[str]) -> str:
    """Attempt to categorise a criterion based on its name and tags."""
    name_lower = name.lower()
    all_text = name_lower + " " + " ".join(t.lower() for t in tags)

    categories = {
        "Income & Employment": [
            "income", "salary", "employed", "self-employed", "contractor",
            "pension", "benefits", "affordability", "earnings",
        ],
        "Property": [
            "property", "house", "flat", "leasehold", "freehold", "valuation",
            "new build", "construction", "ex-local", "land",
        ],
        "Applicant": [
            "age", "nationality", "residency", "ccj", "bankruptcy", "iva",
            "credit", "adverse", "default", "first time", "ftb",
        ],
        "Mortgage Terms": [
            "ltv", "loan", "term", "repayment", "interest only", "overpayment",
            "porting", "product transfer", "early repayment",
        ],
        "Legal & Compliance": [
            "solicitor", "conveyancer", "id", "aml", "electronic",
            "accountant", "certification",
        ],
        "Fees & Charges": [
            "fee", "charge", "valuation fee", "arrangement", "booking",
        ],
    }

    for category, keywords in categories.items():
        if any(kw in all_text for kw in keywords):
            return category

    return "General"


# Synchronous DB seeding function
def seed_database():
    """Seed the database with parsed criteria. Run with: python -m app.seed.parse_knowledge_bank"""
    import asyncio

    from sqlalchemy import select

    from app.database import async_session
    from app.models.criteria import EligibilityCriteria, LendingType
    from app.models.lender import Lender

    criteria_data = parse_knowledge_bank()
    print(f"Parsed {len(criteria_data)} criteria from Knowledge Bank HTML")

    async def _seed():
        async with async_session() as db:
            # Get or create lender
            lender_name = criteria_data[0]["lender_name"] if criteria_data else "Accord"
            result = await db.execute(
                select(Lender).where(Lender.name == lender_name)
            )
            lender = result.scalar_one_or_none()

            if not lender:
                lender = Lender(name=lender_name)
                db.add(lender)
                await db.commit()
                await db.refresh(lender)
                print(f"Created lender: {lender_name}")

            # Insert criteria
            count = 0
            for crit in criteria_data:
                lending_type = (
                    LendingType.buy_to_let
                    if crit["lending_type"] == "buy_to_let"
                    else LendingType.residential
                )

                existing = await db.execute(
                    select(EligibilityCriteria).where(
                        EligibilityCriteria.source_crit_id == crit["source_crit_id"],
                        EligibilityCriteria.lender_id == lender.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                ec = EligibilityCriteria(
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
                db.add(ec)
                count += 1

            await db.commit()
            print(f"Seeded {count} new criteria for {lender_name}")

    asyncio.run(_seed())


# Also provide sample product data for Accord
def seed_sample_products():
    """Seed sample mortgage products for testing."""
    import asyncio

    from sqlalchemy import select

    from app.database import async_session
    from app.models.lender import Lender
    from app.models.product import Product, ProductType

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
            "min_income": None,
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
            "min_income": None,
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
            "name": "Accord 5-Year Fixed 95% LTV FTB",
            "product_type": ProductType.fixed,
            "rate": 5.64,
            "rate_type": "fixed",
            "initial_period_months": 60,
            "svr_rate": 7.99,
            "min_ltv": 90.01,
            "max_ltv": 95,
            "min_loan": 25000,
            "max_loan": 350000,
            "arrangement_fee": 0,
            "booking_fee": 0,
            "cashback": 0,
            "min_income": 25000,
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
            "min_income": None,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
        {
            "name": "Accord 2-Year Discount Variable 80% LTV",
            "product_type": ProductType.discount,
            "rate": 4.99,
            "rate_type": "variable",
            "initial_period_months": 24,
            "svr_rate": 7.99,
            "min_ltv": 0,
            "max_ltv": 80,
            "min_loan": 25000,
            "max_loan": 500000,
            "arrangement_fee": 0,
            "booking_fee": 0,
            "cashback": 0,
            "min_income": None,
            "max_income_multiple": 4.5,
            "first_time_buyer_eligible": True,
        },
    ]

    async def _seed():
        async with async_session() as db:
            result = await db.execute(select(Lender).where(Lender.name == "Accord"))
            lender = result.scalar_one_or_none()

            if not lender:
                lender = Lender(name="Accord")
                db.add(lender)
                await db.commit()
                await db.refresh(lender)

            count = 0
            for prod_data in sample_products:
                existing = await db.execute(
                    select(Product).where(
                        Product.name == prod_data["name"],
                        Product.lender_id == lender.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                product = Product(lender_id=lender.id, **prod_data)
                db.add(product)
                count += 1

            await db.commit()
            print(f"Seeded {count} sample products for Accord")

    asyncio.run(_seed())


if __name__ == "__main__":
    if "--products" in sys.argv:
        seed_sample_products()
    elif "--all" in sys.argv:
        seed_database()
        seed_sample_products()
    else:
        seed_database()
