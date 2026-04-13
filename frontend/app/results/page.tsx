"use client";

import { useEffect, useState } from "react";
import ProductCard from "@/components/ProductCard";
import IncomeAnalysis from "@/components/IncomeAnalysis";
import ExpenseFlags from "@/components/ExpenseFlags";
import AffordabilityBreakdown from "@/components/AffordabilityBreakdown";
import {
  getRecommendations,
  getBankingAnalysis,
  getCustomer,
} from "@/lib/api";

const COMPLEXITY_LABELS: Record<string, string> = {
  non_standard_employment: "non-standard employment",
  adverse_credit: "adverse credit history",
  high_ltv: "high loan-to-value",
  non_standard_property: "non-standard property",
  irregular_income: "irregular income",
  critical_expenses: "critical expense flags",
  interest_only_repayment: "interest-only repayment",
};

export default function ResultsPage() {
  const [loading, setLoading] = useState(true);
  const [customer, setCustomer] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [bankingAnalysis, setBankingAnalysis] = useState<any>(null);

  useEffect(() => {
    const customerId = localStorage.getItem("customerId");
    if (!customerId) {
      window.location.href = "/";
      return;
    }
    loadData(Number(customerId));
  }, []);

  async function loadData(customerId: number) {
    try {
      const [custData, recData, baData] = await Promise.all([
        getCustomer(customerId),
        getRecommendations(customerId),
        getBankingAnalysis(customerId).catch(() => null),
      ]);
      setCustomer(custData);
      setRecommendations(recData.recommendations || []);
      setBankingAnalysis(baData);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-gray-500">Loading your results...</p>
        </div>
      </div>
    );
  }

  // Complexity reasons are attached to each recommendation at match-time.
  // They're customer-wide, so the first recommendation is representative.
  const complexityReasons: string[] =
    recommendations[0]?.complexity_reasons || [];
  const requiresBrokerReview =
    recommendations.some((r) => r.requires_broker_review) ||
    complexityReasons.length > 0;
  const topRec = recommendations[0];

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Mortgage Options</h1>
        <p className="text-gray-500 mt-1">
          Based on your profile, here are the top matched products. A broker
          will review these before any formal recommendation.
        </p>
      </div>

      {/* Routing banner */}
      {recommendations.length > 0 &&
        (requiresBrokerReview ? (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="font-semibold text-amber-900 mb-1">
              Broker review required
            </div>
            <p className="text-sm text-amber-800">
              Your case requires assessment by a qualified broker before
              these recommendations can be finalised because of:{" "}
              <span className="font-medium">
                {complexityReasons
                  .map((r) => COMPLEXITY_LABELS[r] || r)
                  .join(", ")}
              </span>
              .
            </p>
          </div>
        ) : (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="font-semibold text-green-900 mb-1">
              Your case qualifies for automated recommendation
            </div>
            <p className="text-sm text-green-800">
              Your profile matches the standard case criteria. A broker will
              countersign the recommendation, but no additional underwriting
              is required.
            </p>
          </div>
        ))}

      {/* Customer summary */}
      {customer && (
        <div className="card mb-6">
          <h2 className="font-semibold text-lg mb-3">Your Profile</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Property Value</span>
              <div className="font-medium">
                {customer.property_value
                  ? `£${Number(customer.property_value).toLocaleString()}`
                  : "N/A"}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Deposit</span>
              <div className="font-medium">
                {customer.deposit_amount
                  ? `£${Number(customer.deposit_amount).toLocaleString()}`
                  : "N/A"}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Annual Income</span>
              <div className="font-medium">
                {customer.annual_income
                  ? `£${Number(customer.annual_income).toLocaleString()}`
                  : "N/A"}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Employment</span>
              <div className="font-medium capitalize">
                {customer.employment_type?.replace("_", " ") || "N/A"}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recommendations */}
        <div className="lg:col-span-2 space-y-6">
          {recommendations.length === 0 ? (
            <div className="card text-center py-12">
              <p className="text-gray-500">
                No product recommendations yet. Complete the chat to get
                matched.
              </p>
              <a href="/chat" className="btn-primary inline-block mt-4">
                Go to Chat
              </a>
            </div>
          ) : (
            recommendations.map((rec: any) => (
              <ProductCard
                key={rec.id}
                recommendationId={rec.id}
                rank={rec.rank}
                lenderName={rec.product?.lender_name || "Unknown"}
                productName={rec.product?.product_name || rec.product_id}
                rate={rec.product?.rate || 0}
                productType={rec.product?.product_type || "fixed"}
                initialPeriodMonths={rec.product?.initial_period_months || 24}
                maxLtv={rec.product?.max_ltv || 0}
                arrangementFee={rec.product?.arrangement_fee || 0}
                estimatedMonthlyPayment={rec.product?.estimated_monthly_payment}
                totalCostInitial={rec.total_cost_initial}
                effectiveRate={rec.effective_rate}
                bindingConstraint={rec.binding_affordability_constraint}
                stressRateUsed={rec.stress_rate_used}
                requiresBrokerReview={rec.requires_broker_review}
                matchScore={Number(rec.match_score)}
                matchReasons={rec.match_reasons}
                unmetCriteria={rec.unmet_criteria}
                brokerApproved={rec.broker_approved}
                brokerNotes={rec.broker_notes}
              />
            ))
          )}
        </div>

        {/* Right: Banking analysis + affordability */}
        <div className="space-y-6">
          {topRec && (
            <AffordabilityBreakdown
              maxLoan={topRec.affordability_max_loan}
              bindingConstraint={topRec.binding_affordability_constraint}
              stressRate={topRec.stress_rate_used}
            />
          )}
          {bankingAnalysis && (
            <>
              <IncomeAnalysis
                salaryFrequency={bankingAnalysis.salary_frequency}
                salaryRegularityScore={bankingAnalysis.salary_regularity_score}
                averageSalary={
                  bankingAnalysis.average_salary
                    ? Number(bankingAnalysis.average_salary)
                    : null
                }
                salaryVariationPct={
                  bankingAnalysis.salary_variation_pct
                    ? Number(bankingAnalysis.salary_variation_pct)
                    : null
                }
              />
              <ExpenseFlags
                flaggedExpenses={bankingAnalysis.flagged_expenses || []}
                estimatedMonthlyRent={
                  bankingAnalysis.estimated_monthly_rent
                    ? Number(bankingAnalysis.estimated_monthly_rent)
                    : null
                }
                totalMonthlyCommitments={
                  bankingAnalysis.total_monthly_commitments
                    ? Number(bankingAnalysis.total_monthly_commitments)
                    : null
                }
              />
            </>
          )}
        </div>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200 text-sm text-blue-800">
        <strong>What happens next?</strong> A qualified mortgage broker will
        review your matched products and financial analysis. They may contact
        you to discuss options before making a formal recommendation. This is
        not financial advice.
      </div>
    </div>
  );
}
