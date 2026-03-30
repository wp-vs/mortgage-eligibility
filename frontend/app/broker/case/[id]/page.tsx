"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProductCard from "@/components/ProductCard";
import IncomeAnalysis from "@/components/IncomeAnalysis";
import ExpenseFlags from "@/components/ExpenseFlags";
import { getBrokerCaseDetail, reviewRecommendation } from "@/lib/api";

export default function BrokerCasePage() {
  const params = useParams();
  const customerId = Number(params.id);
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");

  useEffect(() => {
    loadCase();
  }, [customerId]);

  async function loadCase() {
    try {
      const data = await getBrokerCaseDetail(customerId);
      setCaseData(data);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(recId: number, approved: boolean) {
    try {
      await reviewRecommendation(customerId, recId, approved, reviewNotes);
      setReviewingId(null);
      setReviewNotes("");
      loadCase(); // Reload
    } catch {
      alert("Failed to submit review");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500">Loading case...</p>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        <p className="text-gray-500">Case not found.</p>
      </div>
    );
  }

  const { customer, banking_analysis, recommendations } = caseData;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <a
          href="/broker"
          className="text-sm text-primary-600 hover:underline mb-2 inline-block"
        >
          ← Back to Dashboard
        </a>
        <h1 className="text-3xl font-bold text-gray-900">
          Case: {customer?.full_name || `Customer #${customerId}`}
        </h1>
      </div>

      {/* Customer Profile */}
      <div className="card mb-6">
        <h2 className="font-semibold text-lg mb-4">Customer Profile</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Name</span>
            <div className="font-medium">{customer?.full_name || "N/A"}</div>
          </div>
          <div>
            <span className="text-gray-500">Email</span>
            <div className="font-medium">{customer?.email || "N/A"}</div>
          </div>
          <div>
            <span className="text-gray-500">Employment</span>
            <div className="font-medium capitalize">
              {customer?.employment_type?.replace("_", " ") || "N/A"}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Income</span>
            <div className="font-medium">
              {customer?.annual_income
                ? `£${Number(customer.annual_income).toLocaleString()}`
                : "N/A"}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Property Value</span>
            <div className="font-medium">
              {customer?.property_value
                ? `£${Number(customer.property_value).toLocaleString()}`
                : "N/A"}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Deposit</span>
            <div className="font-medium">
              {customer?.deposit_amount
                ? `£${Number(customer.deposit_amount).toLocaleString()}`
                : "N/A"}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Property Type</span>
            <div className="font-medium capitalize">
              {customer?.property_type?.replace("_", " ") || "N/A"}
            </div>
          </div>
          <div>
            <span className="text-gray-500">First Time Buyer</span>
            <div className="font-medium">
              {customer?.first_time_buyer === true
                ? "Yes"
                : customer?.first_time_buyer === false
                  ? "No"
                  : "N/A"}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recommendations with review controls */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="font-semibold text-xl">
            Product Recommendations ({recommendations?.length || 0})
          </h2>

          {recommendations?.map((rec: any) => (
            <div key={rec.id}>
              <ProductCard
                rank={rec.rank}
                lenderName={rec.product?.lender_name || "Unknown"}
                productName={rec.product?.product_name || ""}
                rate={rec.product?.rate || 0}
                productType={rec.product?.product_type || "fixed"}
                initialPeriodMonths={rec.product?.initial_period_months || 24}
                maxLtv={rec.product?.max_ltv || 0}
                arrangementFee={rec.product?.arrangement_fee || 0}
                estimatedMonthlyPayment={rec.product?.estimated_monthly_payment}
                matchScore={Number(rec.match_score)}
                matchReasons={rec.match_reasons}
                unmetCriteria={rec.unmet_criteria}
                brokerApproved={rec.broker_approved}
                brokerNotes={rec.broker_notes}
              />

              {/* Review controls */}
              {rec.broker_approved === null && (
                <div className="mt-2 card border-dashed">
                  {reviewingId === rec.id ? (
                    <div className="space-y-3">
                      <textarea
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        placeholder="Add notes (optional)..."
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                        rows={2}
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleReview(rec.id, true)}
                          className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleReview(rec.id, false)}
                          className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700"
                        >
                          Decline
                        </button>
                        <button
                          onClick={() => {
                            setReviewingId(null);
                            setReviewNotes("");
                          }}
                          className="text-gray-500 text-sm hover:text-gray-700"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setReviewingId(rec.id)}
                      className="btn-secondary text-sm"
                    >
                      Review This Product
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Right: Banking analysis */}
        <div className="space-y-6">
          {banking_analysis ? (
            <>
              <IncomeAnalysis
                salaryFrequency={banking_analysis.salary_frequency}
                salaryRegularityScore={banking_analysis.salary_regularity_score}
                averageSalary={
                  banking_analysis.average_salary
                    ? Number(banking_analysis.average_salary)
                    : null
                }
                salaryVariationPct={
                  banking_analysis.salary_variation_pct
                    ? Number(banking_analysis.salary_variation_pct)
                    : null
                }
              />
              <ExpenseFlags
                flaggedExpenses={banking_analysis.flagged_expenses || []}
                estimatedMonthlyRent={
                  banking_analysis.estimated_monthly_rent
                    ? Number(banking_analysis.estimated_monthly_rent)
                    : null
                }
                totalMonthlyCommitments={
                  banking_analysis.total_monthly_commitments
                    ? Number(banking_analysis.total_monthly_commitments)
                    : null
                }
              />
            </>
          ) : (
            <div className="card">
              <p className="text-sm text-gray-500">
                No banking analysis available for this customer.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
