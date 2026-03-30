import logging
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExpenseAnalyser:
    # Categories with keywords and severity
    EXPENSE_CATEGORIES = {
        "rent": {
            "keywords": ["rent", "landlord", "letting", "housing", "tenancy"],
            "severity": "info",
            "description": "Rent / housing costs",
        },
        "gambling": {
            "keywords": [
                "bet365",
                "betfair",
                "paddy power",
                "william hill",
                "ladbrokes",
                "coral",
                "skybet",
                "casino",
                "gambl",
                "poker",
                "lottery",
                "lotto",
                "bingo",
                "flutter",
                "betfred",
                "888",
                "tombola",
            ],
            "severity": "critical",
            "description": "Gambling transactions",
        },
        "high_interest_loans": {
            "keywords": [
                "payday",
                "wonga",
                "quickquid",
                "amigo",
                "provident",
                "118",
                "moneybarn",
                "vanquis",
                "capital on tap",
                "buddy loan",
            ],
            "severity": "critical",
            "description": "High-interest / payday loan payments",
        },
        "bnpl": {
            "keywords": ["klarna", "clearpay", "laybuy", "afterpay", "zilch", "openpay"],
            "severity": "warning",
            "description": "Buy Now Pay Later commitments",
        },
        "loan_repayment": {
            "keywords": ["loan", "finance", "credit", "repayment", "hp ", "hire purchase"],
            "severity": "info",
            "description": "Loan / finance repayments",
        },
        "childcare": {
            "keywords": ["nursery", "childcare", "childmind", "daycare", "creche"],
            "severity": "info",
            "description": "Childcare costs",
        },
        "council_tax": {
            "keywords": ["council tax", "council_tax"],
            "severity": "info",
            "description": "Council tax",
        },
        "insurance": {
            "keywords": [
                "insurance",
                "aviva",
                "admiral",
                "direct line",
                "axa",
                "vitality",
            ],
            "severity": "info",
            "description": "Insurance premiums",
        },
        "subscriptions": {
            "keywords": [
                "netflix",
                "spotify",
                "amazon prime",
                "disney",
                "sky ",
                "virgin media",
                "bt ",
                "gym",
                "peloton",
            ],
            "severity": "info",
            "description": "Subscriptions and memberships",
        },
    }

    def analyse(self, transactions: list[dict]) -> dict:
        if not transactions:
            return {
                "flagged_expenses": [],
                "estimated_monthly_rent": None,
                "total_monthly_commitments": None,
            }

        # Filter for debits (outgoing payments)
        debits = [
            t
            for t in transactions
            if t.get("transaction_type") == "DEBIT"
            or float(t.get("amount", 0)) < 0
        ]

        flagged = []
        rent_amounts = []
        monthly_commitments = defaultdict(list)

        for transaction in debits:
            description = (transaction.get("description", "") or "").lower()
            amount = abs(float(transaction.get("amount", 0)))

            for category, config in self.EXPENSE_CATEGORIES.items():
                if any(kw in description for kw in config["keywords"]):
                    monthly_commitments[category].append(amount)

                    if category == "rent":
                        rent_amounts.append(amount)

        # Build flagged expenses with monthly estimates
        for category, amounts in monthly_commitments.items():
            config = self.EXPENSE_CATEGORIES[category]
            monthly_estimate = self._estimate_monthly(amounts, len(transactions))

            if monthly_estimate > 0:
                flagged.append({
                    "category": category,
                    "description": config["description"],
                    "monthly_amount": round(monthly_estimate, 2),
                    "severity": config["severity"],
                })

        # Sort by severity (critical first, then warning, then info)
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        flagged.sort(key=lambda x: severity_order.get(x["severity"], 3))

        # Calculate totals
        estimated_rent = (
            round(statistics.mean(rent_amounts), 2) if rent_amounts else None
        )
        total_monthly = sum(f["monthly_amount"] for f in flagged)

        return {
            "flagged_expenses": flagged,
            "estimated_monthly_rent": estimated_rent,
            "total_monthly_commitments": round(total_monthly, 2),
        }

    def _estimate_monthly(self, amounts: list[float], total_transaction_count: int) -> float:
        if not amounts:
            return 0

        # Rough estimate: assume transactions span ~6 months
        # Adjust based on the number of occurrences
        occurrence_count = len(amounts)
        total = sum(amounts)

        # If we see it multiple times, estimate monthly frequency
        if occurrence_count >= 6:
            return total / 6  # Roughly monthly over 6 months
        elif occurrence_count >= 3:
            return total / 3  # Assume ~3 months of data
        else:
            return statistics.mean(amounts)  # Best guess for sparse data
