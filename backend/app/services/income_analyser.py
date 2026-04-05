import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IncomeAnalyser:
    # Typical salary credit patterns
    SALARY_KEYWORDS = [
        "salary",
        "wages",
        "payroll",
        "pay",
        "bacs",
        "employer",
        "income",
    ]

    def analyse(self, transactions: list[dict]) -> dict:
        if not transactions:
            return {
                "frequency": None,
                "regularity_score": 0,
                "average_salary": None,
                "variation_pct": None,
            }

        # Filter for credits (incoming payments)
        credits = [
            t
            for t in transactions
            if t.get("transaction_type") == "CREDIT"
            or float(t.get("amount", 0)) > 0
        ]

        if not credits:
            return {
                "frequency": None,
                "regularity_score": 0,
                "average_salary": None,
                "variation_pct": None,
            }

        # Identify likely salary payments
        salary_candidates = self._identify_salary_payments(credits)

        if not salary_candidates:
            return {
                "frequency": "irregular",
                "regularity_score": 20,
                "average_salary": None,
                "variation_pct": None,
            }

        # Analyse frequency
        frequency = self._detect_frequency(salary_candidates)
        regularity_score = self._calculate_regularity(salary_candidates, frequency)
        amounts = [abs(float(t.get("amount", 0))) for t in salary_candidates]
        average_salary = statistics.mean(amounts) if amounts else 0
        variation_pct = (
            (statistics.stdev(amounts) / average_salary * 100)
            if len(amounts) > 1 and average_salary > 0
            else 0
        )

        return {
            "frequency": frequency,
            "regularity_score": min(100, max(0, regularity_score)),
            "average_salary": round(average_salary, 2),
            "variation_pct": round(variation_pct, 2),
        }

    def _identify_salary_payments(self, credits: list[dict]) -> list[dict]:
        # Group credits by similar amounts (within 10% tolerance)
        amount_groups = defaultdict(list)

        for t in credits:
            amount = abs(float(t.get("amount", 0)))
            if amount < 500:  # Skip small credits unlikely to be salary
                continue

            matched = False
            for key_amount in list(amount_groups.keys()):
                if abs(amount - key_amount) / key_amount <= 0.10:
                    amount_groups[key_amount].append(t)
                    matched = True
                    break

            if not matched:
                amount_groups[amount].append(t)

        if not amount_groups:
            return []

        # The salary is likely the most frequent recurring credit of significant value
        best_group = max(amount_groups.values(), key=len)

        # Also check description for salary keywords
        keyword_matches = [
            t
            for t in credits
            if any(
                kw in (t.get("description", "") or "").lower()
                for kw in self.SALARY_KEYWORDS
            )
            and abs(float(t.get("amount", 0))) >= 500
        ]

        # Prefer keyword matches if they form a reasonable group
        if len(keyword_matches) >= 3:
            return keyword_matches

        return best_group if len(best_group) >= 2 else []

    def _detect_frequency(self, salary_payments: list[dict]) -> str:
        if len(salary_payments) < 2:
            return "irregular"

        dates = sorted(
            [
                datetime.fromisoformat(
                    t.get("timestamp", t.get("date", "2024-01-01"))[:10]
                )
                for t in salary_payments
            ]
        )

        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        if not gaps:
            return "irregular"

        avg_gap = statistics.mean(gaps)

        if 25 <= avg_gap <= 35:
            return "monthly"
        elif 12 <= avg_gap <= 16:
            return "fortnightly"
        elif 5 <= avg_gap <= 9:
            return "weekly"
        else:
            return "irregular"

    def _calculate_regularity(self, salary_payments: list[dict], frequency: str) -> int:
        if frequency == "irregular":
            return 30

        score = 50  # Base score for having regular-looking payments

        # Bonus for number of payments (more data = more confidence)
        count = len(salary_payments)
        if count >= 6:
            score += 20
        elif count >= 3:
            score += 10

        # Check amount consistency
        amounts = [abs(float(t.get("amount", 0))) for t in salary_payments]
        if len(amounts) > 1:
            avg = statistics.mean(amounts)
            variation = statistics.stdev(amounts) / avg * 100 if avg > 0 else 100
            if variation < 5:
                score += 20  # Very consistent
            elif variation < 10:
                score += 10  # Fairly consistent
            elif variation > 25:
                score -= 10  # High variation

        # Check timing consistency
        dates = sorted(
            [
                datetime.fromisoformat(
                    t.get("timestamp", t.get("date", "2024-01-01"))[:10]
                )
                for t in salary_payments
            ]
        )
        if len(dates) > 1:
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            gap_variation = statistics.stdev(gaps) if len(gaps) > 1 else 0
            if gap_variation < 3:
                score += 10  # Very regular timing
            elif gap_variation > 7:
                score -= 10  # Irregular timing

        return score
