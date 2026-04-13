interface AffordabilityBreakdownProps {
  maxLoan?: number | null;
  bindingConstraint?: string | null;
  stressRate?: number | null;
}

/**
 * Shows the broker which cap (income multiple, stress rate, or post-expense
 * cashflow) is determining the maximum loan the lender will offer. This is
 * the "why" column on the advisor's affordability worksheet — every case is
 * bound by one of these and knowing which one is dispositive is what the
 * suitability letter cites.
 */
export default function AffordabilityBreakdown({
  maxLoan,
  bindingConstraint,
  stressRate,
}: AffordabilityBreakdownProps) {
  if (maxLoan == null && !bindingConstraint) return null;

  const constraintLabel: Record<string, string> = {
    income_multiple: "Income multiple",
    stress: "Stress-rate affordability",
    cashflow: "Post-expense cashflow",
  };

  const constraintExplanation: Record<string, string> = {
    income_multiple:
      "The lender's income multiple is the binding cap on your borrowing.",
    stress:
      "The lender's stress-test rate is the binding cap — the monthly payment at the stressed rate hits the debt-to-income ceiling.",
    cashflow:
      "Your post-expense cashflow is the binding cap — existing commitments reduce the mortgage payment you can afford.",
  };

  return (
    <div className="card">
      <h3 className="font-semibold text-sm mb-3">Affordability assessment</h3>
      {maxLoan != null && (
        <div className="mb-3">
          <div className="text-xs text-gray-500">Maximum affordable loan</div>
          <div className="text-xl font-bold text-gray-900">
            £{Math.round(maxLoan).toLocaleString()}
          </div>
        </div>
      )}
      {bindingConstraint && (
        <div className="space-y-1">
          <div className="text-xs text-gray-500">Binding constraint</div>
          <div className="text-sm font-medium text-gray-900">
            {constraintLabel[bindingConstraint] || bindingConstraint}
          </div>
          <p className="text-xs text-gray-600">
            {constraintExplanation[bindingConstraint] || ""}
          </p>
        </div>
      )}
      {stressRate != null && (
        <div className="mt-3 pt-3 border-t text-xs text-gray-600">
          Stress rate applied:{" "}
          <span className="font-medium">{stressRate.toFixed(2)}%</span>
        </div>
      )}
    </div>
  );
}
